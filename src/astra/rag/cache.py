"""
Distributed caching layer for RAG with TTL and LRU eviction
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List, Set
import time
import json
from pathlib import Path
import structlog
from dataclasses import dataclass
import hashlib
from collections import OrderedDict
import threading
import asyncio
from contextlib import asynccontextmanager

logger = structlog.get_logger(__name__)

@dataclass
class CacheConfig:
    """Configuration for RAG cache"""
    max_size: int = 10000  # Maximum number of entries
    ttl: int = 3600  # Default TTL in seconds
    persist_dir: Optional[str] = None  # Directory for persistence
    shard_bits: int = 4  # Number of bits for consistent hashing
    checksum_keys: bool = True  # Use content checksums as keys

class ConsistentHashRing:
    """Simple consistent hashing implementation"""
    
    def __init__(self, num_slots: int = 16):
        self.slots = num_slots
        self.nodes: Dict[int, str] = {}
        
    def _hash(self, key: str) -> int:
        """Get slot for key"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.slots
        
    def add_node(self, node_id: str) -> None:
        """Add node to ring"""
        slot = self._hash(node_id)
        self.nodes[slot] = node_id
        
    def remove_node(self, node_id: str) -> None:
        """Remove node from ring"""
        slot = self._hash(node_id)
        self.nodes.pop(slot, None)
        
    def get_node(self, key: str) -> Optional[str]:
        """Get node for key"""
        if not self.nodes:
            return None
            
        slot = self._hash(key)
        # Find next available slot
        while slot < self.slots:
            if slot in self.nodes:
                return self.nodes[slot]
            slot += 1
        # Wrap around
        slot = 0
        while slot < self._hash(key):
            if slot in self.nodes:
                return self.nodes[slot]
            slot += 1
        return None

class RAGCache:
    """
    Distributed cache for RAG results with TTL and LRU eviction
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize cache"""
        self.config = config or CacheConfig()
        self.logger = logger.bind(component="rag_cache")
        
        # Initialize cache structures
        self._cache: OrderedDict[str, Dict] = OrderedDict()
        self._ttls: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        # Initialize consistent hashing
        self.ring = ConsistentHashRing(2 ** self.config.shard_bits)
        self.ring.add_node("primary")  # Single node for now
        
        # Load persistent cache if configured
        if self.config.persist_dir:
            self._load_persistent()
            
        self.logger.info("cache_initialized",
                        max_size=self.config.max_size,
                        ttl=self.config.ttl)
                        
    def _create_key(self, query: str, params: Dict) -> str:
        """Create cache key from query and params"""
        if self.config.checksum_keys:
            # Use content hash as key
            content = json.dumps({
                "query": query,
                "params": params
            }, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
        else:
            # Use query directly
            return query
            
    def _evict_expired(self) -> None:
        """Remove expired entries"""
        now = time.time()
        expired = set()
        
        for key, expires_at in self._ttls.items():
            if expires_at <= now:
                expired.add(key)
                
        for key in expired:
            self._cache.pop(key, None)
            self._ttls.pop(key, None)
            
        if expired:
            self.logger.debug("cache_evicted",
                            count=len(expired))
                            
    def _enforce_size_limit(self) -> None:
        """Remove oldest entries if cache exceeds max size"""
        while len(self._cache) > self.config.max_size:
            self._cache.popitem(last=False)  # Remove oldest
            
    @asynccontextmanager
    async def _lock_key(self, key: str):
        """Lock for concurrent access to key"""
        with self._lock:
            yield
            
    def get(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Get cached results for query
        
        Args:
            query: Search query
            params: Optional parameters affecting results
            
        Returns:
            Cached results or None if not found/expired
        """
        params = params or {}
        key = self._create_key(query, params)
        
        with self._lock:
            # Check expiry
            if key in self._ttls:
                if time.time() > self._ttls[key]:
                    # Expired
                    self._cache.pop(key, None)
                    self._ttls.pop(key)
                    return None
                    
            # Get from cache
            if key in self._cache:
                # Move to end (most recent)
                self._cache.move_to_end(key)
                return self._cache[key]
                
        return None
        
    def set(
        self,
        query: str,
        results: Dict,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache results for query
        
        Args:
            query: Search query
            results: Results to cache
            params: Optional parameters affecting results
            ttl: Optional TTL override
        """
        params = params or {}
        key = self._create_key(query, params)
        ttl = ttl or self.config.ttl
        
        with self._lock:
            # Evict expired
            self._evict_expired()
            
            # Add new entry
            self._cache[key] = results
            self._ttls[key] = time.time() + ttl
            
            # Move to end (most recent)
            self._cache.move_to_end(key)
            
            # Enforce size limit
            self._enforce_size_limit()
            
            # Persist if configured
            if self.config.persist_dir:
                self._persist_key(key)
                
    def _persist_key(self, key: str) -> None:
        """Persist single cache entry"""
        if not self.config.persist_dir:
            return
            
        path = Path(self.config.persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        # Shard by key prefix
        shard = key[:2]
        shard_dir = path / shard
        shard_dir.mkdir(exist_ok=True)
        
        entry = {
            "data": self._cache[key],
            "expires_at": self._ttls[key]
        }
        
        with open(shard_dir / f"{key}.json", "w") as f:
            json.dump(entry, f)
            
    def _load_persistent(self) -> None:
        """Load persistent cache entries"""
        if not self.config.persist_dir:
            return
            
        path = Path(self.config.persist_dir)
        if not path.exists():
            return
            
        now = time.time()
        loaded = 0
        
        # Load each shard
        for shard in path.iterdir():
            if not shard.is_dir():
                continue
                
            # Load entries in shard
            for entry_file in shard.glob("*.json"):
                try:
                    with open(entry_file) as f:
                        entry = json.load(f)
                        
                    # Skip if expired
                    if entry["expires_at"] <= now:
                        entry_file.unlink()
                        continue
                        
                    key = entry_file.stem
                    self._cache[key] = entry["data"]
                    self._ttls[key] = entry["expires_at"]
                    loaded += 1
                    
                except Exception as e:
                    self.logger.error("cache_load_failed",
                                    file=str(entry_file),
                                    error=str(e))
                    
        self.logger.info("cache_loaded", entries=loaded)
        
    def invalidate(
        self,
        query: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> None:
        """
        Invalidate cache entries
        
        Args:
            query: Optional query to invalidate
            params: Optional parameters to match
            
        If no query specified, invalidates all entries
        """
        with self._lock:
            if query:
                # Invalidate specific query
                key = self._create_key(query, params or {})
                self._cache.pop(key, None)
                self._ttls.pop(key, None)
                
                if self.config.persist_dir:
                    path = Path(self.config.persist_dir)
                    shard = key[:2]
                    entry_file = path / shard / f"{key}.json"
                    if entry_file.exists():
                        entry_file.unlink()
            else:
                # Invalidate all
                self._cache.clear()
                self._ttls.clear()
                
                if self.config.persist_dir:
                    path = Path(self.config.persist_dir)
                    if path.exists():
                        for file in path.glob("**/*.json"):
                            file.unlink()
                            
            self.logger.info("cache_invalidated",
                           query=query or "all")