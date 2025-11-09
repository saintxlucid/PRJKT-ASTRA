"""
Memory caching implementation with LRU cache.
"""
from typing import Dict, Any, List, Optional
from collections import OrderedDict
import time
import structlog
from dataclasses import dataclass

from .metrics import MEMORY_CACHE_HITS, MEMORY_CACHE_MISSES

logger = structlog.get_logger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached memory entry."""
    data: Dict[str, Any]
    expires_at: float

class MemoryCache:
    """LRU cache for memory entries."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cached entries
        """
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        logger.info("memory_cache_initialized", max_size=max_size, ttl=ttl_seconds)
        
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            entry = self._cache.get(key)
            now = time.time()
            
            # Not found
            if entry is None:
                MEMORY_CACHE_MISSES.inc()
                return None
                
            # Expired
            if now > entry.expires_at:
                MEMORY_CACHE_MISSES.inc()
                del self._cache[key]
                return None
                
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            MEMORY_CACHE_HITS.inc()
            return entry.data
            
        except Exception as e:
            logger.error("cache_get_error", error=str(e), key=key)
            return None
            
    def set(self, key: str, data: Dict[str, Any]) -> None:
        """
        Add entry to cache.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        try:
            # Enforce max size
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # Remove oldest
                
            # Add new entry
            self._cache[key] = CacheEntry(
                data=data,
                expires_at=time.time() + self.ttl
            )
            self._cache.move_to_end(key)  # Move to end
            
        except Exception as e:
            logger.error("cache_set_error", error=str(e), key=key)
            
    def get_many(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple entries from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict of key -> cached data
        """
        results = {}
        for key in keys:
            if data := self.get(key):
                results[key] = data
        return results
        
    def set_many(self, entries: Dict[str, Dict[str, Any]]) -> None:
        """
        Add multiple entries to cache.
        
        Args:
            entries: Dict of key -> data to cache
        """
        for key, data in entries.items():
            self.set(key, data)