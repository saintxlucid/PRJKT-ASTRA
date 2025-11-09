"""
ASTRA RAG Fusion Engine
Created: October 25, 2025

Implements ASTRA's Retrieval-Augmented Generation with:
- Memory-based retrieval with energy thresholds
- Persona-anchored context planning
- Length budgeting and deduplication
- Source labeling and citation tracking
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging
import structlog
from uuid import uuid4

from astra.memory_types import Memory, MemoryEnergy
from astra.core.memory_engine import MemoryEngine
from astra.core.persona import PersonaManager
from astra.core.inference_queue import InferenceQueue

logger = structlog.get_logger()

class RAGFusionEngine:
    """Orchestrates retrieval and fusion of memories with persona"""
    
    def __init__(
        self,
        memory_engine: MemoryEngine,
        persona_manager: PersonaManager,
        inference_queue: InferenceQueue,
        default_k: int = 5,
        min_energy: float = 0.3,
        max_context_tokens: int = 3072  # Conservative default
    ):
        self.memory_engine = memory_engine
        self.persona_manager = persona_manager
        self.inference_queue = inference_queue
        self.default_k = default_k
        self.min_energy = min_energy
        self.max_context_tokens = max_context_tokens
        
    async def answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        k: Optional[int] = None,
        context_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a response using RAG fusion
        
        Args:
            query: User question/prompt
            session_id: Optional session for context continuity
            persona_id: Optional specific persona to use
            k: Number of memories to retrieve (default: self.default_k)
            context_tokens: Max tokens for context (default: self.max_context_tokens)
            
        Returns:
            Dict containing response and metadata including:
            - text: Generated response
            - memory_ids: List of memory IDs used
            - adapter_ids: List of adapter IDs applied
            - citations: Source attribution details
            - metrics: Timing and token usage stats
        """
        trace_id = str(uuid4())
        start_time = datetime.now()
        
        # 1. Retrieve relevant memories
        memories = await self._retrieve_memories(
            query,
            k or self.default_k,
            trace_id
        )
        
        # 2. Plan context budget and deduplicate
        context, citations = self._plan_context(
            memories,
            context_tokens or self.max_context_tokens
        )
        
        # 3. Get persona anchor
        persona = await self.persona_manager.get_persona(persona_id)
        system_prompt = self._compose_system_prompt(persona, context)
        
        # 4. Queue for inference
        result = await self.inference_queue.enqueue(
            system_prompt=system_prompt,
            user_prompt=query,
            trace_id=trace_id,
            session_id=session_id
        )
        
        # 5. Enrich response with metadata
        elapsed = (datetime.now() - start_time).total_seconds()
        memory_ids = [m.id for m in memories]
        
        response = {
            "text": result["text"],
            "memory_ids": memory_ids,
            "adapter_ids": result.get("adapter_ids", []),
            "citations": citations,
            "metrics": {
                "retrieval_time": elapsed,
                "total_time": elapsed + result.get("generation_time", 0),
                "context_tokens": len(context),
                "output_tokens": result.get("output_tokens", 0)
            },
            "trace_id": trace_id
        }
        
        # Log completion with key metrics
        logger.info(
            "rag_fusion_complete",
            trace_id=trace_id,
            memory_count=len(memory_ids),
            total_time=response["metrics"]["total_time"],
            context_tokens=response["metrics"]["context_tokens"]
        )
        
        return response
        
    async def _retrieve_memories(
        self,
        query: str,
        k: int,
        trace_id: str
    ) -> List[Memory]:
        """Retrieve relevant memories above energy threshold"""
        results = await self.memory_engine.search(
            query,
            k=k,
            min_energy=self.min_energy
        )
        
        # Log retrieval stats
        energy_stats = self._calculate_energy_stats(results)
        logger.info(
            "memory_retrieval",
            trace_id=trace_id,
            results_count=len(results),
            **energy_stats
        )
        
        return results
        
    def _plan_context(
        self,
        memories: List[Memory],
        max_tokens: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Plan context composition within token budget"""
        from astra.utils.tokenization import TokenCounter
        
        counter = TokenCounter()
        context_parts = []
        citations = {}
        
        # Prepare memory texts with markers
        marked_texts = []
        for i, memory in enumerate(memories):
            marker = f"[src{i+1}]"
            marked_text = f"{marker} {memory.content}"
            marked_texts.append((marked_text, marker, memory))
            
        # Measure and select within budget
        selected_texts, remaining = counter.measure_components(
            [t[0] for t in marked_texts],
            max_tokens
        )
        
        # Build context and citations
        for text, marker, memory in zip(selected_texts, 
                                      [t[1] for t in marked_texts],
                                      [t[2] for t in marked_texts]):
            context_parts.append(text)
            citations[marker] = {
                "id": memory.id,
                "source": memory.source,
                "timestamp": memory.created_at.isoformat()
            }
            
        return "\n\n".join(context_parts), citations
        
    def _compose_system_prompt(
        self,
        persona: Dict[str, Any],
        context: str
    ) -> str:
        """Compose system prompt with persona and context"""
        return f"""You are {persona['name']}, {persona['description']}

When answering, use the following context as reference. Always cite sources using [srcN] markers when drawing from context.

Context:
{context}

Answer in your unique voice while being accurate and helpful. If the context doesn't contain relevant information, say so clearly."""
        
    def _calculate_energy_stats(
        self,
        memories: List[Memory]
    ) -> Dict[str, float]:
        """Calculate energy statistics for retrieved memories"""
        if not memories:
            return {"avg_energy": 0, "max_energy": 0, "min_energy": 0}
            
        energies = [m.energy for m in memories]
        return {
            "avg_energy": sum(energies) / len(energies),
            "max_energy": max(energies),
            "min_energy": min(energies)
        }