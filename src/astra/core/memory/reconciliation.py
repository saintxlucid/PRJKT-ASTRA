"""
Memory store reconciliation job to ensure consistency between cache and long-term storage.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set
import structlog

from astra.core.metrics import MEMORY_METRICS
from astra.core.memory.write_cache import MemoryWriteCache

logger = structlog.get_logger(__name__)

@dataclass
class ReconciliationReport:
    """Results from a reconciliation run"""
    start_time: datetime
    end_time: datetime
    semantic_diffs: int = 0
    episodic_diffs: int = 0 
    procedural_diffs: int = 0
    errors: List[str] = None

    @property
    def total_diffs(self) -> int:
        return self.semantic_diffs + self.episodic_diffs + self.procedural_diffs

    def __str__(self) -> str:
        duration = (self.end_time - self.start_time).total_seconds()
        return (
            f"Reconciliation Report:\n"
            f"Duration: {duration:.2f}s\n"
            f"Semantic Diffs: {self.semantic_diffs}\n"
            f"Episodic Diffs: {self.episodic_diffs}\n"
            f"Procedural Diffs: {self.procedural_diffs}\n"
            f"Total Diffs: {self.total_diffs}\n"
            f"Errors: {len(self.errors or [])} errors"
        )

class MemoryReconciliationJob:
    """
    Job to reconcile memory stores and ensure consistency.
    Runs verification between write-through cache and long-term storage.
    """
    
    def __init__(self, write_cache: MemoryWriteCache):
        self.write_cache = write_cache
        self.errors: List[str] = []
        
    async def reconcile(self) -> ReconciliationReport:
        """
        Run full reconciliation across all memory types.
        
        Returns:
            ReconciliationReport with results
        """
        start_time = datetime.now()
        self.errors = []
        
        try:
            # Reconcile each memory type
            semantic_diffs = await self._reconcile_semantic()
            episodic_diffs = await self._reconcile_episodic() 
            procedural_diffs = await self._reconcile_procedural()

            # Record metrics
            MEMORY_METRICS.observe_reconciliation_diffs(
                semantic_diffs,
                episodic_diffs,
                procedural_diffs
            )
            
            return ReconciliationReport(
                start_time=start_time,
                end_time=datetime.now(),
                semantic_diffs=semantic_diffs,
                episodic_diffs=episodic_diffs,
                procedural_diffs=procedural_diffs,
                errors=self.errors
            )
            
        except Exception as e:
            self.errors.append(f"Reconciliation failed: {str(e)}")
            logger.error("Reconciliation job failed", error=str(e))
            return ReconciliationReport(
                start_time=start_time,
                end_time=datetime.now(),
                errors=self.errors
            )

    async def _reconcile_semantic(self) -> int:
        """Reconcile semantic memories between cache and Chroma"""
        try:
            # Get IDs from both stores
            cache_ids = await self.write_cache.get_semantic_ids()
            chroma_ids = await self.write_cache.get_chroma_ids()
            
            # Find differences
            cache_only = cache_ids - chroma_ids
            chroma_only = chroma_ids - cache_ids
            
            # Process cache-only entries
            for memory_id in cache_only:
                try:
                    memory = await self.write_cache.get_semantic(memory_id)
                    if memory:
                        # Re-insert into Chroma
                        await self.write_cache.write_semantic_to_chroma(
                            memory_id,
                            memory["text"],
                            memory["metadata"]
                        )
                except Exception as e:
                    self.errors.append(f"Error reconciling semantic {memory_id}: {str(e)}")
                    
            # Log any Chroma-only entries as warnings
            for memory_id in chroma_only:
                logger.warning("Found Chroma-only semantic memory", id=memory_id)
                
            return len(cache_only) + len(chroma_only)
            
        except Exception as e:
            self.errors.append(f"Semantic reconciliation failed: {str(e)}")
            return 0

    async def _reconcile_episodic(self) -> int:
        """Reconcile episodic memories between cache and SQLite"""
        try:
            # Get IDs from both stores
            cache_ids = await self.write_cache.get_episodic_ids()
            sqlite_ids = await self.write_cache.get_sqlite_episodic_ids()
            
            # Find differences
            cache_only = cache_ids - sqlite_ids
            sqlite_only = sqlite_ids - cache_ids
            
            # Process cache-only entries
            for memory_id in cache_only:
                try:
                    memory = await self.write_cache.get_episodic(memory_id)
                    if memory:
                        # Re-insert into SQLite
                        await self.write_cache.write_episodic_to_sqlite(
                            memory_id,
                            memory["text"],
                            memory["metadata"]
                        )
                except Exception as e:
                    self.errors.append(f"Error reconciling episodic {memory_id}: {str(e)}")
                    
            # Log any SQLite-only entries as warnings
            for memory_id in sqlite_only:
                logger.warning("Found SQLite-only episodic memory", id=memory_id)
                
            return len(cache_only) + len(sqlite_only)
            
        except Exception as e:
            self.errors.append(f"Episodic reconciliation failed: {str(e)}")
            return 0

    async def _reconcile_procedural(self) -> int:
        """Reconcile procedural memories between cache and SQLite"""
        try:
            # Get names from both stores (procedures use names as IDs)
            cache_names = await self.write_cache.get_procedural_names()
            sqlite_names = await self.write_cache.get_sqlite_procedural_names()
            
            # Find differences
            cache_only = cache_names - sqlite_names
            sqlite_only = sqlite_names - cache_names
            
            # Process cache-only entries
            for name in cache_only:
                try:
                    procedure = await self.write_cache.get_procedural(name)
                    if procedure:
                        # Re-insert into SQLite
                        await self.write_cache.write_procedural_to_sqlite(
                            procedure["name"],
                            procedure["script"],
                            procedure["tags"]
                        )
                except Exception as e:
                    self.errors.append(f"Error reconciling procedure {name}: {str(e)}")
                    
            # Log any SQLite-only entries as warnings
            for name in sqlite_only:
                logger.warning("Found SQLite-only procedure", name=name)
                
            return len(cache_only) + len(sqlite_only)
            
        except Exception as e:
            self.errors.append(f"Procedural reconciliation failed: {str(e)}")
            return 0