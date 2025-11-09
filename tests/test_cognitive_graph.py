"""
Test Phase 6: Hypergraph Cognitive Topology

Validates graph-based cognitive state representation with:
- Node creation and management
- Hyperedge connections (multi-way relationships)
- Path finding between nodes
- Spreading activation
- Subgraph extraction
- Reasoning chains
"""

from chat_os.cognitive.cognitive_graph import (
    CognitiveHypergraph,
    CognitiveNode,
    EdgeType,
    HyperEdge,
    NodeType,
    get_cognitive_graph,
)


def test_node_creation():
    """CognitiveNode creates with valid attributes."""
    node = CognitiveNode(
        node_type=NodeType.CONCEPT,
        label="Test Concept",
        content="test data",
        metadata={"key": "value"},
    )

    assert node.node_type == NodeType.CONCEPT
    assert node.label == "Test Concept"
    assert node.content == "test data"
    assert node.metadata["key"] == "value"
    assert node.node_id is not None
    assert node.activation == 0.0


def test_node_equality():
    """Nodes are equal based on node_id."""
    node1 = CognitiveNode(node_type=NodeType.CONCEPT, label="A")
    node2 = CognitiveNode(node_type=NodeType.CONCEPT, label="B")

    # Different nodes
    assert node1 != node2

    # Same node
    assert node1 == node1

    # Node hashable
    node_set = {node1, node2}
    assert len(node_set) == 2


def test_hyperedge_creation():
    """HyperEdge creates with source and target nodes."""
    edge = HyperEdge(
        edge_type=EdgeType.IMPLIES,
        source_nodes={"node1", "node2"},
        target_nodes={"node3"},
        weight=0.8,
    )

    assert edge.edge_type == EdgeType.IMPLIES
    assert "node1" in edge.source_nodes
    assert "node2" in edge.source_nodes
    assert "node3" in edge.target_nodes
    assert edge.weight == 0.8


def test_hyperedge_validation():
    """HyperEdge validates at least one source and target."""
    # Valid edge
    HyperEdge(source_nodes={"a"}, target_nodes={"b"})

    # Invalid - no sources
    try:
        HyperEdge(source_nodes=set(), target_nodes={"b"})
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "at least one source" in str(e).lower()


def test_hyperedge_arity():
    """HyperEdge reports arity (num sources, num targets)."""
    edge = HyperEdge(
        source_nodes={"a", "b", "c"},
        target_nodes={"d", "e"},
    )

    arity = edge.arity()
    assert arity == (3, 2)


def test_hyperedge_involves_node():
    """HyperEdge checks if it involves a node."""
    edge = HyperEdge(
        source_nodes={"a", "b"},
        target_nodes={"c"},
    )

    assert edge.involves_node("a")
    assert edge.involves_node("b")
    assert edge.involves_node("c")
    assert not edge.involves_node("d")


def test_graph_add_node():
    """Graph adds nodes correctly."""
    graph = CognitiveHypergraph()

    node = graph.add_node(
        node_type=NodeType.FACT,
        label="Test Fact",
        content="fact data",
    )

    assert len(graph.nodes) == 1
    assert node.node_id in graph.nodes
    assert graph.get_node(node.node_id) == node


def test_graph_add_edge():
    """Graph adds hyperedges between nodes."""
    graph = CognitiveHypergraph()

    node1 = graph.add_node(NodeType.CONCEPT, "A")
    node2 = graph.add_node(NodeType.CONCEPT, "B")
    node3 = graph.add_node(NodeType.CONCEPT, "C")

    edge = graph.add_edge(
        source_nodes=[node1, node2],
        target_nodes=[node3],
        edge_type=EdgeType.IMPLIES,
        weight=0.9,
    )

    assert len(graph.edges) == 1
    assert node1.node_id in edge.source_nodes
    assert node2.node_id in edge.source_nodes
    assert node3.node_id in edge.target_nodes


def test_graph_add_edge_by_id():
    """Graph adds edges using node IDs."""
    graph = CognitiveHypergraph()

    node1 = graph.add_node(NodeType.CONCEPT, "A")
    node2 = graph.add_node(NodeType.CONCEPT, "B")

    edge = graph.add_edge(
        source_nodes=[node1.node_id],
        target_nodes=[node2.node_id],
        edge_type=EdgeType.CAUSES,
    )

    assert edge.edge_type == EdgeType.CAUSES


def test_graph_get_neighbors():
    """Graph retrieves neighboring nodes."""
    graph = CognitiveHypergraph()

    a = graph.add_node(NodeType.CONCEPT, "A")
    b = graph.add_node(NodeType.CONCEPT, "B")
    c = graph.add_node(NodeType.CONCEPT, "C")

    graph.add_edge([a], [b], EdgeType.IMPLIES)
    graph.add_edge([b], [c], EdgeType.IMPLIES)

    # Outgoing neighbors of A
    neighbors = graph.get_neighbors(a.node_id, "outgoing")
    assert len(neighbors) == 1
    assert b in neighbors

    # Incoming neighbors of C
    neighbors = graph.get_neighbors(c.node_id, "incoming")
    assert len(neighbors) == 1
    assert b in neighbors

    # Both directions for B
    neighbors = graph.get_neighbors(b.node_id, "both")
    assert len(neighbors) == 2
    assert a in neighbors
    assert c in neighbors


