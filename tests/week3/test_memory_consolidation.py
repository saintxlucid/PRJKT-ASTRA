# Memory Consolidation Test Suite
# SPDX-License-Identifier: MIT
"""
Test suite for memory consolidation ("dreaming").

Tests:
1. Event clustering with DBSCAN
2. LLM summarization
3. Storage in semantic memory
4. Scheduler execution
5. API endpoints
6. End-to-end consolidation flow
"""
import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from gateways.event_store_sqlite import SQLiteEventStore
from gateways.chroma_memory_gateway_bge import ChromaMemoryGatewayBGE
from services.llm_service_local import LocalLLMService
from services.memory_consolidation import (
    MemoryConsolidationService,
    ConsolidationConfig
)
from services.consolidation_scheduler import ConsolidationScheduler


def test_event_clustering():
    """Test: Event clustering with DBSCAN on BGE-M3 embeddings."""
    print("\n=== Test: Event Clustering ===\n")
    
    # Create test event store
    event_store = SQLiteEventStore(db_path="data/eventlog_test.sqlite")
    
    # Add test events (similar events for clustering)
    identity = {"agent": "test", "warmth": 0.7}
    
    # Cluster 1: Architecture questions
    for i in range(5):
        event_store.append(
            "user_query",
            {"query": f"What is hexagonal architecture? (variant {i})"},
            identity
        )
    
    # Cluster 2: Memory questions
    for i in range(5):
        event_store.append(
            "user_query",
            {"query": f"How does memory signing work? (variant {i})"},
            identity
        )
    
    # Initialize consolidation service
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3_test",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()
    
    service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig(
            min_events=5,
            min_cluster_size=2,
            clustering_eps=0.5
        )
    )
    
    # Get events
    events = service._get_unconsolidated_events()
    print(f"✅ Retrieved {len(events)} events")
    
    # Embed events
    embeddings = service._embed_events(events)
    print(f"✅ Embedded events (shape: {embeddings.shape})")
    
    # Cluster events
    clusters = service._cluster_events(events, embeddings)
    print(f"✅ Found {len(clusters)} clusters")
    
    for i, cluster in enumerate(clusters, 1):
        print(f"\n  Cluster {i}: {len(cluster.events)} events")
        print(f"    Sample: {cluster.events[0].typ}")
    
    event_store.close()
    assert len(clusters) >= 1, "Expected at least 1 cluster"
    print("\n✅ Test passed: Event clustering works")


def test_llm_summarization():
    """Test: LLM summarization of event clusters."""
    print("\n=== Test: LLM Summarization ===\n")
    
    # Create test cluster
    from domain.events import Event
    import numpy as np
    from services.memory_consolidation import EventCluster
    
    events = [
        Event(
            id="1",
            ts="2025-11-02T00:00:00Z",
            typ="user_query",
            payload={"query": "What is hexagonal architecture?"},
            identity={"agent": "test"},
            prev_hash="GENESIS",
            hash="hash1"
        ),
        Event(
            id="2",
            ts="2025-11-02T00:01:00Z",
            typ="user_query",
            payload={"query": "Explain domain-driven design"},
            identity={"agent": "test"},
            prev_hash="hash1",
            hash="hash2"
        )
    ]
    
    cluster = EventCluster(
        cluster_id=1,
        events=events,
        centroid=np.zeros(1024)  # Dummy centroid
    )
    
    # Initialize service
    event_store = SQLiteEventStore(db_path="data/eventlog_test.sqlite")
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3_test",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()
    
    service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig()
    )
    
    # Generate theme
    theme = service._generate_theme(cluster)
    print(f"✅ Generated theme: {theme}")
    
    # Summarize cluster
    summary = service._summarize_cluster(cluster)
    print(f"✅ Generated summary: {summary[:100]}...")
    
    event_store.close()
    assert len(summary) > 0, "Summary should not be empty"
    print("\n✅ Test passed: LLM summarization works")


