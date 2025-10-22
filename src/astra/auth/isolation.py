"""
User memory and resource isolation manager.
"""

from typing import Dict, List, Optional, Any
import asyncio
import structlog
from prometheus_client import Counter, Histogram

from .quota import quota_manager
from .persistence import memory_store

logger = structlog.get_logger(__name__)

# Metrics
MEMORY_ISOLATION_ERRORS = Counter(
    "astra_memory_isolation_errors_total",
    "Memory isolation errors by type",
    ["error_type"]
)

MEMORY_ACCESS_LATENCY = Histogram(
    "astra_memory_access_latency_seconds",
    "Memory access latency with isolation",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25)
)

class MemoryIsolation:
    """Handles per-user memory isolation."""

    def __init__(self):
        """Initialize memory isolation."""
        self.user_memories: Dict[str, Dict[str, Any]] = {}
        self.user_locks: Dict[str, asyncio.Lock] = {}
        self._load_lock = asyncio.Lock()
        self._initialized = False
        
    async def ensure_initialized(self) -> None:
        """Ensure the memory store is initialized."""
        if not self._initialized:
            async with self._load_lock:
                if not self._initialized:
                    await memory_store.initialize()
                    self._initialized = True
        
    async def _ensure_loaded(self, user_id: str) -> None:
        """Ensure user's memory is loaded from persistence."""
        if user_id not in self.user_memories:
            async with self._load_lock:
                # Check again in case another task loaded it
                if user_id not in self.user_memories:
                    self.user_memories[user_id] = await memory_store.load_all(user_id)

    async def get_user_memory(self, user_id: str, key: str) -> Optional[Any]:
        """Get value from user's isolated memory."""
        start_time = asyncio.get_event_loop().time()
        try:
            await self.ensure_initialized()
            await self._ensure_loaded(user_id)
            
            async with self._get_user_lock(user_id):
                value = self.user_memories[user_id].get(key)
                
            latency = asyncio.get_event_loop().time() - start_time
            MEMORY_ACCESS_LATENCY.labels(operation="read").observe(latency)
            
            return value
            
        except Exception as e:
            MEMORY_ISOLATION_ERRORS.labels(error_type="read").inc()
            logger.error("memory_read_error", 
                        user_id=user_id,
                        key=key,
                        error=str(e))
            raise

    async def set_user_memory(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> None:
        """Set value in user's isolated memory."""
        start_time = asyncio.get_event_loop().time()
        try:
            await self.ensure_initialized()
            await self._ensure_loaded(user_id)
            
            # Check quotas before proceeding
            current_keys = len(self.user_memories.get(user_id, {}))
            old_value = self.user_memories.get(user_id, {}).get(key)
            
            if not quota_manager.check_key_quota(user_id, current_keys):
                raise ValueError(f"Key quota exceeded for user {user_id}")
                
            if not quota_manager.check_value_size(user_id, value):
                raise ValueError(f"Value size quota exceeded for user {user_id}")
                
            if not quota_manager.check_total_quota(user_id, value):
                raise ValueError(f"Total memory quota exceeded for user {user_id}")
            
            if user_id not in self.user_memories:
                self.user_memories[user_id] = {}
            
            async with self._get_user_lock(user_id):
                # Update persistence first
                await memory_store.set(user_id, key, value)
                # Then update in-memory cache
                self.user_memories[user_id][key] = value
                quota_manager.update_usage(user_id, old_value, value)
                
            latency = asyncio.get_event_loop().time() - start_time
            MEMORY_ACCESS_LATENCY.labels(operation="write").observe(latency)
            
        except Exception as e:
            MEMORY_ISOLATION_ERRORS.labels(error_type="write").inc()
            logger.error("memory_write_error",
                        user_id=user_id,
                        key=key,
                        error=str(e))
            raise

    async def delete_user_memory(self, user_id: str, key: str) -> bool:
        """Delete value from user's isolated memory."""
        start_time = asyncio.get_event_loop().time()
        try:
            await self.ensure_initialized()
            await self._ensure_loaded(user_id)
            
            async with self._get_user_lock(user_id):
                if key in self.user_memories[user_id]:
                    old_value = self.user_memories[user_id][key]
                    # Update persistence first
                    await memory_store.delete(user_id, key)
                    # Then update in-memory cache
                    del self.user_memories[user_id][key]
                    quota_manager.update_usage(user_id, old_value, None)
                    
            latency = asyncio.get_event_loop().time() - start_time
            MEMORY_ACCESS_LATENCY.labels(operation="delete").observe(latency)
            
            return True
            
        except Exception as e:
            MEMORY_ISOLATION_ERRORS.labels(error_type="delete").inc()
            logger.error("memory_delete_error",
                        user_id=user_id,
                        key=key,
                        error=str(e))
            raise

    async def list_user_memory(self, user_id: str) -> List[str]:
        """List all keys in user's isolated memory."""
        start_time = asyncio.get_event_loop().time()
        try:
            await self.ensure_initialized()
            await self._ensure_loaded(user_id)
            
            async with self._get_user_lock(user_id):
                keys = list(self.user_memories[user_id].keys())
                
            latency = asyncio.get_event_loop().time() - start_time
            MEMORY_ACCESS_LATENCY.labels(operation="list").observe(latency)
            
            return keys
            
        except Exception as e:
            MEMORY_ISOLATION_ERRORS.labels(error_type="list").inc()
            logger.error("memory_list_error",
                        user_id=user_id,
                        error=str(e))
            raise

    async def clear_user_memory(self, user_id: str) -> None:
        """Clear all memory for a user."""
        start_time = asyncio.get_event_loop().time()
        try:
            await self.ensure_initialized()
            async with self._get_user_lock(user_id):
                # Update persistence first
                await memory_store.clear(user_id)
                # Then update in-memory cache
                if user_id in self.user_memories:
                    del self.user_memories[user_id]
                    quota_manager.clear_usage(user_id)
                    
            latency = asyncio.get_event_loop().time() - start_time
            MEMORY_ACCESS_LATENCY.labels(operation="clear").observe(latency)
            
        except Exception as e:
            MEMORY_ISOLATION_ERRORS.labels(error_type="clear").inc()
            logger.error("memory_clear_error",
                        user_id=user_id,
                        error=str(e))
            raise

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create lock for user's memory."""
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]

# Global memory isolation instance
memory_isolation = MemoryIsolation()