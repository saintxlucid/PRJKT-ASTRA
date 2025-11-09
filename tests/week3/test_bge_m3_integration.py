#!/usr/bin/env python3
"""
Test suite for BGE-M3 embeddings integration.

Tests:
1. BGE_M3_Embedder initialization and embedding
2. ChromaMemoryGatewayBGE storage and retrieval
3. Provenance tracking (source citations)
4. Retrieval quality comparison (old vs BGE-M3)
5. Tamper detection with signatures
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.embeddings_bge_m3 import BGE_M3_Embedder, EmbeddingConfig
from gateways.chroma_memory_gateway_bge import ChromaMemoryGatewayBGE, MemoryRecord


def test_bge_m3_embedder():
    """Test BGE-M3 embedder initialization and embedding."""
    print("\n=== Test 1: BGE-M3 Embedder ===")
    
    # Initialize
    cfg = EmbeddingConfig(device="cpu", batch_size=4)
    embedder = BGE_M3_Embedder(cfg)
    print(f"✅ Model loaded: {embedder.model.get_sentence_embedding_dimension()}D vectors")
    
    # Single embedding
    text = "ASTRA is a local, offline sovereign intelligence"
    vec = embedder.embed_single(text)
    assert vec.shape == (1024,), f"Expected 1024D, got {vec.shape}"
    print(f"✅ Single embedding: {vec.shape}")
    
    # Batch embedding
    texts = [
        "Hexagonal architecture",
        "Event sourcing",
        "Memory signing",
        "BGE-M3 embeddings"
    ]
    vecs = embedder.embed_batch(texts)
    assert vecs.shape == (4, 1024), f"Expected (4, 1024), got {vecs.shape}"
    print(f"✅ Batch embedding: {vecs.shape}")
    
    # Similarity
    sim_related = embedder.similarity("ASTRA Core", "ASTRA System")
    sim_unrelated = embedder.similarity("ASTRA Core", "Weather forecast")
    assert sim_related > sim_unrelated, "Related texts should have higher similarity"
    print(f"✅ Similarity: related={sim_related:.3f} > unrelated={sim_unrelated:.3f}")
    
    print("✅ Test 1 PASSED\n")
    return True


def test_chroma_gateway_storage():
    """Test ChromaMemoryGatewayBGE storage and retrieval."""
    print("=== Test 2: ChromaDB Storage ===")
    
    # Initialize
    gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/test_memory_bge_m3",
        hmac_key="test-key-123"
    )
    
    # Clear for clean test
    gateway.clear()
    assert gateway.count() == 0, "Collection should be empty after clear"
    print("✅ Collection cleared")
    
    # Store memories
    memories = [
        ("ASTRA uses hexagonal architecture", {"source_file": "ARCHITECTURE.md"}),
        ("Memory signing uses HMAC-SHA256", {"source_file": "security/memory_signing.md"}),
        ("BGE-M3 provides better retrieval", {"source_file": "embeddings_bge_m3.py"})
    ]
    
    stored_ids = []
    for text, metadata in memories:
        mem_id = gateway.store(text, metadata)
        stored_ids.append(mem_id)
        print(f"✅ Stored: {text[:40]}... (ID: {mem_id[:8]})")
    
    assert gateway.count() == 3, f"Expected 3 memories, got {gateway.count()}"
    print(f"✅ Total memories: {gateway.count()}")
    
    # Retrieve by ID
    mem = gateway.get(stored_ids[0])
    assert mem is not None, "Memory should exist"
    assert mem.text == memories[0][0], "Text should match"
    print(f"✅ Retrieved by ID: {mem.text[:40]}...")
    
    print("✅ Test 2 PASSED\n")
    return True


def test_semantic_search_with_provenance():
    """Test semantic search with provenance tracking."""
    print("=== Test 3: Semantic Search + Provenance ===")
    
    gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/test_memory_bge_m3",
        hmac_key="test-key-123"
    )
    
    # Search: architecture query
    query = "What design patterns does ASTRA use?"
    results = gateway.search(query, top_k=2)
    
    assert len(results) > 0, "Should return results"
    print(f"✅ Query: '{query}'")
    print(f"✅ Results: {len(results)}")
    
    for i, r in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Text: {r.text[:60]}...")
        print(f"    Source: {r.source_file}")
        print(f"    Timestamp: {r.timestamp}")
        
        # Verify signature
        is_valid = gateway._verify_signature(r.text, r.signature)
        assert is_valid, f"Signature invalid for {r.id}"
        print(f"    Signature: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    # Most relevant result should mention architecture
    assert "architecture" in results[0].text.lower(), "Top result should mention architecture"
    print("\n✅ Top result is relevant (mentions 'architecture')")
    
    print("✅ Test 3 PASSED\n")
    return True


def test_tamper_detection():
    """Test tamper detection with memory signing."""
    print("=== Test 4: Tamper Detection ===")
    
    gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/test_memory_bge_m3",
        hmac_key="test-key-123"
    )
    
    # Store memory
    original_text = "This memory should be tamper-proof"
    mem_id = gateway.store(original_text, {"type": "test"})
    print(f"✅ Stored: {original_text}")
    
    # Retrieve and verify
    mem = gateway.get(mem_id)
    assert mem is not None, "Memory should exist"
    
    is_valid = gateway._verify_signature(mem.text, mem.signature)
    assert is_valid, "Original signature should be valid"
    print(f"✅ Original signature: VALID")
    
    # Simulate tampering (wrong signature for different text)
    tampered_text = "This memory has been tampered with"
    is_valid_tampered = gateway._verify_signature(tampered_text, mem.signature)
    assert not is_valid_tampered, "Tampered text should fail verification"
    print(f"✅ Tampered text detected: signature INVALID")
    
    print("✅ Test 4 PASSED\n")
    return True


def test_metadata_filtering():
    """Test metadata filtering in search."""
    print("=== Test 5: Metadata Filtering ===")
    
    gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/test_memory_bge_m3",
        hmac_key="test-key-123"
    )
    
    # Clear and add diverse memories
    gateway.clear()
    
    gateway.store("Security feature 1", {"type": "security", "source_file": "sec1.md"})
    gateway.store("Security feature 2", {"type": "security", "source_file": "sec2.md"})
    gateway.store("Architecture pattern", {"type": "architecture", "source_file": "arch.md"})
    
    # Search with filter: only security
    results = gateway.search(
        "features",
        top_k=5,
        filter_metadata={"type": "security"}
    )
    
    print(f"✅ Query with filter type='security': {len(results)} results")
    
    for r in results:
        assert r.metadata["type"] == "security", "Should only return security memories"
        print(f"  - {r.text} (type: {r.metadata['type']})")
    
    print("✅ All results match filter")
    print("✅ Test 5 PASSED\n")
    return True


def run_all_tests():
    """Run all BGE-M3 integration tests."""
    print("=" * 80)
    print("  BGE-M3 Integration Test Suite")
    print("=" * 80)
    
    tests = [
        ("BGE-M3 Embedder", test_bge_m3_embedder),
        ("ChromaDB Storage", test_chroma_gateway_storage),
        ("Semantic Search + Provenance", test_semantic_search_with_provenance),
        ("Tamper Detection", test_tamper_detection),
        ("Metadata Filtering", test_metadata_filtering)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            start = time.time()
            result = test_func()
            elapsed = time.time() - start
            
            if result:
                passed += 1
                print(f"✅ {name}: PASSED ({elapsed:.2f}s)\n")
            else:
                failed += 1
                print(f"❌ {name}: FAILED\n")
        
        except Exception as e:
            failed += 1
            print(f"❌ {name}: ERROR - {e}\n")
    
    # Summary
    print("=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"Total: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed / (passed + failed) * 100:.0f}%")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED")
    else:
        print(f"\n❌ {failed} TESTS FAILED")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
