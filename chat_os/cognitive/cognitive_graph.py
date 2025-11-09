"""
Phase 6: Hypergraph Cognitive Topology

Implements graph-based cognitive state representation where:
- Nodes represent concepts, states, or knowledge fragments
- HyperEdges connect multiple nodes simultaneously (not just pairs)
- Enables complex reasoning chains and multi-way relationships

Traditional graphs: edge connects 2 nodes (A → B)
Hypergraphs: hyperedge connects N nodes ({A, B, C} → D)

This allows modeling:
- Complex causal relationships (multiple causes → effect)
- Multi-step reasoning chains (premise1, premise2, rule → conclusion)
- Contextual dependencies (fact + context → interpretation)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of cognitive nodes."""

    CONCEPT = "concept"  # Abstract concept or idea
    STATE = "state"  # System or cognitive state
    FACT = "fact"  # Known fact or observation
    RULE = "rule"  # Inference rule or heuristic
    GOAL = "goal"  # Desired outcome or objective
    ACTION = "action"  # Executable action
    MEMORY = "memory"  # Episodic memory fragment
    EMOTION = "emotion"  # Emotional state
    UNKNOWN = "unknown"


class EdgeType(Enum):
    """Types of hyperedge relationships."""

    IMPLIES = "implies"  # Logical implication
    CAUSES = "causes"  # Causal relationship
    REQUIRES = "requires"  # Dependency
    CONFLICTS = "conflicts"  # Contradiction
    SUPPORTS = "supports"  # Evidence/support
    TRANSFORMS = "transforms"  # State transition
    ASSOCIATES = "associates"  # General association
    DERIVES = "derives"  # Derivation/inference


@dataclass
class CognitiveNode:
    """
    A node in the cognitive hypergraph.

    Represents a concept, state, fact, or other cognitive element.
    """

    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_type: NodeType = NodeType.CONCEPT
    label: str = ""  # Human-readable label
    content: Any = None  # Node payload (data, embedding, etc.)
    metadata: dict[str, Any] = field(default_factory=dict)
    activation: float = 0.0  # Activation level [0-1] for spreading activation

    def __hash__(self) -> int:
        """Make node hashable for set/dict operations."""
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        """Equality based on node_id."""
        if not isinstance(other, CognitiveNode):
            return False
        return self.node_id == other.node_id


@dataclass
class HyperEdge:
    """
    A hyperedge connecting multiple nodes.

    Unlike traditional edges (connecting 2 nodes), hyperedges can connect
    any number of source nodes to any number of target nodes.
    """

    edge_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    edge_type: EdgeType = EdgeType.ASSOCIATES
    source_nodes: set[str] = field(default_factory=set)  # Node IDs
    target_nodes: set[str] = field(default_factory=set)  # Node IDs
    weight: float = 1.0  # Edge strength/confidence [0-1]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate edge has at least one source and target."""
        if not self.source_nodes or not self.target_nodes:
            raise ValueError("HyperEdge must have at least one source and one target")

    def involves_node(self, node_id: str) -> bool:
        """Check if edge involves a specific node."""
        return node_id in self.source_nodes or node_id in self.target_nodes

    def arity(self) -> tuple[int, int]:
        """Return (num_sources, num_targets)."""
        return (len(self.source_nodes), len(self.target_nodes))


