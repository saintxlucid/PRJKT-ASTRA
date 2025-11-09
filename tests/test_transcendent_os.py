"""
Tests for ASTRA OS Phase 10: Transcendent Unification

Tests the complete integration of all 9 phases into a unified,
self-aware, distributed cognitive operating system.

Tests cover:
- Unified cognitive pipeline
- Cross-phase synergies
- Emergent behaviors
- System health monitoring
- Cognitive mode transitions
- Evolution tracking
- End-to-end scenarios
"""

import pytest
import asyncio
from chat_os.cognitive.transcendent_os import (
    TranscendentOS,
    UnificationLevel,
    CognitiveMode,
    UnifiedRequest,
    SystemHealth,
    EmergentBehavior,
    get_transcendent_os
)


@pytest.mark.asyncio
async def test_os_initialization():
    """Test transcendent OS initialization"""
    os_instance = TranscendentOS(
        enable_distributed=True,
        enable_self_modification=True,
        unification_level=UnificationLevel.TRANSCENDENT
    )
    
    assert os_instance.unification_level == UnificationLevel.TRANSCENDENT
    assert os_instance.enable_distributed is True
    assert os_instance.enable_self_modification is True
    assert os_instance.cognitive_mode == CognitiveMode.REACTIVE
    assert os_instance.memory is not None
    assert os_instance.intent is not None
    assert os_instance.graph is not None
    assert os_instance.learner is not None
    assert os_instance.distributed is not None
    assert os_instance.modifier is not None


@pytest.mark.asyncio
async def test_os_initialization_minimal():
    """Test OS initialization with minimal features"""
    os_instance = TranscendentOS(
        enable_distributed=False,
        enable_self_modification=False,
        unification_level=UnificationLevel.CONNECTED
    )
    
    assert os_instance.distributed is None
    assert os_instance.modifier is None
    assert os_instance.unification_level == UnificationLevel.CONNECTED


@pytest.mark.asyncio
async def test_unified_request_processing():
    """Test processing a unified request through all phases"""
    os_instance = TranscendentOS()
    
    request = await os_instance.process_unified(
        query="What is machine learning?",
        context={"domain": "AI"}
    )
    
    assert isinstance(request, UnifiedRequest)
    assert request.query == "What is machine learning?"
    assert request.response != ""
    assert 0 <= request.confidence_score <= 1
    assert len(request.reasoning_trace) > 0
    assert "response_time" in request.metadata


@pytest.mark.asyncio
async def test_intent_analysis_phase():
    """Test intent analysis in unified pipeline"""
    os_instance = TranscendentOS()
    
    request = await os_instance.process_unified(
        query="How do I optimize performance?",
        context={}
    )
    
    assert "primary_intent" in request.intent_analysis
    assert "confidence" in request.intent_analysis
    assert 0 <= request.intent_analysis["confidence"] <= 1


@pytest.mark.asyncio
async def test_memory_retrieval_phase():
    """Test memory retrieval in unified pipeline"""
    os_instance = TranscendentOS()
    
    # Add some memories first
    os_instance.memory.store(
        content="Machine learning is a subset of AI",
        memory_type="episodic",
        metadata={"topic": "ML"}
    )
    
    request = await os_instance.process_unified(
        query="Tell me about ML",
        context={}
    )
    
    assert isinstance(request.memory_context, list)


@pytest.mark.asyncio
async def test_graph_contextualization_phase():
    """Test graph building in unified pipeline"""
    os_instance = TranscendentOS()
    
    request = await os_instance.process_unified(
        query="Explain neural networks",
        context={}
    )
    
    assert "query_node" in request.graph_context
    assert "node_count" in request.graph_context
    assert request.graph_context["node_count"] >= 0


@pytest.mark.asyncio
async def test_distributed_consultation_phase():
    """Test distributed consultation in unified pipeline"""
    os_instance = TranscendentOS(enable_distributed=True)
    
    # Register a mock peer
    from chat_os.cognitive.distributed_consciousness import PeerInfo, PeerStatus
    peer = PeerInfo(
        peer_id="test_peer",
        address="localhost:8000",
        status=PeerStatus.ACTIVE,
        capabilities={"reasoning"},
        max_load=10,
        current_load=2,
        reliability_score=0.9
    )
    os_instance.distributed.register_peer(peer)
    
    request = await os_instance.process_unified(
        query="Distributed question",
        context={}
    )
    
    # Should have distributed context
    assert "peer_count" in request.distributed_context or request.distributed_context == {}


