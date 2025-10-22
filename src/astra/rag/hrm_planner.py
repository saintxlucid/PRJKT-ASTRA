"""
ASTRA Multi-RAG HRM Planner
Hierarchical Reasoning Model with dual-speed planning loops.

Fast Loop (Gamma ~30 Hz): Rapid retrieval refinement, evidence gap detection
Slow Loop (Alpha ~8-13 Hz): Reflection, meta-reasoning, plan adjustment

Sacred Code: 333
Author: Saint Lucid ⚛️
Date: October 20, 2025
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import structlog

from astra.rag.multi_rag_core import (
    MultiRAGRetriever,
    FusionLayer,
    ContextComposer,
    RetrievalResult,
    RAGAnswer,
    CitationRef
)

logger = structlog.get_logger("astra.rag.planner")


# ============================================================================
# PLAN & STATE MODELS
# ============================================================================

@dataclass
class RetrievalPlan:
    """State for retrieval plan."""
    query: str
    active_categories: List[str]
    retrieval_config: Dict[str, Any]
    fusion_weights: Optional[Dict[str, float]] = None
    reranker_threshold: float = 0.5
    diversity_cap: float = 0.4
    iterations: int = 0
    max_iterations: int = 2


@dataclass
class ReflectionResult:
    """Result from slow-loop reflection."""
    answerability: float  # [0, 1]
    conflict_score: float  # [0, 1] where 0 = no conflict
    specificity: float  # [0, 1]
    confidence: float  # Composite confidence
    should_finalize: bool  # Decision to finalize


# ============================================================================
# HRM PLANNER
# ============================================================================

class HRMPlanner:
    """
    Hierarchical Reasoning Model for Multi-RAG.
    Implements dual-speed planning with fast retrieval refinement and slow reflection.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        retriever: MultiRAGRetriever,
        fusion_layer: FusionLayer,
        context_composer: ContextComposer,
        reasoner: Optional[Any] = None
    ):
        """
        Initialize HRM planner.
        
        Args:
            config: System configuration
            retriever: MultiRAGRetriever instance
            fusion_layer: FusionLayer instance
            context_composer: ContextComposer instance
            reasoner: LLM or reasoning engine (optional, for demo can be mocked)
        """
        self.config = config
        self.retriever = retriever
        self.fusion_layer = fusion_layer
        self.context_composer = context_composer
        self.reasoner = reasoner
        
        self.fast_config = config.get("planner", {}).get("fast_loop", {})
        self.slow_config = config.get("planner", {}).get("slow_loop", {})
        
        logger.info("hrm_planner_initialized")
    
    async def answer(
        self,
        query: str,
        policy: str = "hrm",
        categories: Optional[List[str]] = None,
        trace: bool = False
    ) -> RAGAnswer:
        """
        Full HRM planning loop: retrieve → fast loop → reflect → finalize.
        
        Args:
            query: User query
            policy: Retrieval policy ("hrm" | "fast_only" | "slow_only")
            categories: Optional category filter
            trace: Return detailed trace metadata
        
        Returns:
            RAGAnswer with citations and confidence
        """
        logger.info("answer_start", query=query, policy=policy)
        
        # Initialize plan
        plan = RetrievalPlan(
            query=query,
            active_categories=categories or list(self.config["categories"].keys()),
            retrieval_config=self.config.get("retrieval_pipeline", {}),
            max_iterations=self.fast_config.get("max_iterations", 2)
        )
        
        # Initial retrieval
        logger.info("initial_retrieval_start")
        candidates = await self.retriever.retrieve(
            query=query,
            categories=plan.active_categories,
            policy=policy
        )
        
        # Fuse across categories
        logger.info("fusion_start")
        fused_results = self.fusion_layer.fuse(query, candidates)
        
        # Fast loop: Evidence gap detection and refinement
        if policy in ("hrm", "fast_only"):
            fused_results = await self._fast_loop(query, plan, fused_results)
        
        # Compose context
        logger.info("context_composition_start")
        composed_context, citations = self.context_composer.compose(query, fused_results)
        
        # Generate initial answer
        answer_text = await self._reason(query, composed_context)
        confidence = 0.85  # Initial confidence
        
        # Slow loop: Reflection and meta-reasoning
        if policy == "hrm" and self.slow_config.get("enabled", False):
            reflection = await self._slow_loop(
                query,
                answer_text,
                fused_results,
                composed_context
            )
            
            confidence = reflection.confidence
            
            if not reflection.should_finalize:
                # Adjust plan and re-retrieve
                logger.info("plan_adjustment_triggered")
                plan = self._adjust_plan(plan, reflection)
                
                # Re-retrieve with adjusted plan
                candidates = await self.retriever.retrieve(
                    query=query,
                    categories=plan.active_categories,
                    policy="default"
                )
                fused_results = self.fusion_layer.fuse(query, candidates)
                composed_context, citations = self.context_composer.compose(query, fused_results)
                answer_text = await self._reason(query, composed_context)
        
        # Compile answer
        result = RAGAnswer(
            answer=answer_text,
            citations=citations,
            confidence=confidence,
            metadata={
                "query": query,
                "categories_used": plan.active_categories,
                "planner_mode": policy,
                "fast_loops": plan.iterations,
                "slow_loops": 1 if policy == "hrm" else 0,
                "source_diversity": self._compute_diversity(fused_results),
                "retrieval_time_ms": 0,  # TODO: add timing
                "final_context_tokens": len(composed_context.split())
            }
        )
        
        logger.info("answer_complete", confidence=confidence)
        return result
    
    async def _fast_loop(
        self,
        query: str,
        plan: RetrievalPlan,
        initial_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Fast loop (Gamma ~30 Hz):
        Detects evidence gaps and triggers sub-queries for refinement.
        
        Returns:
            Refined retrieval results
        """
        logger.info("fast_loop_start", max_iterations=plan.max_iterations)
        
        current_results = initial_results
        plan.iterations = 0
        
        for iteration in range(plan.max_iterations):
            plan.iterations += 1
            
            # Check evidence gap
            diversity = self._compute_diversity(current_results)
            coverage = self._estimate_coverage(current_results, query)
            
            gap_threshold = self.fast_config.get("evidence_gap_threshold", 0.3)
            
            logger.info(
                "fast_loop_iteration",
                iteration=iteration,
                diversity=diversity,
                coverage=coverage
            )
            
            if diversity < gap_threshold or coverage < gap_threshold:
                # Trigger sub-queries
                logger.info("evidence_gap_detected", triggering_sub_queries=True)
                sub_queries = self._generate_sub_queries(query, current_results)
                
                for sub_q in sub_queries:
                    logger.info("executing_sub_query", sub_query=sub_q)
                    
                    # Retrieve for sub-query
                    sub_candidates = await self.retriever.retrieve(
                        query=sub_q,
                        categories=plan.active_categories
                    )
                    
                    # Fuse with existing results
                    sub_fused = self.fusion_layer.fuse(sub_q, sub_candidates)
                    
                    # Merge and re-rank
                    current_results = self._merge_and_rerank(current_results, sub_fused)
                
                logger.info("sub_queries_complete", count=len(sub_queries))
            else:
                # Evidence sufficient
                logger.info("fast_loop_sufficient_evidence")
                break
        
        logger.info("fast_loop_complete", iterations=plan.iterations)
        return current_results[:50]  # Top 50 for slow loop
    
    async def _slow_loop(
        self,
        query: str,
        answer: str,
        context_results: List[RetrievalResult],
        composed_context: str
    ) -> ReflectionResult:
        """
        Slow loop (Alpha ~8-13 Hz):
        Reflect on candidate answer and decide to finalize or re-retrieve.
        
        Returns:
            ReflectionResult with decision
        """
        logger.info("slow_loop_start")
        
        # Answerability check
        answerability = await self._score_answerability(
            query,
            answer,
            composed_context
        )
        logger.info("answerability_scored", score=answerability)
        
        # Conflict detection
        conflict = self._compute_conflict_score(context_results)
        logger.info("conflict_scored", score=conflict)
        
        # Specificity check
        specificity = self._check_specificity(answer)
        logger.info("specificity_scored", score=specificity)
        
        # Composite confidence
        confidence = (answerability + (1 - conflict) + specificity) / 3
        
        # Decision threshold
        threshold = self.slow_config.get("decision_threshold", 0.7)
        should_finalize = confidence >= threshold
        
        result = ReflectionResult(
            answerability=answerability,
            conflict_score=conflict,
            specificity=specificity,
            confidence=confidence,
            should_finalize=should_finalize
        )
        
        logger.info(
            "slow_loop_complete",
            confidence=confidence,
            should_finalize=should_finalize
        )
        
        return result
    
    # ========================================================================
    # HELPER METHODS — EVIDENCE GAP DETECTION
    # ========================================================================
    
    def _generate_sub_queries(
        self,
        query: str,
        current_results: List[RetrievalResult]
    ) -> List[str]:
        """
        Generate sub-queries to refine evidence.
        Strategies:
          - Synonym expansion
          - Extract table/figure captions
          - Switch chunker mode
          - Cross-category expansion
        """
        sub_queries = []
        
        # 1. Synonym expansion
        synonyms = self._expand_synonyms(query)
        sub_queries.extend(synonyms[:1])  # Top 1 synonym query
        
        # 2. Related concept expansion
        concepts = self._extract_concepts(query)
        if concepts:
            sub_queries.append(f"{query} {' '.join(concepts[:2])}")
        
        # 3. Meta-question (ask about the question itself)
        meta_q = f"What is the definition of {self._get_main_noun(query)}?"
        sub_queries.append(meta_q)
        
        return sub_queries[:self.fast_config.get("max_sub_queries", 2)]
    
    def _expand_synonyms(self, query: str) -> List[str]:
        """Simple synonym expansion (can be enhanced with WordNet)."""
        expansions = []
        
        # Manual synonym map (can be replaced with WordNet)
        synonyms_map = {
            "neural": ["deep learning", "neural nets"],
            "music": ["audio", "melody", "composition"],
            "learning": ["training", "optimization"],
        }
        
        for word, syns in synonyms_map.items():
            if word.lower() in query.lower():
                for syn in syns:
                    expansions.append(query.replace(word, syn, 1))
        
        return expansions
    
    def _extract_concepts(self, query: str) -> List[str]:
        """Extract key concepts from query."""
        # Simple noun extraction (can be enhanced with NLP)
        words = query.split()
        return [w for w in words if len(w) > 4][:3]
    
    def _get_main_noun(self, query: str) -> str:
        """Extract main noun from query."""
        words = query.split()
        return words[-1] if words else "topic"
    
    def _merge_and_rerank(
        self,
        existing: List[RetrievalResult],
        new: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Merge and re-rank results."""
        # Combine and de-duplicate by chunk_id
        merged_dict = {}
        
        for result in existing + new:
            key = result.chunk.chunk_id
            if key not in merged_dict or result.score > merged_dict[key].score:
                merged_dict[key] = result
        
        # Re-sort by score
        return sorted(merged_dict.values(), key=lambda x: -x.score)
    
    # ========================================================================
    # HELPER METHODS — REFLECTION
    # ========================================================================
    
    async def _score_answerability(
        self,
        query: str,
        answer: str,
        context: str
    ) -> float:
        """
        Score answerability of answer given context.
        Heuristics:
          - Does answer address the query directly?
          - Is there supporting context?
          - Is answer coherent?
        """
        score = 0.0
        
        # 1. Query overlap
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(query_words & answer_words) / max(len(query_words), 1)
        score += 0.3 * overlap
        
        # 2. Context relevance
        context_words = set(context.lower().split())
        context_overlap = len(query_words & context_words) / max(len(query_words), 1)
        score += 0.3 * context_overlap
        
        # 3. Answer length (non-zero is better)
        length_score = min(1.0, len(answer) / 200)
        score += 0.4 * length_score
        
        return min(1.0, score)
    
    def _compute_conflict_score(self, results: List[RetrievalResult]) -> float:
        """
        Compute conflict between top sources.
        Returns: [0, 1] where 0 = no conflict, 1 = high conflict
        """
        if len(results) < 2:
            return 0.0
        
        # Simple heuristic: if top 2 results are very different in score,
        # there's potential conflict
        top_2_scores = sorted([r.score for r in results], reverse=True)[:2]
        score_diff = (top_2_scores[0] - top_2_scores[1]) / max(top_2_scores[0], 0.1)
        
        # High score diff = low conflict, low score diff = high conflict
        conflict = 1.0 - min(1.0, score_diff)
        
        return conflict
    
    def _check_specificity(self, answer: str) -> float:
        """
        Check specificity of answer.
        Returns: [0, 1] where 1 = very specific
        """
        # Heuristics: specific answers have numbers, dates, cited sources
        specificity = 0.0
        
        # Check for numbers
        if any(c.isdigit() for c in answer):
            specificity += 0.3
        
        # Check for citations (e.g., [1], [2])
        if "[" in answer and "]" in answer:
            specificity += 0.4
        
        # Check length (longer = more specific)
        specificity += min(0.3, len(answer) / 500)
        
        return min(1.0, specificity)
    
    def _adjust_plan(self, plan: RetrievalPlan, reflection: ReflectionResult) -> RetrievalPlan:
        """Adjust retrieval plan based on reflection."""
        logger.info("plan_adjustment", old_confidence=reflection.confidence)
        
        # Relax constraints
        plan.reranker_threshold = max(0.3, plan.reranker_threshold - 0.1)
        plan.diversity_cap = min(0.6, plan.diversity_cap + 0.1)
        
        # Optionally: adjust fusion weights or category priorities
        
        return plan
    
    # ========================================================================
    # HELPER METHODS — DIVERSITY & COVERAGE
    # ========================================================================
    
    def _compute_diversity(self, results: List[RetrievalResult]) -> float:
        """
        Compute source diversity.
        Returns: [0, 1] where 1 = perfect diversity across docs
        """
        if not results:
            return 0.0
        
        # Count unique docs
        unique_docs = len(set(r.chunk.doc_id for r in results if r.chunk.doc_id))
        
        # Diversity score
        diversity = unique_docs / max(len(results), 1)
        
        return diversity
    
    def _estimate_coverage(self, results: List[RetrievalResult], query: str) -> float:
        """
        Estimate coverage of query by results.
        Returns: [0, 1] where 1 = full coverage
        """
        if not results:
            return 0.0
        
        # Simple heuristic: check if query words are in result texts
        query_words = set(query.lower().split())
        covered_words = set()
        
        for result in results[:10]:  # Check top 10
            result_words = set(result.chunk.text.lower().split())
            covered_words.update(query_words & result_words)
        
        coverage = len(covered_words) / max(len(query_words), 1)
        
        return min(1.0, coverage)
    
    # ========================================================================
    # REASONING
    # ========================================================================
    
    async def _reason(self, query: str, context: str) -> str:
        """
        Generate answer using LLM reasoner or mock.
        
        Args:
            query: User query
            context: Composed context from retrieval
        
        Returns:
            Answer text
        """
        if self.reasoner:
            # Use real reasoner
            prompt = f"""Based on the following context, answer the query concisely.

Query: {query}

Context:
{context}

Answer:"""
            answer = await self.reasoner.generate(prompt)
        else:
            # Mock answer (for testing)
            answer = f"Based on the context, here's an answer to '{query}': [This would be generated by an LLM]"
        
        return answer


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "HRMPlanner",
    "RetrievalPlan",
    "ReflectionResult"
]
