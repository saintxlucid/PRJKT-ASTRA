from __future__ import annotations
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass
import time
import hashlib
from .metrics import (
    MEMORY_RETRIEVAL_LATENCY,
    MEMORY_COUNT,
    TOKEN_USAGE,
    TOKEN_BUDGET_USAGE,
    MEMORY_TOKENS,
    ERROR_COUNT,
)
from .memory_cache import MemoryCache
from .templates import ResponseTemplate

DEFAULT_BUDGET = 3000
DEFAULT_OUTPUT_RESERVE = 512
DEFAULT_CACHE_SIZE = 1000
DEFAULT_CACHE_TTL = 3600

@dataclass
class MemoryHit:
    id: str
    text: str
    energy: float
    score: Optional[float] = None  # similarity score (higher is better) or distance (lower is better)

class RAGFusionEngine:
    def __init__(
        self,
        memory_engine,
        persona_manager,
        token_counter: Callable[[str], int],
        max_context_tokens: int = DEFAULT_BUDGET,
        output_reserve_tokens: int = DEFAULT_OUTPUT_RESERVE,
        min_energy: float = 0.0,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        self.memory = memory_engine
        self.persona = persona_manager
        self.count = token_counter
        self.max_ctx = max_context_tokens
        self.reserve = output_reserve_tokens
        self.min_energy = min_energy
        self.cache = MemoryCache(max_size=cache_size, ttl_seconds=cache_ttl)
        self.templates = ResponseTemplate()
        
    def _cache_key(self, query: str, k: int) -> str:
        """Generate cache key for query."""
        return hashlib.sha256(
            f"{query}::{k}".encode()
        ).hexdigest()

    # ----- retrieval + ranking -----
    async def retrieve(self, query: str, k: int = 8) -> List[MemoryHit]:
        start = time.perf_counter()
        cache_key = self._cache_key(query, k)
        
        # Check cache
        if cached := self.cache.get(cache_key):
            return [MemoryHit(**hit) for hit in cached["hits"]]
            
        try:
            raw = self.memory.retrieve(query, top_k=k)  # sync API from your MemoryEngine
            
            # Process results
            hits = []
            for r in raw:
                meta = r.get("metadata", {})
                text = meta.get("text_preview") or meta.get("document") or r.get("text_preview") or ""
                energy = float(meta.get("nutrition", {}).get("energy_score", 0.5))
                # prefer 'score' if present (SimpleVecDB), else invert distance from Chroma
                score = r.get("score")
                if score is None and "distance" in r:
                    try:
                        score = 1.0 / (1.0 + float(r["distance"]))
                    except Exception:
                        score = 0.0
                if energy >= self.min_energy and text:
                    hits.append(MemoryHit(id=r.get("id", ""), text=text, energy=energy, score=score))
            
            # Sort by (energy, score) descending
            hits.sort(key=lambda h: (round(h.energy, 3), h.score or 0.0), reverse=True)
            
            # Dedup by text
            seen = set()
            uniq: List[MemoryHit] = []
            for h in hits:
                key = h.text.strip()
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(h)
                
            # Cache results
            self.cache.set(cache_key, {
                "hits": [
                    {
                        "id": h.id,
                        "text": h.text,
                        "energy": h.energy,
                        "score": h.score
                    }
                    for h in uniq
                ]
            })
            
            MEMORY_COUNT.observe(len(uniq))
            return uniq
            
        except Exception as e:
            ERROR_COUNT.labels(type="retrieval").inc()
            raise
        finally:
            MEMORY_RETRIEVAL_LATENCY.observe(time.perf_counter() - start)
        hits: List[MemoryHit] = []
        for r in raw:
            meta = r.get("metadata", {})
            text = meta.get("text_preview") or meta.get("document") or r.get("text_preview") or ""
            energy = float(meta.get("nutrition", {}).get("energy_score", 0.5))
            # prefer 'score' if present (SimpleVecDB), else invert distance from Chroma
            score = r.get("score")
            if score is None and "distance" in r:
                try:
                    score = 1.0 / (1.0 + float(r["distance"]))
                except Exception:
                    score = 0.0
            if energy >= self.min_energy and text:
                hits.append(MemoryHit(id=r.get("id", ""), text=text, energy=energy, score=score))
        # sort by (energy, score) descending
        hits.sort(key=lambda h: (round(h.energy, 3), h.score or 0.0), reverse=True)
        # dedup by text
        seen = set()
        uniq: List[MemoryHit] = []
        for h in hits:
            key = h.text.strip()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(h)
        MEMORY_COUNT.observe(len(uniq))
        return uniq

    # ----- context planning -----
    def plan(self, query: str, hits: List[MemoryHit]) -> Tuple[str, List[Dict[str, Any]]]:
        # Get persona info
        anchor = self.persona.get_anchor()
        system_prelude = self.persona.system_prelude()
        persona_data = None
        if anchor:
            persona_data = {"description": anchor}

        # Format memories respecting budget
        budget = max(128, self.max_ctx - self.reserve)
        used = 0
        
        # Track system/persona token usage
        if system_prelude:
            prelude_tokens = self.count(system_prelude)
            TOKEN_USAGE.labels(stage="prompt").inc(prelude_tokens)
            used += prelude_tokens
            
        if anchor:
            anchor_tokens = self.count(anchor)
            TOKEN_USAGE.labels(stage="prompt").inc(anchor_tokens)
            used += anchor_tokens

        # Process memories
        memory_data = []
        citations = []
        for h in hits:
            snippet = h.text.strip()
            add_tokens = self.count(snippet) + 16  # safety margin for formatting
            if used + add_tokens > budget:
                break
                
            memory_data.append({
                "id": h.id,
                "text": snippet,
                "source": "unknown",  # enhance with source tracking
                "energy": h.energy
            })
            citations.append({
                "id": h.id,
                "energy": round(h.energy, 3),
                "text": snippet
            })
            
            used += add_tokens
            TOKEN_USAGE.labels(stage="context").inc(add_tokens)
            MEMORY_TOKENS.observe(add_tokens)

        # Format with template
        prompt = self.templates.format_prompt(
            query=query.strip(),
            memories=memory_data,
            system_context=system_prelude,
            persona=persona_data
        )
        
        return prompt, citations

    # ----- public high-level helper -----
    async def fuse(self, query: str, k: int = 8) -> Dict[str, Any]:
        hits = await self.retrieve(query, k=k)
        prompt, citations = self.plan(query, hits)
        context_tokens = self.count(prompt)
        TOKEN_BUDGET_USAGE.observe((context_tokens / self.max_ctx) * 100)
        return {
            "prompt": prompt,
            "citations": citations,
            "persona_id": self.persona.anchor_id(),
            "context_tokens": context_tokens,
            "budget_tokens": self.max_ctx,
        }