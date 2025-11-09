"""
Test Memory Integration (Week-2 Days 9-10)
===========================================

End-to-end test for ChromaMemoryGateway integration with server.

Tests:
1. Add memories via gateway
2. Search memories via API endpoint
3. Verify signature validation
4. Check event logging

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Days 9-10)
"""

import requests
import json
from uuid import uuid4

# Server endpoint
BASE_URL = "http://localhost:8000"

def test_memory_add():
    """Test adding memories directly via gateway."""
    print("\n" + "="*80)
    print("TEST 1: Add Memories")
    print("="*80)
    
    # Initialize gateway
    from src.gateways.chroma_memory_gateway import ChromaMemoryGateway
    
    gateway = ChromaMemoryGateway(
        persist_directory="data/chroma",
        collection_name="astra_memory",
        embedding_model="all-MiniLM-L6-v2",
        signing_key="test_key_123"
    )
    
    # Add test memories
    memories = [
        {
            "id": str(uuid4()),
            "text": "ASTRA is an AI assistant focused on thoughtful, safe interaction.",
            "metadata": {"category": "identity", "timestamp": "2025-11-02"}
        },
        {
            "id": str(uuid4()),
            "text": "Week-2 architecture refactor transforms ASTRA into an auditable synthetic being.",
            "metadata": {"category": "architecture", "timestamp": "2025-11-02"}
        },
        {
            "id": str(uuid4()),
            "text": "The memory gateway uses ChromaDB with HMAC-SHA256 signing for tamper detection.",
            "metadata": {"category": "technical", "timestamp": "2025-11-02"}
        }
    ]
    
    for mem in memories:
        mem_id = gateway.add(mem)
        print(f"✅ Added memory: {mem_id[:8]}... | {mem['text'][:60]}...")
    
    # Verify count
    count = gateway.count()
    print(f"\n📊 Total memories in store: {count}")
    
    return gateway


def test_memory_search_api(gateway):
    """Test searching memories via API endpoint."""
    print("\n" + "="*80)
    print("TEST 2: Search Memories (API)")
    print("="*80)
    
    # Test queries
    queries = [
        "What is ASTRA?",
        "How does memory work?",
        "Tell me about architecture"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: {query}")
        
        response = requests.post(
            f"{BASE_URL}/memory/search",
            json={"query": query, "limit": 3},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            event_id = data.get("event_id", "unknown")
            
            print(f"✅ Found {len(results)} results (event_id: {event_id[:8]}...)")
            
            for i, result in enumerate(results, 1):
                text = result.get("text", "")
                distance = result.get("distance", 0)
                signed = result.get("metadata", {}).get("signed", False)
                valid = result.get("metadata", {}).get("signature_valid", True)
                
                status = "🔐 SIGNED" if signed else "🔓 UNSIGNED"
                if signed:
                    status += " ✅" if valid else " ❌ TAMPERED"
                
                print(f"  {i}. {status} (distance: {distance:.3f})")
                print(f"     {text[:80]}...")
        else:
            print(f"❌ API error: {response.status_code} - {response.text}")


def test_tampering_detection(gateway):
    """Test tamper detection."""
    print("\n" + "="*80)
    print("TEST 3: Tamper Detection")
    print("="*80)
    
    # Scan for tampering
    tampered_ids = list(gateway.scan_for_tampering())
    
    if tampered_ids:
        print(f"⚠️  Found {len(tampered_ids)} tampered memories:")
        for mem_id in tampered_ids:
            print(f"   - {mem_id}")
    else:
        print("✅ No tampering detected - all signatures valid")


def test_event_log():
    """Test event log entries."""
    print("\n" + "="*80)
    print("TEST 4: Event Log Verification")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/events?limit=10", timeout=10)
    
    if response.status_code == 200:
        events = response.json()
        
        # Find memory-related events
        memory_events = [
            e for e in events
            if e["event_type"] in ["memory_searched", "memory_search_failed", "memory_search_error"]
        ]
        
        print(f"✅ Found {len(memory_events)} memory-related events:")
        for event in memory_events[:5]:
            event_type = event["event_type"]
            event_id = event["event_id"]
            payload = event.get("payload", {})
            query = payload.get("query", "N/A")
            results_count = payload.get("results_count", 0)
            
            print(f"   - {event_type} | query: {query} | results: {results_count} | id: {event_id[:8]}...")
    else:
        print(f"❌ Failed to fetch events: {response.status_code}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 MEMORY INTEGRATION TEST SUITE (Week-2 Days 9-10)")
    print("="*80)
    
    try:
        # Test 1: Add memories
        gateway = test_memory_add()
        
        # Test 2: Search via API
        test_memory_search_api(gateway)
        
        # Test 3: Tamper detection
        test_tampering_detection(gateway)
        
        # Test 4: Event log
        test_event_log()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