def test_graph_find_paths():
    """Graph finds paths between nodes."""
    graph = CognitiveHypergraph()

    a = graph.add_node(NodeType.CONCEPT, "A")
    b = graph.add_node(NodeType.CONCEPT, "B")
    c = graph.add_node(NodeType.CONCEPT, "C")
    d = graph.add_node(NodeType.CONCEPT, "D")

    # Create path: A -> B -> C -> D
    graph.add_edge([a], [b], EdgeType.IMPLIES)
    graph.add_edge([b], [c], EdgeType.IMPLIES)
    graph.add_edge([c], [d], EdgeType.IMPLIES)

    # Also: A -> D (shortcut)
    graph.add_edge([a], [d], EdgeType.IMPLIES)

    paths = graph.find_paths(a.node_id, d.node_id, max_depth=5)

    # Should find at least 2 paths: direct and through B,C
    assert len(paths) >= 2

    # Check for direct path
    direct_path = [a.node_id, d.node_id]
    assert direct_path in paths

    # Check for long path
    long_path = [a.node_id, b.node_id, c.node_id, d.node_id]
    assert long_path in paths


def test_graph_spreading_activation():
    """Graph performs spreading activation."""
    graph = CognitiveHypergraph()

    a = graph.add_node(NodeType.CONCEPT, "A")
    b = graph.add_node(NodeType.CONCEPT, "B")
    c = graph.add_node(NodeType.CONCEPT, "C")

    graph.add_edge([a], [b], EdgeType.ASSOCIATES)
    graph.add_edge([b], [c], EdgeType.ASSOCIATES)

    # Activate A
    activations = graph.spreading_activation(
        start_nodes=[a.node_id],
        num_iterations=2,
        decay=0.5,
        threshold=0.1,
    )

    # A should be most activated
    assert activations[a.node_id] == 1.0

    # B should be activated (direct neighbor)
    assert a.node_id in activations
    assert b.node_id in activations

    # C might be activated (2 steps away, depends on threshold)
    # Just verify activations are in [0, 1]
    for activation in activations.values():
        assert 0.0 <= activation <= 1.0


def test_graph_subgraph_extraction():
    """Graph extracts subgraphs."""
    graph = CognitiveHypergraph()

    a = graph.add_node(NodeType.CONCEPT, "A")
    b = graph.add_node(NodeType.CONCEPT, "B")
    c = graph.add_node(NodeType.CONCEPT, "C")
    d = graph.add_node(NodeType.CONCEPT, "D")

    graph.add_edge([a], [b], EdgeType.IMPLIES)
    graph.add_edge([b], [c], EdgeType.IMPLIES)
    graph.add_edge([c], [d], EdgeType.IMPLIES)

    # Extract subgraph with A and B
    subgraph = graph.get_subgraph({a.node_id, b.node_id}, include_connecting_edges=True)

    assert len(subgraph.nodes) == 2
    assert a.node_id in subgraph.nodes
    assert b.node_id in subgraph.nodes
    assert c.node_id not in subgraph.nodes

    # Should have edge between A and B
    assert len(subgraph.edges) == 1


def test_graph_statistics():
    """Graph computes statistics."""
    graph = CognitiveHypergraph()

    graph.add_node(NodeType.CONCEPT, "A")
    graph.add_node(NodeType.CONCEPT, "B")
    graph.add_node(NodeType.FACT, "C")

    a = graph.nodes[list(graph.nodes.keys())[0]]
    b = graph.nodes[list(graph.nodes.keys())[1]]
    c = graph.nodes[list(graph.nodes.keys())[2]]

    graph.add_edge([a], [b], EdgeType.IMPLIES)
    graph.add_edge([a, b], [c], EdgeType.DERIVES)

    stats = graph.get_stats()

    assert stats["num_nodes"] == 3
    assert stats["num_edges"] == 2
    assert stats["node_types"]["concept"] == 2
    assert stats["node_types"]["fact"] == 1
    assert stats["edge_types"]["implies"] == 1
    assert stats["edge_types"]["derives"] == 1


