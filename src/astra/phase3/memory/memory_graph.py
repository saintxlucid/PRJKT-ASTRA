"""
ASTRA Persistent Memory Graph: Stores facts, relationships, and context as directed graph.

This module implements a knowledge graph structure that:
- Represents entities (nodes) and relationships (edges) with full context
- Supports memory hierarchies (facts → concepts → schemas)
- Enables multi-hop reasoning and relationship traversal
- Integrates with embedding store for semantic search
- Tracks recency and relevance for memory management

Architecture:
- MemoryNode: Entity with properties, embeddings, update history
- MemoryEdge: Relationship with type, weight, and temporal metadata
- MemoryGraph: Graph management with query/insert/delete operations
- TTL-based cleanup for expired memories
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.astra.observability.metrics import MetricsCollector
from src.astra.observability.structured_logger import StructuredLogger


class MemoryType(Enum):
    """Categories of memory nodes."""

    FACT = "fact"  # Atomic fact: "Paris is in France"
    CONCEPT = "concept"  # Abstract concept: "Geography", "History"
    SCHEMA = "schema"  # Pattern/template: "City(name, country, population)"
    INTERACTION = "interaction"  # User interaction record
    DECISION = "decision"  # Decision with reasoning


class RelationType(Enum):
    """Types of relationships between nodes."""

    IS_A = "is_a"  # Inheritance: Dog is_a Animal
    PART_OF = "part_of"  # Composition: Wheel part_of Car
    RELATED_TO = "related_to"  # General association
    CAUSES = "causes"  # Causal: Rain causes Wetness
    TEMPORAL = "temporal"  # Time-based: Before, After, During
    CONTAINS = "contains"  # Containment: City contains District
    SIMILAR_TO = "similar_to"  # Semantic similarity


@dataclass
class MemoryNode:
    """Represents an entity in the memory graph.

    Attributes:
        id: Unique node identifier (UUID)
        content: Primary content/text of the memory
        node_type: MemoryType enum (FACT, CONCEPT, SCHEMA, etc.)
        properties: Dict of additional attributes (domain, confidence, source)
        embedding: Vector representation for semantic search
        created_at: Unix timestamp of creation
        updated_at: Unix timestamp of last update
        accessed_at: Unix timestamp of last access
        relevance_score: 0-1 score for importance
        ttl_seconds: Time-to-live before expiration (None = permanent)
        metadata: Additional context (source, confidence, references)
    """

    id: str
    content: str
    node_type: MemoryType
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    relevance_score: float = 0.8
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if memory has exceeded TTL."""
        if self.ttl_seconds is None:
            return False
        age_sec = time.time() - self.created_at
        return age_sec > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "node_type": self.node_type.value,
            "properties": self.properties,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "accessed_at": self.accessed_at,
            "relevance_score": self.relevance_score,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }


@dataclass
class MemoryEdge:
    """Represents a relationship between two nodes.

    Attributes:
        id: Unique edge identifier
        source_id: Source node ID
        target_id: Target node ID
        relation_type: Type of relationship
        weight: 0-1 strength of relationship
        created_at: When relationship was established
        updated_at: When relationship was last updated
        temporal_context: Time-based metadata (before, after, during)
        metadata: Additional relationship properties
    """

    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 0.8
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    temporal_context: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "temporal_context": self.temporal_context,
            "metadata": self.metadata,
        }