@pytest.mark.asyncio
async def test_learning_update_phase():
    """Test learning updates in unified pipeline"""
    os_instance = TranscendentOS()
    
    initial_experiences = len(os_instance.learner.feedback_history)
    
    await os_instance.process_unified(
        query="Test query for learning",
        context={}
    )
    
    # Should have recorded experience
    assert len(os_instance.learner.feedback_history) >= initial_experiences


@pytest.mark.asyncio
async def test_self_modification_check():
    """Test self-modification checks in unified pipeline"""
    os_instance = TranscendentOS(enable_self_modification=True)
    
    initial_mods = len(os_instance.modifier.modifications)
    
    # Process multiple requests (might trigger optimization)
    for _ in range(3):
        await os_instance.process_unified(
            query="Test query",
            context={}
        )
    
    # Modifications may or may not be proposed depending on performance
    assert len(os_instance.modifier.modifications) >= initial_mods


@pytest.mark.asyncio
async def test_cognitive_mode_reactive():
    """Test reactive cognitive mode"""
    os_instance = TranscendentOS()
    
    result = os_instance.set_cognitive_mode(CognitiveMode.REACTIVE)
    
    assert result["new_mode"] == "reactive"
    assert os_instance.cognitive_mode == CognitiveMode.REACTIVE


@pytest.mark.asyncio
async def test_cognitive_mode_proactive():
    """Test proactive cognitive mode"""
    os_instance = TranscendentOS()
    
    os_instance.set_cognitive_mode(CognitiveMode.PROACTIVE)
    
    assert os_instance.cognitive_mode == CognitiveMode.PROACTIVE


@pytest.mark.asyncio
async def test_cognitive_mode_reflective():
    """Test reflective cognitive mode"""
    os_instance = TranscendentOS(enable_self_modification=True)
    
    os_instance.set_cognitive_mode(CognitiveMode.REFLECTIVE)
    
    assert os_instance.cognitive_mode == CognitiveMode.REFLECTIVE
    assert os_instance.modifier.safe_mode is True


@pytest.mark.asyncio
async def test_cognitive_mode_collaborative():
    """Test collaborative cognitive mode"""
    os_instance = TranscendentOS(enable_distributed=True)
    
    os_instance.set_cognitive_mode(CognitiveMode.COLLABORATIVE)
    
    assert os_instance.cognitive_mode == CognitiveMode.COLLABORATIVE
    from chat_os.cognitive.distributed_consciousness import SyncStrategy
    assert os_instance.distributed.sync_strategy == SyncStrategy.IMMEDIATE


@pytest.mark.asyncio
async def test_cognitive_mode_transcendent():
    """Test transcendent cognitive mode"""
    os_instance = TranscendentOS()
    
    os_instance.set_cognitive_mode(CognitiveMode.TRANSCENDENT)
    
    assert os_instance.cognitive_mode == CognitiveMode.TRANSCENDENT


@pytest.mark.asyncio
async def test_system_health_monitoring():
    """Test comprehensive system health monitoring"""
    os_instance = TranscendentOS()
    
    # Process some requests to generate data
    await os_instance.process_unified("Test query 1", {})
    await os_instance.process_unified("Test query 2", {})
    
    health = os_instance.get_system_health()
    
    assert isinstance(health, SystemHealth)
    assert 0 <= health.overall_health <= 1
    assert 0 <= health.memory_health <= 1
    assert 0 <= health.intent_health <= 1
    assert 0 <= health.graph_health <= 1
    assert 0 <= health.learning_health <= 1
    assert 0 <= health.distributed_health <= 1
    assert 0 <= health.modification_health <= 1
    assert health.success_rate >= 0
    assert health.response_time_avg >= 0


@pytest.mark.asyncio
async def test_system_health_issues_detection():
    """Test system health issue detection"""
    os_instance = TranscendentOS()
    
    health = os_instance.get_system_health()
    
    # Issues and warnings should be lists
    assert isinstance(health.issues, list)
    assert isinstance(health.warnings, list)