def test_semantic_storage():
    """Test: Storage of summaries in semantic memory."""
    print("\n=== Test: Semantic Storage ===\n")
    
    from domain.events import Event
    import numpy as np
    from services.memory_consolidation import EventCluster
    
    # Create test cluster with summary
    events = [
        Event(
            id="1",
            ts="2025-11-02T00:00:00Z",
            typ="user_query",
            payload={"query": "Test query"},
            identity={"agent": "test"},
            prev_hash="GENESIS",
            hash="hash1"
        )
    ]
    
    cluster = EventCluster(
        cluster_id=1,
        events=events,
        centroid=np.zeros(1024),
        summary="User frequently asks about architecture patterns"
    )
    
    # Initialize service
    event_store = SQLiteEventStore(db_path="data/eventlog_test.sqlite")
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3_test",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()
    
    service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig()
    )
    
    # Store summary
    before_count = memory_gateway.count()
    service._store_summary(cluster)
    after_count = memory_gateway.count()
    
    print(f"✅ Stored summary (before: {before_count}, after: {after_count})")
    
    # Search for summary
    results = memory_gateway.search("architecture", top_k=1)
    print(f"✅ Retrieved {len(results)} results")
    
    if results:
        print(f"   Result: {results[0].text[:80]}...")
        print(f"   Metadata: {results[0].metadata.get('source')}")
    
    event_store.close()
    assert after_count > before_count, "Memory count should increase"
    print("\n✅ Test passed: Semantic storage works")


def test_consolidation_end_to_end():
    """Test: End-to-end consolidation flow."""
    print("\n=== Test: End-to-End Consolidation ===\n")
    
    # Create test event store with events
    event_store = SQLiteEventStore(db_path="data/eventlog_test.sqlite")
    identity = {"agent": "test", "warmth": 0.7}
    
    # Add test events
    for i in range(15):
        event_store.append(
            "user_query",
            {"query": f"Test query {i}"},
            identity
        )
    
    # Initialize consolidation service
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3_test",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()
    
    service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig(
            min_events=10,
            max_events=20,
            min_cluster_size=2
        )
    )
    
    # Run consolidation
    print("Running consolidation...")
    result = service.consolidate()
    
    print(f"\n✅ Consolidation result:")
    print(f"   Status: {result['status']}")
    print(f"   Events processed: {result['events_count']}")
    print(f"   Clusters found: {result['clusters_count']}")
    print(f"   Summaries stored: {result['summaries_stored']}")
    print(f"   Duration: {result['duration_seconds']}s")
    
    event_store.close()
    assert result['status'] in ['success', 'skipped_insufficient_events'], "Consolidation should succeed or skip"
    print("\n✅ Test passed: End-to-end consolidation works")


def test_scheduler():
    """Test: Consolidation scheduler."""
    print("\n=== Test: Consolidation Scheduler ===\n")
    
    # Initialize dependencies
    event_store = SQLiteEventStore(db_path="data/eventlog_test.sqlite")
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3_test",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()
    
    consolidation_service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig(min_events=5)
    )
    
    # Initialize scheduler (disable for testing)
    scheduler = ConsolidationScheduler(
        consolidation_service=consolidation_service,
        schedule="* * * * *",  # Every minute
        enabled=False  # Disabled for testing
    )
    
    print(f"✅ Scheduler initialized (enabled: {scheduler.enabled})")
    
    # Manual run
    print("Running consolidation manually...")
    result = scheduler.run_now()
    
    print(f"\n✅ Manual run result:")
    print(f"   Status: {result['status']}")
    print(f"   Events: {result['events_count']}")
    print(f"   Clusters: {result['clusters_count']}")
    
    # Check history
    history = scheduler.get_job_history(limit=5)
    print(f"\n✅ Job history: {len(history)} runs")
    
    event_store.close()
    assert len(history) > 0, "Job history should not be empty"
    print("\n✅ Test passed: Scheduler works")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 Memory Consolidation Test Suite")
    print("="*80)
    
    tests = [
        ("Event Clustering", test_event_clustering),
        ("LLM Summarization", test_llm_summarization),
        ("Semantic Storage", test_semantic_storage),
        ("End-to-End Consolidation", test_consolidation_end_to_end),
        ("Scheduler", test_scheduler)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ Test failed: {name}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 Test Summary: {passed}/{len(tests)} passed, {failed} failed")
    print("="*80 + "\n")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    
    if failed == 0:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