@dataclass
class CognitiveHypergraph:
    """
    A hypergraph representing cognitive topology.

    Nodes represent concepts/states, hyperedges represent multi-way relationships.
    Supports complex reasoning through path traversal and spreading activation.
    """

    nodes: dict[str, CognitiveNode] = field(default_factory=dict)
    edges: dict[str, HyperEdge] = field(default_factory=dict)

    # Adjacency structures for efficient traversal
    _outgoing: dict[str, set[str]] = field(default_factory=dict)  # node_id -> edge_ids
    _incoming: dict[str, set[str]] = field(default_factory=dict)  # node_id -> edge_ids

    def add_node(
        self,
        node_type: NodeType = NodeType.CONCEPT,
        label: str = "",
        content: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> CognitiveNode:
        """Add a node to the hypergraph."""
        node = CognitiveNode(
            node_type=node_type,
            label=label,
            content=content,
            metadata=metadata or {},
        )
        self.nodes[node.node_id] = node
        self._outgoing[node.node_id] = set()
        self._incoming[node.node_id] = set()
        return node

    def add_edge(
        self,
        source_nodes: list[CognitiveNode] | list[str],
        target_nodes: list[CognitiveNode] | list[str],
        edge_type: EdgeType = EdgeType.ASSOCIATES,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> HyperEdge:
        """
        Add a hyperedge connecting source nodes to target nodes.

        Args:
            source_nodes: List of nodes or node IDs (sources)
            target_nodes: List of nodes or node IDs (targets)
            edge_type: Type of relationship
            weight: Edge strength [0-1]
            metadata: Additional edge data

        Returns:
            Created hyperedge
        """
        # Convert nodes to IDs
        source_ids = set()
        for node in source_nodes:
            node_id = node.node_id if isinstance(node, CognitiveNode) else node
            if node_id not in self.nodes:
                raise ValueError(f"Source node {node_id} not in graph")
            source_ids.add(node_id)

        target_ids = set()
        for node in target_nodes:
            node_id = node.node_id if isinstance(node, CognitiveNode) else node
            if node_id not in self.nodes:
                raise ValueError(f"Target node {node_id} not in graph")
            target_ids.add(node_id)

        edge = HyperEdge(
            edge_type=edge_type,
            source_nodes=source_ids,
            target_nodes=target_ids,
            weight=weight,
            metadata=metadata or {},
        )

        self.edges[edge.edge_id] = edge

        # Update adjacency structures
        for src_id in source_ids:
            self._outgoing[src_id].add(edge.edge_id)
        for tgt_id in target_ids:
            self._incoming[tgt_id].add(edge.edge_id)

        return edge

    def get_node(self, node_id: str) -> CognitiveNode | None:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> HyperEdge | None:
        """Get edge by ID."""
        return self.edges.get(edge_id)

    def get_neighbors(
        self, node_id: str, direction: str = "outgoing"
    ) -> set[CognitiveNode]:
        """
        Get neighboring nodes.

        Args:
            node_id: Source node ID
            direction: 'outgoing', 'incoming', or 'both'

        Returns:
            Set of neighboring nodes
        """
        neighbors = set()

        if direction in ("outgoing", "both"):
            for edge_id in self._outgoing.get(node_id, set()):
                edge = self.edges[edge_id]
                for target_id in edge.target_nodes:
                    neighbors.add(self.nodes[target_id])

        if direction in ("incoming", "both"):
            for edge_id in self._incoming.get(node_id, set()):
                edge = self.edges[edge_id]
                for source_id in edge.source_nodes:
                    neighbors.add(self.nodes[source_id])

        return neighbors

    def find_paths(
        self,
        start_node_id: str,
        end_node_id: str,
        max_depth: int = 5,
    ) -> list[list[str]]:
        """
        Find paths between two nodes using BFS.

        Args:
            start_node_id: Starting node ID
            end_node_id: Target node ID
            max_depth: Maximum path length

        Returns:
            List of paths (each path is list of node IDs)
        """
        if start_node_id not in self.nodes or end_node_id not in self.nodes:
            return []

        paths: list[list[str]] = []
        queue: list[tuple[str, list[str]]] = [(start_node_id, [start_node_id])]
        visited: set[tuple[str, ...]] = set()

        while queue:
            current_id, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            if current_id == end_node_id:
                paths.append(path)
                continue

            # Explore neighbors
            for neighbor in self.get_neighbors(current_id, "outgoing"):
                if neighbor.node_id not in path:  # Avoid cycles
                    new_path = path + [neighbor.node_id]
                    path_tuple = tuple(new_path)
                    if path_tuple not in visited:
                        visited.add(path_tuple)
                        queue.append((neighbor.node_id, new_path))

        return paths

    def spreading_activation(
        self,
        start_nodes: list[str],
        num_iterations: int = 3,
        decay: float = 0.5,
        threshold: float = 0.1,
    ) -> dict[str, float]:
        """
        Perform spreading activation from start nodes.

        Activation spreads through the graph, decaying at each step.
        Models how concepts activate related concepts in cognition.

        Args:
            start_nodes: Initial activated node IDs
            num_iterations: Number of spreading iterations
            decay: Activation decay factor per step (0-1)
            threshold: Minimum activation to spread

        Returns:
            Dict mapping node_id to final activation level
        """
        # Initialize activations
        activations = {node_id: 0.0 for node_id in self.nodes}
        for node_id in start_nodes:
            if node_id in activations:
                activations[node_id] = 1.0

        # Spread activation
        for _ in range(num_iterations):
            new_activations = activations.copy()

            for node_id, activation in activations.items():
                if activation < threshold:
                    continue

                # Spread to neighbors
                neighbors = self.get_neighbors(node_id, "outgoing")
                if not neighbors:
                    continue

                spread_amount = activation * decay / len(neighbors)

                for neighbor in neighbors:
                    new_activations[neighbor.node_id] = max(
                        new_activations[neighbor.node_id],
                        new_activations[neighbor.node_id] + spread_amount,
                    )

            activations = new_activations

        return {k: v for k, v in activations.items() if v >= threshold}

    def get_subgraph(
        self, node_ids: set[str], include_connecting_edges: bool = True
    ) -> CognitiveHypergraph:
        """
        Extract subgraph containing specified nodes.

        Args:
            node_ids: Set of node IDs to include
            include_connecting_edges: Whether to include edges between nodes

        Returns:
            New hypergraph containing only specified nodes
        """
        subgraph = CognitiveHypergraph()

        # Add nodes
        for node_id in node_ids:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                # Create new node with same ID
                new_node = CognitiveNode(
                    node_type=node.node_type,
                    label=node.label,
                    content=node.content,
                    metadata=node.metadata.copy(),
                    activation=node.activation,
                )
                # Override with original ID
                new_node.node_id = node_id
                subgraph.nodes[node_id] = new_node
                # Initialize adjacency structures
                subgraph._outgoing[node_id] = set()
                subgraph._incoming[node_id] = set()

        # Add edges if requested
        if include_connecting_edges:
            for edge in self.edges.values():
                # Include edge if all its nodes are in subgraph
                if edge.source_nodes.issubset(node_ids) and edge.target_nodes.issubset(
                    node_ids
                ):
                    subgraph.add_edge(
                        source_nodes=list(edge.source_nodes),
                        target_nodes=list(edge.target_nodes),
                        edge_type=edge.edge_type,
                        weight=edge.weight,
                        metadata=edge.metadata.copy(),
                    )

        return subgraph

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        node_type_counts = {}
        for node in self.nodes.values():
            node_type = node.node_type.value
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

        edge_type_counts = {}
        for edge in self.edges.values():
            edge_type = edge.edge_type.value
            edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1

        # Calculate hyperedge arities
        arities = [edge.arity() for edge in self.edges.values()]
        avg_sources = sum(a[0] for a in arities) / len(arities) if arities else 0
        avg_targets = sum(a[1] for a in arities) / len(arities) if arities else 0

        return {
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "node_types": node_type_counts,
            "edge_types": edge_type_counts,
            "avg_sources_per_edge": avg_sources,
            "avg_targets_per_edge": avg_targets,
        }

    def clear(self) -> None:
        """Clear all nodes and edges."""
        self.nodes.clear()
        self.edges.clear()
        self._outgoing.clear()
        self._incoming.clear()


def get_cognitive_graph() -> CognitiveHypergraph:
    """Get global cognitive hypergraph singleton."""
    global _cognitive_graph
    if "_cognitive_graph" not in globals():
        _cognitive_graph = CognitiveHypergraph()
    return _cognitive_graph


# Example usage
if __name__ == "__main__":
    graph = CognitiveHypergraph()

    # Create nodes
    python = graph.add_node(NodeType.CONCEPT, "Python", content="programming language")
    file = graph.add_node(NodeType.CONCEPT, "File", content="data container")
    read = graph.add_node(NodeType.ACTION, "Read", content="read operation")
    data = graph.add_node(NodeType.STATE, "Data", content="loaded data")

    # Create hyperedge: (Python, File) --REQUIRES--> Read --PRODUCES--> Data
    # This shows: reading a file in Python requires both concepts and produces data
    graph.add_edge([python, file], [read], EdgeType.REQUIRES, weight=0.9)
    graph.add_edge([read], [data], EdgeType.TRANSFORMS, weight=1.0)

    # Find reasoning paths
    paths = graph.find_paths(python.node_id, data.node_id)
    print(f"Paths from Python to Data: {len(paths)}")

    # Spreading activation
    activations = graph.spreading_activation([python.node_id], num_iterations=2)
    print(f"\nActivated nodes from Python:")
    for node_id, activation in sorted(
        activations.items(), key=lambda x: x[1], reverse=True
    ):
        node = graph.get_node(node_id)
        print(f"  {node.label}: {activation:.3f}")  # type: ignore

    # Statistics
    stats = graph.get_stats()
    print(f"\nGraph stats: {stats['num_nodes']} nodes, {stats['num_edges']} edges")
