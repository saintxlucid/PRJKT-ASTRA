"""
ASTRA Memory Management
Handles memory cleanup, usage tracking, and optimization
Created: October 21, 2025
"""

from typing import Dict, Any, Optional, List, Set
import time
import gc
import psutil
import os
import structlog
from pathlib import Path
import sqlite3
import chromadb

logger = structlog.get_logger()


class MemoryManager:
    """Manages memory resources and cleanup"""
    
    def __init__(
        self,
        vector_store=None,
        database_path: Optional[Path] = None,
        max_memory_percent: float = 85.0,
        cleanup_interval: int = 3600
    ):
        """
        Initialize memory manager.
        
        Args:
            vector_store: Vector store instance
            database_path: Path to SQLite database
            max_memory_percent: Maximum memory usage percentage
            cleanup_interval: Seconds between cleanup runs
        """
        self.vector_store = vector_store
        self.database_path = database_path
        self.max_memory_percent = max_memory_percent
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = 0.0
        
        # Track deleted items for cache invalidation
        self.deleted_items: Set[str] = set()
        
        logger.info("Memory manager initialized",
                   max_memory=f"{max_memory_percent}%",
                   cleanup_interval=f"{cleanup_interval}s")
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """
        Check current memory usage.
        
        Returns:
            Dictionary with memory statistics
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        stats = {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": process.memory_percent(),
            "gc_count": gc.get_count(),
            "gc_threshold": gc.get_threshold()
        }
        
        # Check vector store size
        if self.vector_store:
            try:
                vector_size = self.vector_store.get_memory_count()
                stats["vector_store_size"] = vector_size
            except Exception as e:
                logger.error(f"Error getting vector store size: {e}")
        
        # Check database size
        if self.database_path and self.database_path.exists():
            stats["database_size"] = self.database_path.stat().st_size
        
        return stats
    
    def needs_cleanup(self) -> bool:
        """Check if cleanup is needed based on memory usage or time"""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return False
        
        stats = self.check_memory_usage()
        return stats["percent"] > self.max_memory_percent
    
    async def cleanup(self) -> Dict[str, Any]:
        """
        Perform memory cleanup.
        
        Returns:
            Cleanup statistics
        """
        logger.info("Starting memory cleanup")
        start_time = time.time()
        stats_before = self.check_memory_usage()
        
        cleanup_stats = {
            "gc_collected": 0,
            "vector_items_removed": 0,
            "database_items_removed": 0,
            "cache_items_removed": 0
        }
        
        # Force garbage collection
        gc.collect()
        cleanup_stats["gc_collected"] = sum(gc.get_count())
        
        # Clean vector store
        if self.vector_store:
            try:
                # Remove old or low-relevance vectors
                removed = await self._cleanup_vector_store()
                cleanup_stats["vector_items_removed"] = removed
            except Exception as e:
                logger.error(f"Error cleaning vector store: {e}")
        
        # Clean SQLite database
        if self.database_path and self.database_path.exists():
            try:
                removed = await self._cleanup_database()
                cleanup_stats["database_items_removed"] = removed
            except Exception as e:
                logger.error(f"Error cleaning database: {e}")
        
        # Update timestamps
        self.last_cleanup = time.time()
        cleanup_stats["duration"] = self.last_cleanup - start_time
        
        # Get final stats
        stats_after = self.check_memory_usage()
        cleanup_stats["memory_freed"] = stats_before["rss"] - stats_after["rss"]
        
        logger.info("Memory cleanup complete",
                   duration=f"{cleanup_stats['duration']:.2f}s",
                   freed=f"{cleanup_stats['memory_freed'] / 1024 / 1024:.1f}MB")
        
        return cleanup_stats
    
    async def _cleanup_vector_store(self) -> int:
        """
        Clean up old or irrelevant vectors.
        
        Returns:
            Number of items removed
        """
        if not self.vector_store:
            return 0
        
        try:
            # Get all vectors with metadata
            all_vectors = self.vector_store.get_memories()
            removed = 0
            
            for vector in all_vectors:
                # Check age and relevance
                metadata = vector.get("metadata", {})
                timestamp = metadata.get("timestamp", 0)
                relevance = metadata.get("relevance", 0.0)
                
                # Remove if older than 30 days and low relevance
                if (time.time() - timestamp > 30 * 86400 and
                    relevance < 0.3):
                    self.vector_store.delete_memory(vector["id"])
                    self.deleted_items.add(vector["id"])
                    removed += 1
            
            return removed
            
        except Exception as e:
            logger.error(f"Error in vector store cleanup: {e}")
            return 0
    
    async def _cleanup_database(self) -> int:
        """
        Clean up old database entries.
        
        Returns:
            Number of items removed
        """
        if not self.database_path or not self.database_path.exists():
            return 0
        
        try:
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()
            removed = 0
            
            # Clean episodic memories older than 90 days
            cursor.execute("""
                DELETE FROM episodic 
                WHERE timestamp < datetime('now', '-90 days')
            """)
            removed += cursor.rowcount
            
            # Clean unused procedural memories
            cursor.execute("""
                DELETE FROM procedural
                WHERE last_used < datetime('now', '-180 days')
                AND usage_count < 5
            """)
            removed += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return removed
            
        except Exception as e:
            logger.error(f"Error in database cleanup: {e}")
            return 0
    
    def invalidate_cache(self, memory_id: str) -> None:
        """
        Mark memory as deleted for cache invalidation.
        
        Args:
            memory_id: ID of deleted memory
        """
        self.deleted_items.add(memory_id)
    
    def is_deleted(self, memory_id: str) -> bool:
        """
        Check if memory was deleted.
        
        Args:
            memory_id: Memory ID to check
        
        Returns:
            True if memory was deleted
        """
        return memory_id in self.deleted_items
    
    def clear_deleted_tracking(self) -> None:
        """Clear deleted items tracking"""
        self.deleted_items.clear()