def test_multi_way_relationships():
    """Hypergraph supports multi-way relationships (not just pairs)."""
    graph = CognitiveHypergraph()

    # Create reasoning: premise1 AND premise2 AND rule -> conclusion
    premise1 = graph.add_node(NodeType.FACT, "Premise 1")
    premise2 = graph.add_node(NodeType.FACT, "Premise 2")
    rule = graph.add_node(NodeType.RULE, "Inference Rule")
    conclusion = graph.add_node(NodeType.FACT, "Conclusion")

    # Multi-way hyperedge: 3 sources -> 1 target
    edge = graph.add_edge(
        source_nodes=[premise1, premise2, rule],
        target_nodes=[conclusion],
        edge_type=EdgeType.DERIVES,
        weight=0.95,
    )

    # Verify it's truly multi-way
    arity = edge.arity()
    assert arity[0] == 3  # 3 sources
    assert arity[1] == 1  # 1 target

    # Conclusion should have 3 incoming source nodes
    assert len(edge.source_nodes) == 3


def test_reasoning_chain():
    """Graph models complex reasoning chains."""
    graph = CognitiveHypergraph()

    # Build reasoning: observation -> hypothesis -> experiment -> conclusion
    observation = graph.add_node(NodeType.FACT, "Observation")
    hypothesis = graph.add_node(NodeType.CONCEPT, "Hypothesis")
    experiment = graph.add_node(NodeType.ACTION, "Experiment")
    result = graph.add_node(NodeType.STATE, "Result")
    conclusion = graph.add_node(NodeType.FACT, "Conclusion")

    graph.add_edge([observation], [hypothesis], EdgeType.SUPPORTS)
    graph.add_edge([hypothesis], [experiment], EdgeType.REQUIRES)
    graph.add_edge([experiment], [result], EdgeType.TRANSFORMS)
    graph.add_edge([result, hypothesis], [conclusion], EdgeType.DERIVES)

    # Find reasoning path
    paths = graph.find_paths(observation.node_id, conclusion.node_id, max_depth=10)

    # Should find at least one reasoning path
    assert len(paths) > 0

    # Longest path should go through all intermediate steps
    longest_path = max(paths, key=len)
    assert len(longest_path) >= 4  # At least 4 nodes in chain


def test_graph_clear():
    """Graph can be cleared."""
    graph = CognitiveHypergraph()

    graph.add_node(NodeType.CONCEPT, "A")
    graph.add_node(NodeType.CONCEPT, "B")
    a = list(graph.nodes.values())[0]
    b = list(graph.nodes.values())[1]
    graph.add_edge([a], [b], EdgeType.IMPLIES)

    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    graph.clear()

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_global_singleton():
    """get_cognitive_graph returns singleton."""
    graph1 = get_cognitive_graph()
    graph2 = get_cognitive_graph()

    assert graph1 is graph2
    assert isinstance(graph1, CognitiveHypergraph)


def test_contextual_dependencies():
    """Graph models contextual dependencies."""
    graph = CognitiveHypergraph()

    # fact + context -> interpretation
    fact = graph.add_node(NodeType.FACT, "Raw Fact")
    context1 = graph.add_node(NodeType.STATE, "Context 1")
    context2 = graph.add_node(NodeType.STATE, "Context 2")
    interp1 = graph.add_node(NodeType.CONCEPT, "Interpretation 1")
    interp2 = graph.add_node(NodeType.CONCEPT, "Interpretation 2")

    # Same fact, different contexts -> different interpretations
    graph.add_edge([fact, context1], [interp1], EdgeType.DERIVES)
    graph.add_edge([fact, context2], [interp2], EdgeType.DERIVES)

    # Both edges involve the fact
    edges_with_fact = [e for e in graph.edges.values() if e.involves_node(fact.node_id)]
    assert len(edges_with_fact) == 2


def test_causal_relationships():
    """Graph models causal relationships."""
    graph = CognitiveHypergraph()

    cause1 = graph.add_node(NodeType.STATE, "Cause 1")
    cause2 = graph.add_node(NodeType.STATE, "Cause 2")
    effect = graph.add_node(NodeType.STATE, "Effect")

    # Multiple causes -> effect
    graph.add_edge(
        [cause1, cause2],
        [effect],
        EdgeType.CAUSES,
        weight=0.8,
    )

    # Effect has incoming edge from both causes
    incoming_edges = graph._incoming[effect.node_id]
    assert len(incoming_edges) == 1

    edge = graph.edges[list(incoming_edges)[0]]
    assert edge.edge_type == EdgeType.CAUSES
    assert len(edge.source_nodes) == 2


def test_node_types_enum():
    """NodeType enum has all expected types."""
    expected_types = [
        "CONCEPT",
        "STATE",
        "FACT",
        "RULE",
        "GOAL",
        "ACTION",
        "MEMORY",
        "EMOTION",
        "UNKNOWN",
    ]

    for type_name in expected_types:
        assert hasattr(NodeType, type_name)


def test_edge_types_enum():
    """EdgeType enum has all expected types."""
    expected_types = [
        "IMPLIES",
        "CAUSES",
        "REQUIRES",
        "CONFLICTS",
        "SUPPORTS",
        "TRANSFORMS",
        "ASSOCIATES",
        "DERIVES",
    ]

    for type_name in expected_types:
        assert hasattr(EdgeType, type_name)


# Phase 6 Complete: 20 tests validating hypergraph cognitive topology
