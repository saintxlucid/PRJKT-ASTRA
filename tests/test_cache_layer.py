import time
import pytest
from src.astra.core.cache import LRUCache

def test_ttl_and_eviction():
    """Test TTL expiration and size-based eviction"""
    cache = LRUCache(max_items=2, ttl_s=0.05)
    
    # Test basic set/get
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    
    # Test TTL expiration
    time.sleep(0.06)
    assert cache.get("a") is None
    assert cache.get("b") is None
    
    # Test size-based eviction
    cache.set("c", 3)
    cache.set("d", 4)
    assert len(cache) == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("a") is None
    assert cache.get("b") is None

def test_cache_metrics():
    """Test cache metric counters"""
    cache = LRUCache(max_items=2, ttl_s=0.1)
    
    # Test hits counter
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"  # Hit
    assert cache.get("nonexistent") is None  # Miss
    assert cache.metrics["hits_total"] == 1
    assert cache.metrics["requests_total"] == 2
    
    # Test eviction counter
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # Should evict key1
    assert cache.metrics["evictions_total"] == 1
    
    # Test TTL expiration counter
    time.sleep(0.11)  # Wait for TTL
    assert cache.get("key2") is None
    assert cache.metrics["ttl_expirations_total"] == 1