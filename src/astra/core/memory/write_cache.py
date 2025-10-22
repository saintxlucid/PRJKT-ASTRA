"""
Memory Write-Through Cache

Implements a write-through caching layer for memory operations to ensure 
consistency between ChromaDB (semantic) and SQLite (episodic/procedural).

Created: October 21, 2025
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, cast, Protocol
from pathlib import Path
import structlog
import chromadb
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from src.astra.telemetry.memory_metrics import MEMORY_METRICS
from .transaction import memory_transaction

logger = structlog.get_logger()

class ChromaClient(Protocol):
    """Protocol for ChromaDB client interface"""
    def get_or_create_collection(self, name: str) -> Any: ...
    def get_collection(self, name: str) -> Any: ...


@dataclass
class WriteOperation:
    """Represents a write operation to be synchronized"""
    memory_type: str  # semantic, episodic, procedural
    operation: str  # insert, update, delete
    data: Dict[str, Any]
    timestamp: float = time.time()


class MemoryWriteCache:
    """
    Write-through cache ensuring consistency across memory stores.
    
    Implements:
    - Atomic writes across stores
    - Write confirmation
    - Operation logging
    - Reconciliation tracking
    """
    
    def __init__(self, database_path: Path, chroma_client: ChromaClient):
        """
        Initialize write cache.
        
        Args:
            database_path: Path to SQLite database
            chroma_client: ChromaDB client for vector store
        """
        self.database_path = database_path
        self.chroma_client = chroma_client
        self.pending_writes: List[WriteOperation] = []
        self.failed_writes: Set[str] = set()
        
    async def write_semantic(self, data: Dict[str, Any], max_retries: int = 3) -> bool:
        """
        Write semantic memory with write-through caching.
        
        Args:
            data: Memory data to write
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if write successful
        """
        start_time = time.time()
        operation = WriteOperation(
            memory_type="semantic",
            operation="insert",
            data=data
        )
        
        for attempt in range(max_retries):
            try:
                async with memory_transaction(self.database_path, self.chroma_client) as tx:
                    # Write to ChromaDB
                    collection = self.chroma_client.get_or_create_collection("semantic")
                    collection.add(
                        documents=[data["text"]],
                        metadatas=[data.get("metadata", {})],
                        ids=[data["id"]]
                    )
                    
                    await tx.add_operation("chroma", {
                        "id": data["id"],
                        "type": "insert"
                    })
                    
                    # Log operation
                    self.pending_writes.append(operation)
                    
                    duration = time.time() - start_time
                    MEMORY_METRICS.observe_store_latency("semantic", duration)
                    return True
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error("Failed to write semantic memory after retries", error=str(e))
                    self.failed_writes.add(data["id"])
                    MEMORY_METRICS.record_reconcile_drift("chroma")
                    return False
                    
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                
        return False  # Should never reach here but needed for type checking
            
    async def write_episodic(self, data: Dict[str, Any]) -> bool:
        """
        Write episodic memory with write-through caching.
        
        Args:
            data: Memory data to write
            
        Returns:
            True if write successful
        """
        start_time = time.time()
        operation = WriteOperation(
            memory_type="episodic",
            operation="insert", 
            data=data
        )
        
        conn = None
        try:
            # Write to SQLite
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO episodic (title, summary, tags, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET
                    summary = excluded.summary,
                    tags = excluded.tags,
                    timestamp = excluded.timestamp
            """, (
                data["title"],
                data["summary"],
                ",".join(data.get("tags", [])),
                datetime.now().timestamp()
            ))
            
            conn.commit()
            
            # Log operation
            self.pending_writes.append(operation)
            
            duration = time.time() - start_time
            MEMORY_METRICS.observe_store_latency("episodic", duration)
            return True
            
        except Exception as e:
            logger.error("Failed to write episodic memory", error=str(e))
            self.failed_writes.add(data["title"])
            MEMORY_METRICS.record_reconcile_drift("sqlite")
            return False
            
        finally:
            if conn:
                conn.close()
                
    async def write_procedural(self, data: Dict[str, Any]) -> bool:
        """
        Write procedural memory with write-through caching.
        
        Args:
            data: Memory data to write
            
        Returns:
            True if write successful
        """
        start_time = time.time()
        operation = WriteOperation(
            memory_type="procedural",
            operation="insert",
            data=data
        )
        
        conn = None
        try:
            # Write to SQLite
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO procedural (name, script, tags, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    script = excluded.script,
                    tags = excluded.tags,
                    timestamp = excluded.timestamp
            """, (
                data["name"],
                data["script"],
                ",".join(data.get("tags", [])),
                datetime.now().timestamp()
            ))
            
            conn.commit()
            
            # Log operation
            self.pending_writes.append(operation)
            
            duration = time.time() - start_time
            MEMORY_METRICS.observe_store_latency("procedural", duration)
            return True
            
        except Exception as e:
            logger.error("Failed to write procedural memory", error=str(e))
            self.failed_writes.add(data["name"])
            MEMORY_METRICS.record_reconcile_drift("sqlite")
            return False
            
        finally:
            if conn:
                conn.close()
                
    def get_failed_writes(self) -> Set[str]:
        """Get IDs of failed write operations"""
        return self.failed_writes.copy()
        
    def clear_failed_writes(self) -> None:
        """Clear the set of failed writes"""
        self.failed_writes.clear()
        
    def get_pending_writes(self) -> List[WriteOperation]:
        """Get list of pending write operations"""
        return self.pending_writes.copy()
        
    def clear_pending_writes(self) -> None:
        """Clear the list of pending writes"""
        self.pending_writes.clear()
        
    async def verify_write(self, operation: WriteOperation) -> bool:
        """
        Verify that a write operation was successful.
        
        Args:
            operation: Write operation to verify
            
        Returns:
            True if write is verified
        """
        if operation.memory_type == "semantic":
            try:
                collection = self.chroma_client.get_collection("semantic")
                result = collection.get(
                    ids=[operation.data["id"]], 
                    include=["metadatas"]
                )
                return len(result["ids"]) > 0
            except Exception as e:
                logger.error("Failed to verify semantic write", error=str(e))
                return False
                
        conn = None
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            if operation.memory_type == "episodic":
                cursor.execute(
                    "SELECT COUNT(*) FROM episodic WHERE title = ?",
                    (operation.data["title"],)
                )
            else:  # procedural
                cursor.execute(
                    "SELECT COUNT(*) FROM procedural WHERE name = ?",
                    (operation.data["name"],)
                )
                
            count = cursor.fetchone()[0]
            return count > 0
            
        except Exception as e:
            logger.error(f"Failed to verify {operation.memory_type} write", error=str(e))
            return False
            
        finally:
            if conn:
                conn.close()
                
    async def verify_all_pending(self) -> bool:
        """
        Verify all pending write operations.
        
        Returns:
            True if all writes are verified
        """
        verified = True
        for op in self.pending_writes:
            if not await self.verify_write(op):
                verified = False
                memory_id = (
                    str(op.data.get("id"))
                    if op.data.get("id") is not None
                    else str(op.data.get("title"))
                    if op.data.get("title") is not None
                    else str(op.data.get("name"))
                )
                self.failed_writes.add(memory_id)
                
        if verified:
            self.clear_pending_writes()
            
        return verified