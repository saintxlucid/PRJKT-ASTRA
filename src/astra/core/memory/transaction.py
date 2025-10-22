"""
Memory transaction support for atomic operations.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, AsyncGenerator
import structlog
import sqlite3
import chromadb
from pathlib import Path

logger = structlog.get_logger()

class MemoryTransaction:
    """Handles atomic memory operations across stores"""
    
    def __init__(self, database_path: Path, chroma_client: chromadb.Client):
        self.database_path = database_path
        self.chroma_client = chroma_client
        self.operations: List[Dict[str, Any]] = []
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        
    async def __aenter__(self) -> 'MemoryTransaction':
        """Start transaction"""
        self._sqlite_conn = sqlite3.connect(self.database_path)
        self._sqlite_conn.execute("BEGIN TRANSACTION")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """End transaction"""
        if self._sqlite_conn:
            if exc_type is None:
                try:
                    # Verify Chroma operations first since they can't be rolled back
                    for op in self.operations:
                        if op["store"] == "chroma":
                            if not await self._verify_chroma_op(op):
                                raise Exception("Chroma operation verification failed")
                    
                    # If Chroma verified, commit SQLite
                    self._sqlite_conn.commit()
                except:
                    self._sqlite_conn.rollback()
                    raise
            else:
                self._sqlite_conn.rollback()
            self._sqlite_conn.close()
            
    async def add_operation(self, store: str, operation: Dict[str, Any]) -> None:
        """Add operation to transaction"""
        self.operations.append({
            "store": store,
            "operation": operation
        })
        
    async def _verify_chroma_op(self, operation: Dict[str, Any]) -> bool:
        """Verify a Chroma operation was successful"""
        try:
            collection = self.chroma_client.get_collection("semantic")
            result = collection.get(
                ids=[operation["operation"]["id"]], 
                include=["metadatas"]
            )
            return len(result["ids"]) > 0
        except Exception as e:
            logger.error("Failed to verify Chroma operation", error=str(e))
            return False

@asynccontextmanager
async def memory_transaction(
    database_path: Path,
    chroma_client: chromadb.Client
) -> AsyncGenerator[MemoryTransaction, None]:
    """Context manager for memory transactions"""
    transaction = MemoryTransaction(database_path, chroma_client)
    try:
        async with transaction as tx:
            yield tx
    except Exception as e:
        logger.error("Transaction failed", error=str(e))
        raise