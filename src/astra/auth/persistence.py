"""
Persistent storage for user memory using SQLite.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional
import structlog
from prometheus_client import Counter, Histogram
import aiosqlite
from pathlib import Path

from .metrics import AsyncTimer

logger = structlog.get_logger(__name__)

# Metrics
PERSISTENCE_ERRORS = Counter(
    "astra_memory_persistence_errors_total",
    "Memory persistence errors by type",
    ["error_type"]
)

PERSISTENCE_LATENCY = Histogram(
    "astra_memory_persistence_latency_seconds", 
    "Memory persistence operation latency",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25)
)

class MemoryStore:
    """SQLite-based persistent storage for user memory."""

    def __init__(self) -> None:
        """Initialize memory store."""
        from .config import config as auth_config
        self.db_path = auth_config.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self) -> None:
        """Initialize the database schema. Must be called before using the store."""
        await self._init_db()

    async def _init_db(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, key)
                )
            """)
            # Index for faster user-based queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_memory_user 
                ON user_memory(user_id)
            """)
            await db.commit()

    async def get(self, user_id: str, key: str) -> Optional[Any]:
        """Get value from persistent storage."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with AsyncTimer(PERSISTENCE_LATENCY, {"operation": "read"}):
                    cursor = await db.execute(
                        """
                        SELECT value FROM user_memory 
                        WHERE user_id = ? AND key = ?
                        """,
                        (user_id, key)
                    )
                    row = await cursor.fetchone()
                    if row:
                        return json.loads(row[0])
                    return None
            except Exception as e:
                PERSISTENCE_ERRORS.labels(error_type="read").inc()
                logger.error("persistence_read_error",
                           user_id=user_id,
                           key=key,
                           error=str(e))
                raise

    async def set(self, user_id: str, key: str, value: Any) -> None:
        """Set value in persistent storage."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with AsyncTimer(PERSISTENCE_LATENCY, {"operation": "write"}):
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO user_memory (user_id, key, value, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (user_id, key, json.dumps(value))
                    )
                    await db.commit()
            except Exception as e:
                PERSISTENCE_ERRORS.labels(error_type="write").inc()
                logger.error("persistence_write_error",
                           user_id=user_id,
                           key=key,
                           error=str(e))
                raise

    async def delete(self, user_id: str, key: str) -> bool:
        """Delete value from persistent storage."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with AsyncTimer(PERSISTENCE_LATENCY, {"operation": "delete"}):
                    cursor = await db.execute(
                        """
                        DELETE FROM user_memory 
                        WHERE user_id = ? AND key = ?
                        """,
                        (user_id, key)
                    )
                    await db.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                PERSISTENCE_ERRORS.labels(error_type="delete").inc()
                logger.error("persistence_delete_error",
                           user_id=user_id,
                           key=key,
                           error=str(e))
                raise

    async def list_keys(self, user_id: str) -> List[str]:
        """List all keys for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with AsyncTimer(PERSISTENCE_LATENCY, {"operation": "list"}):
                    cursor = await db.execute(
                        """
                        SELECT key FROM user_memory 
                        WHERE user_id = ?
                        ORDER BY key
                        """,
                        (user_id,)
                    )
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
            except Exception as e:
                PERSISTENCE_ERRORS.labels(error_type="list").inc()
                logger.error("persistence_list_error",
                           user_id=user_id,
                           error=str(e))
                raise

    async def clear(self, user_id: str) -> None:
        """Clear all memory for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with AsyncTimer(PERSISTENCE_LATENCY, {"operation": "clear"}):
                    await db.execute(
                        "DELETE FROM user_memory WHERE user_id = ?",
                        (user_id,)
                    )
                    await db.commit()
            except Exception as e:
                PERSISTENCE_ERRORS.labels(error_type="clear").inc()
                logger.error("persistence_clear_error",
                           user_id=user_id,
                           error=str(e))
                raise

    async def load_all(self, user_id: str) -> Dict[str, Any]:
        """Load all memory for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with AsyncTimer(PERSISTENCE_LATENCY, {"operation": "load"}):
                    cursor = await db.execute(
                        """
                        SELECT key, value FROM user_memory 
                        WHERE user_id = ?
                        """,
                        (user_id,)
                    )
                    rows = await cursor.fetchall()
                    return {
                        row[0]: json.loads(row[1])
                        for row in rows
                    }
            except Exception as e:
                PERSISTENCE_ERRORS.labels(error_type="load").inc()
                logger.error("persistence_load_error",
                           user_id=user_id,
                           error=str(e))
                raise

# Global store instance
memory_store = MemoryStore()