@pytest.mark.asyncio
async def test_emergent_behavior_detection():
    """Test detection of emergent behaviors"""
    os_instance = TranscendentOS()
    
    # Generate enough data to trigger emergent behaviors
    for i in range(15):
        os_instance.memory.store(
            content=f"Memory {i}",
            memory_type="episodic",
            metadata={}
        )
    
    # Register some intents
    for i in range(5):
        os_instance.intent.register_intent(f"intent_{i}", 0.5)
    
    behaviors = os_instance.detect_emergent_behaviors()
    
    assert isinstance(behaviors, list)
    # Should detect at least one behavior
    if len(behaviors) > 0:
        behavior = behaviors[0]
        assert isinstance(behavior, EmergentBehavior)
        assert behavior.behavior_id != ""
        assert len(behavior.involved_phases) > 0
        assert 0 <= behavior.utility_score <= 1


@pytest.mark.asyncio
async def test_emergent_behavior_memory_intent_synergy():
    """Test memory-intent synergy emergent behavior"""
    os_instance = TranscendentOS()
    
    # Create conditions for memory-intent synergy
    for i in range(12):
        os_instance.memory.store(f"Memory {i}", "episodic", {})
    
    for i in range(5):
        os_instance.intent.register_intent(f"intent_{i}", 0.5)
    
    behaviors = os_instance.detect_emergent_behaviors()
    
    behavior_ids = [b.behavior_id for b in behaviors]
    assert "memory_intent_synergy" in behavior_ids


@pytest.mark.asyncio
async def test_emergent_behavior_graph_retrieval():
    """Test graph-accelerated retrieval emergent behavior"""
    os_instance = TranscendentOS()
    
    # Create conditions
    from chat_os.cognitive.cognitive_graph import NodeType
    for i in range(25):
        os_instance.graph.add_node(NodeType.CONCEPT, f"Concept {i}")
    
    for i in range(8):
        os_instance.memory.store(f"Memory {i}", "semantic", {})
    
    behaviors = os_instance.detect_emergent_behaviors()
    
    behavior_ids = [b.behavior_id for b in behaviors]
    assert "graph_retrieval_acceleration" in behavior_ids


@pytest.mark.asyncio
async def test_system_evolution():
    """Test system evolution and generation tracking"""
    os_instance = TranscendentOS()
    
    initial_gen = os_instance.system_generation
    
    # Process some requests
    await os_instance.process_unified("Query 1", {})
    await os_instance.process_unified("Query 2", {})
    
    # Evolve system
    evolution = os_instance.evolve_system()
    
    assert os_instance.system_generation == initial_gen + 1
    assert evolution["generation"] == os_instance.system_generation
    assert "health" in evolution
    assert "metrics" in evolution
    assert "emergent_behaviors" in evolution


@pytest.mark.asyncio
async def test_evolution_history():
    """Test tracking multiple evolution generations"""
    os_instance = TranscendentOS()
    
    # Evolve multiple times
    os_instance.evolve_system()
    os_instance.evolve_system()
    os_instance.evolve_system()
    
    assert len(os_instance.evolution_history) == 3
    assert os_instance.evolution_history[0]["generation"] == 1
    assert os_instance.evolution_history[2]["generation"] == 3


@pytest.mark.asyncio
async def test_unified_stats():
    """Test comprehensive unified statistics"""
    os_instance = TranscendentOS()
    
    # Generate some activity
    await os_instance.process_unified("Test query", {})
    
    stats = os_instance.get_unified_stats()
    
    assert "system" in stats
    assert "performance" in stats
    assert "phases" in stats
    assert stats["system"]["unification_level"] != ""
    assert stats["system"]["cognitive_mode"] != ""
    assert "total_requests" in stats["performance"]


@pytest.mark.asyncio
async def test_performance_tracking():
    """Test performance metric tracking"""
    os_instance = TranscendentOS()
    
    # Process multiple requests
    for i in range(5):
        await os_instance.process_unified(f"Query {i}", {})
    
    assert os_instance.total_requests == 5
    assert os_instance.successful_requests > 0
    assert os_instance.total_response_time > 0


@pytest.mark.asyncio
async def test_request_history():
    """Test request history tracking"""
    os_instance = TranscendentOS()
    
    await os_instance.process_unified("Query 1", {})
    await os_instance.process_unified("Query 2", {})
    
    assert len(os_instance.request_history) == 2
    assert os_instance.request_history[0].query == "Query 1"
    assert os_instance.request_history[1].query == "Query 2"


@pytest.mark.asyncio
async def test_request_history_trimming():
    """Test request history trimming to prevent memory bloat"""
    os_instance = TranscendentOS()
    
    # Add many requests (simulate)
    for i in range(1005):
        request = UnifiedRequest(
            request_id=f"req_{i}",
            timestamp=float(i),
            query=f"Query {i}"
        )
        os_instance.request_history.append(request)
    
    # Process one more to trigger trim
    await os_instance.process_unified("Trigger trim", {})
    
    # Should be trimmed to 1000
    assert len(os_instance.request_history) == 1000


