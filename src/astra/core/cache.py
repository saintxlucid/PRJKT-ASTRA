"""
Core caching infrastructure with multi-tier storage.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
import threading
from collections import OrderedDict
from pathlib import Path
import structlog

logger = structlog.get_logger()

class LRU:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.data = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, k: str) -> Any:
        with self.lock:
            v = self.data.get(k)
            if v is None:
                self.misses += 1
                return None
            self.hits += 1
            self.data.move_to_end(k)
            return v
    
    def set(self, k: str, v: Any) -> None:
        with self.lock:
            self.data[k] = v
            self.data.move_to_end(k)
            if len(self.data) > self.capacity:
                self.data.popitem(last=False)
    
    def clear(self) -> None:
        """Clear cache and reset stats."""
        with self.lock:
            self.data.clear()
            self.hits = 0
            self.misses = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / max(1, total)


class SqliteStore:
    """Persistent SQLite-based cache with TTL support."""
    
    def __init__(self, path: str = "cache/cache.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                k TEXT PRIMARY KEY,
                v BLOB,
                ttl REAL,
                created REAL,
                component TEXT
            )
        """)
        self.db.commit()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, k: str) -> Any:
        with self.lock:
            row = self.db.execute(
                "SELECT v, ttl FROM kv WHERE k=?", 
                (k,)
            ).fetchone()
            
            if not row:
                self.misses += 1
                return None
                
            v, ttl = row
            if ttl and ttl < time.time():
                self.db.execute("DELETE FROM kv WHERE k=?", (k,))
                self.db.commit()
                self.misses += 1
                return None
                
            self.hits += 1
            return v
    
    def set(self, k: str, v: Any, ttl_s: Optional[float] = None, 
            component: Optional[str] = None) -> None:
        expire = time.time() + ttl_s if ttl_s else None
        created = time.time()
        
        with self.lock:
            self.db.execute(
                """
                INSERT OR REPLACE INTO kv(k,v,ttl,created,component) 
                VALUES(?,?,?,?,?)
                """,
                (k, v, expire, created, component)
            )
            self.db.commit()
    
    def vacuum(self) -> None:
        """Remove expired entries and optimize storage."""
        with self.lock:
            self.db.execute("DELETE FROM kv WHERE ttl < ?", (time.time(),))
            self.db.execute("VACUUM")
            self.db.commit()
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / max(1, total)


def cache_key(component: str, payload: dict) -> str:
    """Generate stable cache key from component and payload."""
    raw = json.dumps(
        {"c": component, **payload},
        sort_keys=True,
        ensure_ascii=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


class Cache:
    """Multi-tier caching system with memory and disk storage."""
    
    def __init__(self, memory_cap: int = 2048, ttl_s: float = 3600):
        self.mem = LRU(memory_cap)
        self.disk = SqliteStore()
        self.ttl = ttl_s
        logger.info("cache_initialized",
                   memory_cap=memory_cap,
                   ttl_s=ttl_s)
    
    def get(self, key: str) -> Any:
        """Get value from cache, trying memory then disk."""
        # Try memory first
        v = self.mem.get(key)
        if v is not None:
            logger.debug("cache_hit_memory", key=key)
            return v
            
        # Fall back to disk
        v = self.disk.get(key)
        if v is not None:
            # Promote to memory
            self.mem.set(key, v)
            logger.debug("cache_hit_disk", key=key)
            return v
            
        logger.debug("cache_miss", key=key)
        return None
    
    def set(self, key: str, value: Any, ttl_s: Optional[float] = None,
            component: Optional[str] = None) -> None:
        """Set value in both memory and disk cache."""
        self.mem.set(key, value)
        self.disk.set(
            key, 
            value,
            ttl_s or self.ttl,
            component
        )
        logger.debug("cache_set",
                    key=key,
                    ttl_s=ttl_s,
                    component=component)
    
    def clear_memory(self) -> None:
        """Clear memory cache."""
        self.mem.clear()
        logger.info("memory_cache_cleared")
    
    def vacuum_disk(self) -> None:
        """Clean up disk cache."""
        self.disk.vacuum()
        logger.info("disk_cache_vacuumed")
    
    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "memory_hit_rate": self.mem.hit_rate,
            "disk_hit_rate": self.disk.hit_rate,
            "memory_size": len(self.mem.data),
            "memory_capacity": self.mem.capacity
        }


# Global cache instance
CACHE = Cache()