"""
ASTRA Memory Batch Processing
Handles efficient batch operations for memory systems
Created: October 21, 2025
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import structlog
from dataclasses import dataclass
from datetime import datetime

logger = structlog.get_logger()


@dataclass
class BatchOperation:
    """Single batch operation"""
    operation: str  # 'store' or 'retrieve'
    memory_type: str  # 'semantic', 'episodic', 'procedural'
    content: Any
    metadata: Optional[Dict[str, Any]] = None


class BatchProcessor:
    """Processes memory operations in batches for efficiency"""
    
    def __init__(
        self,
        vector_store=None,
        ltm=None,
        max_batch_size: int = 100,
        max_concurrent: int = 4
    ):
        """
        Initialize batch processor.
        
        Args:
            vector_store: Vector store instance
            ltm: LTM instance
            max_batch_size: Maximum operations per batch
            max_concurrent: Maximum concurrent processing threads
        """
        self.vector_store = vector_store
        self.ltm = ltm
        self.max_batch_size = max_batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
        # Batch queues
        self.semantic_queue: List[BatchOperation] = []
        self.episodic_queue: List[BatchOperation] = []
        self.procedural_queue: List[BatchOperation] = []
        
        logger.info("Batch processor initialized",
                   max_batch=max_batch_size,
                   max_concurrent=max_concurrent)
    
    async def add_operation(
        self,
        operation: str,
        memory_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add operation to processing queue.
        
        Args:
            operation: Operation type ('store' or 'retrieve')
            memory_type: Memory type
            content: Operation content
            metadata: Optional metadata
        """
        batch_op = BatchOperation(
            operation=operation,
            memory_type=memory_type,
            content=content,
            metadata=metadata
        )
        
        # Add to appropriate queue
        if memory_type == "semantic":
            self.semantic_queue.append(batch_op)
            if len(self.semantic_queue) >= self.max_batch_size:
                await self.process_semantic_batch()
        
        elif memory_type == "episodic":
            self.episodic_queue.append(batch_op)
            if len(self.episodic_queue) >= self.max_batch_size:
                await self.process_episodic_batch()
        
        elif memory_type == "procedural":
            self.procedural_queue.append(batch_op)
            if len(self.procedural_queue) >= self.max_batch_size:
                await self.process_procedural_batch()
    
    async def process_semantic_batch(self) -> List[str]:
        """
        Process semantic memory batch.
        
        Returns:
            List of operation IDs
        """
        if not self.semantic_queue:
            return []
        
        batch = self.semantic_queue[:self.max_batch_size]
        self.semantic_queue = self.semantic_queue[self.max_batch_size:]
        results = []
        
        # Group by operation type
        stores = [op for op in batch if op.operation == "store"]
        retrieves = [op for op in batch if op.operation == "retrieve"]
        
        # Process stores
        if stores and self.vector_store:
            try:
                # Prepare batch data
                texts = [op.content for op in stores]
                metadata = [op.metadata or {} for op in stores]
                
                # Batch store in vector store
                ids = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.vector_store.add_memories(texts, metadata)
                )
                results.extend(ids)
                
            except Exception as e:
                logger.error(f"Error in batch semantic store: {e}")
        
        # Process retrieves
        if retrieves and self.vector_store:
            try:
                # Prepare queries
                queries = [op.content for op in retrieves]
                
                # Batch retrieve from vector store
                memories = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.vector_store.search_memories(
                        queries=queries,
                        top_k=5  # Configurable
                    )
                )
                results.extend([m["id"] for m in memories])
                
            except Exception as e:
                logger.error(f"Error in batch semantic retrieve: {e}")
        
        return results
    
    async def process_episodic_batch(self) -> List[int]:
        """
        Process episodic memory batch.
        
        Returns:
            List of operation IDs
        """
        if not self.episodic_queue or not self.ltm:
            return []
        
        batch = self.episodic_queue[:self.max_batch_size]
        self.episodic_queue = self.episodic_queue[self.max_batch_size:]
        results = []
        
        # Group by operation
        stores = [op for op in batch if op.operation == "store"]
        retrieves = [op for op in batch if op.operation == "retrieve"]
        
        # Process stores
        if stores:
            try:
                # Prepare batch data
                episodes = []
                for op in stores:
                    if isinstance(op.content, dict):
                        episodes.append({
                            "title": op.content.get("title", ""),
                            "summary": op.content.get("summary", ""),
                            "tags": op.metadata.get("tags", []) if op.metadata else []
                        })
                
                # Batch store episodes
                ids = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: [
                        self.ltm.save_episode(**episode)
                        for episode in episodes
                    ]
                )
                results.extend(ids)
                
            except Exception as e:
                logger.error(f"Error in batch episodic store: {e}")
        
        # Process retrieves
        if retrieves:
            try:
                # Get episodes in date range
                start_date = min(
                    op.metadata.get("start_date", datetime.now())
                    for op in retrieves if op.metadata
                )
                end_date = max(
                    op.metadata.get("end_date", datetime.now())
                    for op in retrieves if op.metadata
                )
                
                episodes = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.ltm.get_episodes(
                        start_date=start_date,
                        end_date=end_date
                    )
                )
                results.extend([e["id"] for e in episodes])
                
            except Exception as e:
                logger.error(f"Error in batch episodic retrieve: {e}")
        
        return results
    
    async def process_procedural_batch(self) -> List[int]:
        """
        Process procedural memory batch.
        
        Returns:
            List of operation IDs
        """
        if not self.procedural_queue or not self.ltm:
            return []
        
        batch = self.procedural_queue[:self.max_batch_size]
        self.procedural_queue = self.procedural_queue[self.max_batch_size:]
        results = []
        
        # Group by operation
        stores = [op for op in batch if op.operation == "store"]
        retrieves = [op for op in batch if op.operation == "retrieve"]
        
        # Process stores
        if stores:
            try:
                # Prepare procedures
                procedures = []
                for op in stores:
                    if isinstance(op.content, dict):
                        procedures.append({
                            "name": op.content.get("name", ""),
                            "steps": op.content.get("steps", []),
                            "tags": op.metadata.get("tags", []) if op.metadata else []
                        })
                
                # Batch store procedures
                ids = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: [
                        self.ltm.save_procedure(**proc)
                        for proc in procedures
                    ]
                )
                results.extend(ids)
                
            except Exception as e:
                logger.error(f"Error in batch procedural store: {e}")
        
        # Process retrieves
        if retrieves:
            try:
                # Get procedures by tags
                tags = set()
                for op in retrieves:
                    if op.metadata and "tags" in op.metadata:
                        tags.update(op.metadata["tags"])
                
                procedures = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.ltm.get_procedures(list(tags))
                )
                results.extend([p["id"] for p in procedures])
                
            except Exception as e:
                logger.error(f"Error in batch procedural retrieve: {e}")
        
        return results
    
    async def flush(self) -> Dict[str, List]:
        """
        Process all remaining operations.
        
        Returns:
            Results by memory type
        """
        results = {
            "semantic": [],
            "episodic": [],
            "procedural": []
        }
        
        # Process remaining operations
        if self.semantic_queue:
            results["semantic"] = await self.process_semantic_batch()
        
        if self.episodic_queue:
            results["episodic"] = await self.process_episodic_batch()
        
        if self.procedural_queue:
            results["procedural"] = await self.process_procedural_batch()
        
        return results
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes"""
        return {
            "semantic": len(self.semantic_queue),
            "episodic": len(self.episodic_queue),
            "procedural": len(self.procedural_queue)
        }