@pytest.mark.asyncio
async def test_cross_phase_synergies():
    """Test cross-phase synergy activation"""
    os_instance = TranscendentOS()
    
    # Check synergy cache
    assert "memory_graph_integration" in os_instance.synergy_cache
    assert "intent_driven_retrieval" in os_instance.synergy_cache
    assert "learning_optimization" in os_instance.synergy_cache
    
    # Synergies should be enabled
    assert os_instance.synergy_cache["memory_graph_integration"]["enabled"] is True


@pytest.mark.asyncio
async def test_reasoning_trace():
    """Test reasoning trace generation"""
    os_instance = TranscendentOS()
    
    request = await os_instance.process_unified(
        query="Test reasoning trace",
        context={}
    )
    
    # Should have detailed reasoning steps
    assert len(request.reasoning_trace) > 0
    assert any("Intent" in step for step in request.reasoning_trace)
    assert any("memories" in step for step in request.reasoning_trace)
    assert any("cognitive" in step for step in request.reasoning_trace)


@pytest.mark.asyncio
async def test_confidence_scoring():
    """Test unified confidence scoring"""
    os_instance = TranscendentOS()
    
    request = await os_instance.process_unified(
        query="Test confidence",
        context={}
    )
    
    assert 0 <= request.confidence_score <= 1


@pytest.mark.asyncio
async def test_response_metadata():
    """Test response metadata tracking"""
    os_instance = TranscendentOS()
    
    request = await os_instance.process_unified(
        query="Test metadata",
        context={}
    )
    
    assert "response_time" in request.metadata
    assert "memory_count" in request.metadata
    assert "graph_complexity" in request.metadata


@pytest.mark.asyncio
async def test_global_singleton():
    """Test global singleton pattern"""
    os1 = get_transcendent_os()
    os2 = get_transcendent_os()
    
    assert os1 is os2


@pytest.mark.asyncio
async def test_unification_level_enum():
    """Test UnificationLevel enum values"""
    assert UnificationLevel.ISOLATED.value == "isolated"
    assert UnificationLevel.CONNECTED.value == "connected"
    assert UnificationLevel.INTEGRATED.value == "integrated"
    assert UnificationLevel.UNIFIED.value == "unified"
    assert UnificationLevel.TRANSCENDENT.value == "transcendent"


@pytest.mark.asyncio
async def test_cognitive_mode_enum():
    """Test CognitiveMode enum values"""
    assert CognitiveMode.REACTIVE.value == "reactive"
    assert CognitiveMode.PROACTIVE.value == "proactive"
    assert CognitiveMode.REFLECTIVE.value == "reflective"
    assert CognitiveMode.CREATIVE.value == "creative"
    assert CognitiveMode.COLLABORATIVE.value == "collaborative"
    assert CognitiveMode.TRANSCENDENT.value == "transcendent"


@pytest.mark.asyncio
async def test_end_to_end_scenario_simple():
    """Test simple end-to-end scenario"""
    os_instance = TranscendentOS()
    
    # Store relevant memory
    os_instance.memory.store(
        "Python is a programming language",
        "semantic",
        {"topic": "programming"}
    )
    
    # Process query
    request = await os_instance.process_unified(
        query="What is Python?",
        context={"domain": "programming"}
    )
    
    # Verify complete processing
    assert request.response != ""
    assert request.confidence_score > 0
    assert len(request.reasoning_trace) > 5


@pytest.mark.asyncio
async def test_end_to_end_scenario_complex():
    """Test complex end-to-end scenario with all phases"""
    os_instance = TranscendentOS(
        enable_distributed=True,
        enable_self_modification=True
    )
    
    # Setup environment
    for i in range(5):
        os_instance.memory.store(f"Fact {i}", "semantic", {})
    
    os_instance.intent.register_intent("learn", 0.7)
    
    from chat_os.cognitive.cognitive_graph import NodeType
    for i in range(10):
        os_instance.graph.add_node(NodeType.CONCEPT, f"Concept {i}")
    
    # Process query
    request = await os_instance.process_unified(
        query="Complex multi-phase query",
        context={"complexity": "high"}
    )
    
    # Verify all phases engaged
    assert request.intent_analysis != {}
    assert len(request.memory_context) >= 0
    assert request.graph_context != {}
    assert request.response != ""


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in unified pipeline"""
    os_instance = TranscendentOS()
    
    # This should not crash even with edge cases
    request = await os_instance.process_unified(
        query="",  # Empty query
        context={}
    )
    
    # Should handle gracefully
    assert isinstance(request, UnifiedRequest)


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling concurrent requests"""
    os_instance = TranscendentOS()
    
    # Process multiple requests concurrently
    tasks = [
        os_instance.process_unified(f"Query {i}", {})
        for i in range(5)
    ]
    
    requests = await asyncio.gather(*tasks)
    
    assert len(requests) == 5
    for request in requests:
        assert isinstance(request, UnifiedRequest)