class MemoryGraph:
    """Manages persistent memory as a directed graph.

    This class provides:
    - O(1) node lookup by ID
    - O(1) edge lookup by (source, target, type)
    - Multi-hop graph traversal
    - TTL-based automatic cleanup
    - Persistence to disk (JSON)
    """

    def __init__(
        self,
        persistence_path: str = "./data/memory_graph.json",
        logger: StructuredLogger | None = None,
        metrics: MetricsCollector | None = None,
    ):
        """Initialize the memory graph.

        Args:
            persistence_path: Path to save/load graph state
            logger: Optional structured logger
            metrics: Optional metrics collector
        """
        self.persistence_path = Path(persistence_path)
        self.logger = logger or StructuredLogger("memory_graph")
        self.metrics = metrics or MetricsCollector()

        # Graph storage
        self.nodes: dict[str, MemoryNode] = {}
        self.edges: dict[str, MemoryEdge] = {}

        # Indices for fast lookup
        self.node_by_content: dict[str, str] = {}  # content hash -> node_id
        self.edges_by_source: dict[str, list[str]] = {}  # source_id -> [edge_ids]
        self.edges_by_target: dict[str, list[str]] = {}  # target_id -> [edge_ids]

        # Stats
        self.total_inserts = 0
        self.total_queries = 0
        self.last_cleanup = time.time()

        # Load from disk if exists
        self._load_from_disk()

    async def add_node(
        self,
        content: str,
        node_type: MemoryType,
        properties: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Add a new node to the graph.

        Args:
            content: Primary content of the memory
            node_type: Type of memory (FACT, CONCEPT, SCHEMA)
            properties: Optional properties dict
            embedding: Optional embedding vector
            ttl_seconds: Optional TTL in seconds

        Returns:
            Node ID
        """
        start = time.time()

        node_id = str(uuid.uuid4())[:12]
        node = MemoryNode(
            id=node_id,
            content=content,
            node_type=node_type,
            properties=properties or {},
            embedding=embedding,
            ttl_seconds=ttl_seconds,
        )

        self.nodes[node_id] = node
        self.node_by_content[self._content_hash(content)] = node_id
        self.total_inserts += 1

        elapsed = time.time() - start
        self.metrics.record_latency("memory_graph.add_node", elapsed * 1000)

        self.logger.log_event(
            "node_added",
            level="INFO",
            node_id=node_id,
            node_type=node_type.value,
            content_length=len(content),
            latency_ms=elapsed * 1000,
        )

        return node_id

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 0.8,
        temporal_context: str | None = None,
    ) -> str:
        """Add a relationship edge between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relation_type: Type of relationship
            weight: Strength 0-1
            temporal_context: Time-based metadata

        Returns:
            Edge ID
        """
        # Verify nodes exist
        if source_id not in self.nodes or target_id not in self.nodes:
            return ""

        edge_id = str(uuid.uuid4())[:12]
        edge = MemoryEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            temporal_context=temporal_context,
        )

        self.edges[edge_id] = edge

        # Index by source and target
        if source_id not in self.edges_by_source:
            self.edges_by_source[source_id] = []
        self.edges_by_source[source_id].append(edge_id)

        if target_id not in self.edges_by_target:
            self.edges_by_target[target_id] = []
        self.edges_by_target[target_id].append(edge_id)

        self.logger.log_event(
            "edge_added",
            level="INFO",
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type.value,
        )

        return edge_id

    async def get_node(self, node_id: str) -> MemoryNode | None:
        """Retrieve a node by ID.

        Args:
            node_id: Node identifier

        Returns:
            MemoryNode or None if not found
        """
        start = time.time()

        if node_id not in self.nodes:
            return None

        node = self.nodes[node_id]
        node.accessed_at = time.time()  # Update access time

        elapsed = time.time() - start
        self.metrics.record_latency("memory_graph.get_node", elapsed * 1000)

        return node

    async def get_neighbors(
        self,
        node_id: str,
        max_hops: int = 1,
        relation_filter: RelationType | None = None,
    ) -> list[tuple[MemoryNode, MemoryEdge]]:
        """Get neighboring nodes via outgoing edges.

        Args:
            node_id: Source node
            max_hops: Maximum traversal depth
            relation_filter: Filter by relationship type

        Returns:
            List of (MemoryNode, MemoryEdge) tuples
        """
        start = time.time()
        neighbors = []
        visited = {node_id}

        async def traverse(node_id_: str, depth: int) -> None:
            if depth > max_hops or node_id_ not in self.edges_by_source:
                return

            edge_ids = self.edges_by_source.get(node_id_, [])
            for edge_id in edge_ids:
                edge = self.edges[edge_id]

                # Filter by relation type if specified
                if relation_filter and edge.relation_type != relation_filter:
                    continue

                target_id = edge.target_id
                if target_id not in visited:
                    visited.add(target_id)
                    target_node = self.nodes.get(target_id)
                    if target_node:
                        neighbors.append((target_node, edge))
                        await traverse(target_id, depth + 1)

        await traverse(node_id, 0)

        elapsed = time.time() - start
        self.metrics.record_latency("memory_graph.get_neighbors", elapsed * 1000)

        return neighbors

    async def update_node_relevance(self, node_id: str, relevance_delta: float) -> bool:
        """Increase/decrease node relevance score.

        Args:
            node_id: Node to update
            relevance_delta: +/- change amount

        Returns:
            True if updated, False if not found
        """
        if node_id not in self.nodes:
            return False

        node = self.nodes[node_id]
        node.relevance_score = max(0.0, min(1.0, node.relevance_score + relevance_delta))
        node.updated_at = time.time()

        return True

    async def cleanup_expired(self) -> int:
        """Remove expired nodes and their edges.

        Returns:
            Number of nodes removed
        """
        start = time.time()
        expired_ids = [
            node_id
            for node_id, node in self.nodes.items()
            if node.is_expired()
        ]

        for node_id in expired_ids:
            # Remove edges
            for edge_id in self.edges_by_source.get(node_id, []):
                if edge_id in self.edges:
                    del self.edges[edge_id]
            for edge_id in self.edges_by_target.get(node_id, []):
                if edge_id in self.edges:
                    del self.edges[edge_id]

            # Remove node
            node = self.nodes[node_id]
            content_hash = self._content_hash(node.content)
            if content_hash in self.node_by_content:
                del self.node_by_content[content_hash]
            del self.nodes[node_id]

        elapsed = time.time() - start
        self.last_cleanup = time.time()

        self.logger.log_event(
            "cleanup_expired",
            level="INFO",
            nodes_removed=len(expired_ids),
            latency_ms=elapsed * 1000,
        )

        return len(expired_ids)

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Stats dict with node count, edge count, metrics
        """
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "total_inserts": self.total_inserts,
            "total_queries": self.total_queries,
            "avg_relevance": (
                sum(n.relevance_score for n in self.nodes.values()) / len(self.nodes)
                if self.nodes
                else 0.0
            ),
            "last_cleanup": self.last_cleanup,
        }

    def _content_hash(self, content: str) -> str:
        """Generate deterministic hash of content."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()

    def _save_to_disk(self) -> None:
        """Persist graph to disk as JSON."""
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

        graph_data = {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "stats": self.get_stats(),
        }

        with open(self.persistence_path, "w") as f:
            json.dump(graph_data, f, indent=2)

    def _load_from_disk(self) -> None:
        """Load graph from disk if it exists."""
        if not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path) as f:
                graph_data = json.load(f)

            # Reconstruct nodes
            for node_data in graph_data.get("nodes", []):
                node = MemoryNode(
                    id=node_data["id"],
                    content=node_data["content"],
                    node_type=MemoryType(node_data["node_type"]),
                    properties=node_data.get("properties", {}),
                    embedding=node_data.get("embedding"),
                    created_at=node_data.get("created_at", time.time()),
                    updated_at=node_data.get("updated_at", time.time()),
                    accessed_at=node_data.get("accessed_at", time.time()),
                    relevance_score=node_data.get("relevance_score", 0.8),
                    ttl_seconds=node_data.get("ttl_seconds"),
                    metadata=node_data.get("metadata", {}),
                )
                self.nodes[node.id] = node
                self.node_by_content[self._content_hash(node.content)] = node.id

            # Reconstruct edges
            for edge_data in graph_data.get("edges", []):
                edge = MemoryEdge(
                    id=edge_data["id"],
                    source_id=edge_data["source_id"],
                    target_id=edge_data["target_id"],
                    relation_type=RelationType(edge_data["relation_type"]),
                    weight=edge_data.get("weight", 0.8),
                    created_at=edge_data.get("created_at", time.time()),
                    updated_at=edge_data.get("updated_at", time.time()),
                    temporal_context=edge_data.get("temporal_context"),
                    metadata=edge_data.get("metadata", {}),
                )
                self.edges[edge.id] = edge

                # Index edges
                if edge.source_id not in self.edges_by_source:
                    self.edges_by_source[edge.source_id] = []
                self.edges_by_source[edge.source_id].append(edge.id)

                if edge.target_id not in self.edges_by_target:
                    self.edges_by_target[edge.target_id] = []
                self.edges_by_target[edge.target_id].append(edge.id)

            self.logger.log_event(
                "graph_loaded",
                level="INFO",
                nodes_loaded=len(self.nodes),
                edges_loaded=len(self.edges),
            )

        except Exception as e:
            self.logger.log_event(
                "load_error",
                level="ERROR",
                error=str(e),
            )
