"""
ASTRA Memory Cache
Implements caching for frequently accessed memories
Created: October 21, 2025
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import time
from collections import OrderedDict
import structlog

logger = structlog.get_logger()


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    content: Any
    timestamp: float
    access_count: int
    last_access: float


class LRUCache:
    """Least Recently Used (LRU) cache with access counting"""
    
    def __init__(self, max_size: int = 1000, ttl: float = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to store
            ttl: Time to live in seconds (default 1 hour)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value if found and not expired
        """
        try:
            entry = self._cache[key]
            
            # Check expiration
            if time.time() - entry.timestamp > self.ttl:
                self._cache.pop(key)
                self.misses += 1
                return None
            
            # Update access metadata
            entry.access_count += 1
            entry.last_access = time.time()
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            self.hits += 1
            return entry.content
            
        except KeyError:
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """
        Store item in cache.
        
        Args:
            key: Cache key
            value: Value to store
        """
        # Remove oldest if at max size
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        
        now = time.time()
        self._cache[key] = CacheEntry(
            content=value,
            timestamp=now,
            access_count=1,
            last_access=now
        )
        
        # Move to end
        self._cache.move_to_end(key)
    
    def remove(self, key: str) -> None:
        """Remove item from cache"""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all items from cache"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hit_ratio,
            "oldest_entry_age": min(time.time() - e.timestamp for e in self._cache.values()) if self._cache else 0,
            "newest_entry_age": max(time.time() - e.timestamp for e in self._cache.values()) if self._cache else 0,
            "most_accessed": max(e.access_count for e in self._cache.values()) if self._cache else 0,
        }