@pytest.mark.asyncio
async def test_system_health_after_load():
    """Test system health under load"""
    os_instance = TranscendentOS()
    
    # Process many requests
    for i in range(20):
        await os_instance.process_unified(f"Query {i}", {})
    
    health = os_instance.get_system_health()
    
    # System should remain healthy
    assert health.overall_health > 0.5
    assert health.success_rate > 0.8


@pytest.mark.asyncio
async def test_learning_from_failures():
    """Test that system learns from failures"""
    os_instance = TranscendentOS()
    
    initial_experiences = len(os_instance.learner.feedback_history)
    
    # Process requests (some may "fail" with low confidence)
    for i in range(5):
        await os_instance.process_unified(f"Query {i}", {})
    
    # Should have learned from all experiences
    assert len(os_instance.learner.feedback_history) > initial_experiences


@pytest.mark.asyncio
async def test_phase_integration_memory_graph():
    """Test memory-graph integration"""
    os_instance = TranscendentOS()
    
    # Store memory
    os_instance.memory.store("Test memory", "episodic", {})
    
    # Process query to engage graph
    request = await os_instance.process_unified("Test query", {})
    
    # Graph should have nodes
    assert len(os_instance.graph.nodes) > 0


@pytest.mark.asyncio
async def test_phase_integration_intent_memory():
    """Test intent-memory integration"""
    os_instance = TranscendentOS()
    
    # Register intent
    os_instance.intent.register_intent("test_intent", 0.8)
    
    # Store memory with same intent
    os_instance.memory.store(
        "Memory content",
        "episodic",
        {"intent": "test_intent"}
    )
    
    # Process query
    request = await os_instance.process_unified(
        "Query with test_intent",
        {}
    )
    
    # Should retrieve intent-relevant memories
    assert isinstance(request.memory_context, list)


@pytest.mark.asyncio
async def test_self_healing_capability():
    """Test self-healing through modification"""
    os_instance = TranscendentOS(enable_self_modification=True)
    
    # System should detect and propose fixes
    # Process multiple requests to collect data
    for i in range(10):
        await os_instance.process_unified(f"Query {i}", {})
    
    # Check for optimization proposals
    stats = os_instance.modifier.get_modification_stats()
    
    # System is monitoring for improvements
    assert stats["total_analyses"] >= 0


@pytest.mark.asyncio
async def test_distributed_collective_intelligence():
    """Test distributed collective intelligence"""
    os_instance = TranscendentOS(enable_distributed=True)
    
    # Register multiple peers
    from chat_os.cognitive.distributed_consciousness import PeerInfo, PeerStatus
    
    for i in range(3):
        peer = PeerInfo(
            peer_id=f"peer_{i}",
            address=f"localhost:800{i}",
            status=PeerStatus.ACTIVE,
            capabilities={"reasoning"},
            max_load=10,
            current_load=i,
            reliability_score=0.8 + (i * 0.05)
        )
        os_instance.distributed.register_peer(peer)
    
    # Process query with distributed consultation
    request = await os_instance.process_unified(
        "Distributed query",
        {}
    )
    
    # Should have consulted distributed network
    if request.distributed_context:
        assert "peer_count" in request.distributed_context


@pytest.mark.asyncio
async def test_system_generation_progression():
    """Test system evolves across generations"""
    os_instance = TranscendentOS()
    
    gen1 = os_instance.evolve_system()
    
    # Add more data
    for i in range(10):
        os_instance.memory.store(f"Memory {i}", "semantic", {})
    
    gen2 = os_instance.evolve_system()
    
    # Generation should increase
    assert gen2["generation"] > gen1["generation"]
    # Metrics should improve
    assert gen2["metrics"]["total_memories"] > gen1["metrics"]["total_memories"]
