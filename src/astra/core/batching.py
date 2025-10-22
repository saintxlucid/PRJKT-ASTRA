"""
Batching utilities for efficient processing.
"""
from typing import TypeVar, List, Callable, Iterable, Generator, Any
import asyncio
import structlog
from concurrent.futures import ThreadPoolExecutor

logger = structlog.get_logger()

T = TypeVar('T')
U = TypeVar('U')

def batched(seq: List[T], size: int) -> Generator[List[T], None, None]:
    """
    Split sequence into batches of specified size.
    
    Args:
        seq: Input sequence
        size: Batch size
        
    Yields:
        Batches of items
    """
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def map_batched(
    items: List[T],
    fn: Callable[[List[T]], List[U]],
    batch_size: int = 32,
    max_workers: Optional[int] = None
) -> List[U]:
    """
    Apply function to batches of items in parallel.
    
    Args:
        items: Input items
        fn: Function to apply to each batch
        batch_size: Size of batches
        max_workers: Maximum number of worker threads
        
    Returns:
        Combined results from all batches
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        # Submit batch jobs
        for batch in batched(items, batch_size):
            future = executor.submit(fn, batch)
            futures.append(future)
        
        # Collect results
        for future in futures:
            try:
                batch_result = future.result()
                results.extend(batch_result)
            except Exception as e:
                logger.error("batch_processing_failed",
                           error=str(e))
                raise
    
    return results


async def async_map_batched(
    items: List[T],
    fn: Callable[[List[T]], List[U]],
    batch_size: int = 32,
    max_workers: Optional[int] = None
) -> List[U]:
    """
    Asynchronously apply function to batches of items.
    
    Args:
        items: Input items
        fn: Async function to apply to each batch
        batch_size: Size of batches
        max_workers: Maximum number of concurrent tasks
        
    Returns:
        Combined results from all batches
    """
    results = []
    tasks = []
    
    for batch in batched(items, batch_size):
        if max_workers and len(tasks) >= max_workers:
            # Wait for some tasks to complete
            done, tasks = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Process completed tasks
            for task in done:
                try:
                    batch_result = await task
                    results.extend(batch_result)
                except Exception as e:
                    logger.error("async_batch_processing_failed",
                               error=str(e))
                    raise
        
        # Create new task
        task = asyncio.create_task(fn(batch))
        tasks.append(task)
    
    # Wait for remaining tasks
    if tasks:
        done = await asyncio.gather(*tasks, return_exceptions=True)
        for batch_result in done:
            if isinstance(batch_result, Exception):
                raise batch_result
            results.extend(batch_result)
    
    return results


class BatchProcessor:
    """
    Manages batch processing with automatic size adjustment.
    """
    
    def __init__(
        self,
        initial_size: int = 32,
        min_size: int = 8,
        max_size: int = 128,
        target_time: float = 0.1
    ):
        """
        Initialize batch processor.
        
        Args:
            initial_size: Starting batch size
            min_size: Minimum batch size
            max_size: Maximum batch size
            target_time: Target processing time per batch in seconds
        """
        self.batch_size = initial_size
        self.min_size = min_size
        self.max_size = max_size
        self.target_time = target_time
        
        logger.info("batch_processor_initialized",
                   initial_size=initial_size,
                   min_size=min_size,
                   max_size=max_size,
                   target_time=target_time)
    
    def process(
        self,
        items: List[T],
        fn: Callable[[List[T]], List[U]]
    ) -> List[U]:
        """
        Process items in automatically-sized batches.
        
        Args:
            items: Items to process
            fn: Processing function
            
        Returns:
            Combined results
        """
        results = []
        
        for batch in batched(items, self.batch_size):
            start_time = time.time()
            
            try:
                batch_result = fn(batch)
                results.extend(batch_result)
                
                # Adjust batch size based on processing time
                elapsed = time.time() - start_time
                
                if elapsed > self.target_time * 1.5:
                    # Too slow - decrease size
                    self.batch_size = max(
                        self.min_size,
                        int(self.batch_size * 0.8)
                    )
                elif elapsed < self.target_time * 0.5:
                    # Too fast - increase size
                    self.batch_size = min(
                        self.max_size,
                        int(self.batch_size * 1.2)
                    )
                
                logger.debug("batch_processed",
                           batch_size=len(batch),
                           elapsed=elapsed,
                           new_size=self.batch_size)
                
            except Exception as e:
                logger.error("batch_processing_failed",
                           batch_size=len(batch),
                           error=str(e))
                raise
        
        return results