"""
ASTRA Recall Engine: Multi-tier memory retrieval with BM25 + semantic search.

This module implements:
- BM25 keyword-based ranking for lexical match
- Semantic embedding search for meaning-based match
- Hybrid scoring combining both signals
- Multi-hop graph traversal for context expansion
- Caching and ranking optimization
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from src.astra.observability.metrics import MetricsCollector
from src.astra.observability.structured_logger import StructuredLogger
from src.astra.phase3.memory.embedding_store import EmbeddingStore
from src.astra.phase3.memory.memory_graph import MemoryGraph


@dataclass
class RecallResult:
    """Result from memory recall.

    Attributes:
        node_id: Memory node identifier
        content: Memory content
        score: Relevance score 0-1
        rank: Position in result ranking
        source: "bm25" or "semantic" indicating search method
        metadata: Additional context
    """

    node_id: str
    content: str
    score: float
    rank: int
    source: str
    metadata: dict[str, Any]


class RecallEngine:
    """Multi-tier memory retrieval optimized for <300ms P95 latency.

    Combines:
    1. BM25 keyword matching (fast, lexical)
    2. Semantic embedding search (accurate, meaning-based)
    3. Graph traversal (context expansion)
    4. Ranking fusion (combined scoring)
    """

    def __init__(
        self,
        memory_graph: MemoryGraph,
        embedding_store: EmbeddingStore,
        logger: StructuredLogger | None = None,
        metrics: MetricsCollector | None = None,
    ):
        """Initialize recall engine.

        Args:
            memory_graph: MemoryGraph instance
            embedding_store: EmbeddingStore instance
            logger: Optional structured logger
            metrics: Optional metrics collector
        """
        self.memory_graph = memory_graph
        self.embedding_store = embedding_store
        self.logger = logger or StructuredLogger("recall_engine")
        self.metrics = metrics or MetricsCollector()

        # BM25 parameters
        self.k1 = 1.5  # Term frequency saturation
        self.b = 0.75  # Field length normalization

        # Cache
        self.recall_cache: dict[str, list[RecallResult]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    async def recall(
        self,
        query: str,
        embedding: list[float] | None = None,
        k: int = 10,
        use_semantic: bool = True,
        use_bm25: bool = True,
        expand_hops: int = 0,
    ) -> list[RecallResult]:
        """Retrieve relevant memories.

        Args:
            query: Search query text
            embedding: Optional pre-computed query embedding
            k: Number of results
            use_semantic: Enable semantic search
            use_bm25: Enable BM25 keyword search
            expand_hops: Graph expansion depth (0 = no expansion)

        Returns:
            Ranked list of RecallResult
        """
        start = time.time()

        # Check cache
        cache_key = f"{query}:{k}:{expand_hops}"
        if cache_key in self.recall_cache:
            self.cache_hits += 1
            return self.recall_cache[cache_key]

        self.cache_misses += 1
        results = []

        # Tier 1: BM25 keyword search
        if use_bm25:
            bm25_results = await self._search_bm25(query, k)
            results.extend(bm25_results)

        # Tier 2: Semantic search
        if use_semantic and embedding:
            semantic_results = await self._search_semantic(
                embedding,
                k,
                exclude_ids={r.node_id for r in results},
            )
            results.extend(semantic_results)

        # Tier 3: Graph expansion for context
        if expand_hops > 0 and results:
            expanded_results = await self._expand_with_graph(
                results,
                expand_hops,
                k,
            )
            results.extend(expanded_results)

        # Deduplicate and re-rank
        unique_results = {}
        for result in results:
            if result.node_id not in unique_results:
                unique_results[result.node_id] = result
            else:
                # Take higher score
                if result.score > unique_results[result.node_id].score:
                    unique_results[result.node_id] = result

        # Sort by score and rank
        final_results = sorted(
            unique_results.values(),
            key=lambda x: x.score,
            reverse=True,
        )[:k]

        for rank, result in enumerate(final_results, 1):
            result.rank = rank

        # Cache result
        self.recall_cache[cache_key] = final_results

        elapsed = time.time() - start
        self.metrics.record_latency("recall_engine.recall", elapsed * 1000)

        self.logger.log_event(
            "recall_completed",
            level="INFO",
            query_length=len(query),
            results_found=len(final_results),
            latency_ms=elapsed * 1000,
        )

        return final_results

    async def _search_bm25(
        self,
        query: str,
        k: int,
    ) -> list[RecallResult]:
        """BM25 keyword-based search.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of RecallResult with BM25 scores
        """
        query_terms = query.lower().split()
        scores: dict[str, float] = {}

        # Compute BM25 score for each node
        for node_id, node in self.memory_graph.nodes.items():
            content_terms = node.content.lower().split()
            doc_length = len(content_terms)

            score = 0.0
            for term in query_terms:
                # Term frequency in document
                tf = sum(1 for t in content_terms if t == term)
                if tf == 0:
                    continue

                # BM25 formula
                avg_doc_length = (
                    sum(len(n.content.split()) for n in self.memory_graph.nodes.values())
                    / max(len(self.memory_graph.nodes), 1)
                )

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_length / max(avg_doc_length, 1))
                )
                bm25_component = numerator / denominator

                score += bm25_component

            if score > 0:
                scores[node_id] = score

        # Sort and return top k
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]

        results = []
        for rank, (node_id, score) in enumerate(sorted_nodes, 1):
            node = self.memory_graph.nodes[node_id]
            results.append(
                RecallResult(
                    node_id=node_id,
                    content=node.content,
                    score=min(score / 10.0, 1.0),  # Normalize to 0-1
                    rank=rank,
                    source="bm25",
                    metadata={"node_type": node.node_type.value},
                )
            )

        return results

    async def _search_semantic(
        self,
        query_embedding: list[float],
        k: int,
        exclude_ids: set[str] | None = None,
    ) -> list[RecallResult]:
        """Semantic embedding-based search.

        Args:
            query_embedding: Query embedding vector
            k: Number of results
            exclude_ids: Optional set of IDs to exclude

        Returns:
            List of RecallResult with semantic scores
        """
        exclude_ids = exclude_ids or set()

        # Search embeddings
        search_results = await self.embedding_store.search(
            query_embedding,
            k=k * 2,  # Get more to filter
        )

        results = []
        for rank, (vector_id, score) in enumerate(search_results, 1):
            if vector_id in exclude_ids:
                continue

            node = self.memory_graph.nodes.get(vector_id)
            if node:
                results.append(
                    RecallResult(
                        node_id=vector_id,
                        content=node.content,
                        score=score,
                        rank=rank,
                        source="semantic",
                        metadata={"node_type": node.node_type.value},
                    )
                )

                if len(results) >= k:
                    break

        return results

    async def _expand_with_graph(
        self,
        initial_results: list[RecallResult],
        hops: int,
        k: int,
    ) -> list[RecallResult]:
        """Expand recall with graph traversal.

        Args:
            initial_results: Initial recall results
            hops: Number of hops to traverse
            k: Max additional results

        Returns:
            List of expanded RecallResult
        """
        expanded = []
        visited = {r.node_id for r in initial_results}

        for result in initial_results[:k]:
            neighbors = await self.memory_graph.get_neighbors(
                result.node_id,
                max_hops=hops,
            )

            for neighbor_node, edge in neighbors:
                if neighbor_node.id in visited:
                    continue

                visited.add(neighbor_node.id)

                # Score based on edge weight and node relevance
                combined_score = (edge.weight + neighbor_node.relevance_score) / 2

                expanded.append(
                    RecallResult(
                        node_id=neighbor_node.id,
                        content=neighbor_node.content,
                        score=combined_score,
                        rank=len(expanded),
                        source="graph_expansion",
                        metadata={
                            "node_type": neighbor_node.node_type.value,
                            "relation_type": edge.relation_type.value,
                        },
                    )
                )

                if len(expanded) >= k:
                    break

        return expanded

    def get_stats(self) -> dict[str, Any]:
        """Get recall engine statistics.

        Returns:
            Stats dict with cache performance
        """
        total_lookups = self.cache_hits + self.cache_misses
        hit_rate = (
            self.cache_hits / total_lookups if total_lookups > 0 else 0.0
        )

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": hit_rate,
            "cache_size": len(self.recall_cache),
        }

    def clear_cache(self) -> None:
        """Clear recall cache."""
        self.recall_cache.clear()
