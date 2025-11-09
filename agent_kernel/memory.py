# agent_kernel/memory.py
"""
Memory tier abstraction for ASTRA OS agent kernel.
Implements L0-L3 storage tiers with different retention policies.
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class MemoryTier:
    """Base class for memory tiers."""

    def __init__(self, name: str):
        self.name = name

    def write(self, key: str, value: Any, ttl_s: int | None = None) -> bool:
        """Write value to memory."""
        raise NotImplementedError

    def read(self, key: str) -> Any | None:
        """Read value from memory."""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Delete value from memory."""
        raise NotImplementedError

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix filter."""
        raise NotImplementedError

    def clear(self) -> None:
        """Clear all entries in this tier."""
        raise NotImplementedError


class L0PermanentMemory(MemoryTier):
    """
    L0: Permanent SQLite storage.
    Persists across sessions, never auto-expires.
    """

    def __init__(self, db_path: str = "data/memory_l0.db"):
        super().__init__("L0_Permanent")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def write(self, key: str, value: Any, ttl_s: int | None = None) -> bool:
        """Write to permanent storage (TTL ignored)."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            value_json = json.dumps(value)
            now = time.time()

            cursor.execute("""
                INSERT INTO memory (key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, value_json, now, now))

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def read(self, key: str) -> Any | None:
        """Read from permanent storage."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM memory WHERE key = ?", (key,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return json.loads(row[0])
            return None
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        """Delete from permanent storage."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory WHERE key = ?", (key,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception:
            return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            if prefix:
                cursor.execute(
                    "SELECT key FROM memory WHERE key LIKE ?",
                    (f"{prefix}%",)
                )
            else:
                cursor.execute("SELECT key FROM memory")

            keys = [row[0] for row in cursor.fetchall()]
            conn.close()
            return keys
        except Exception:
            return []

    def clear(self) -> None:
        """Clear all permanent storage (use with caution!)."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory")
            conn.commit()
            conn.close()
        except Exception:
            pass


class L1SessionMemory(MemoryTier):
    """
    L1: Session memory.
    Cleared on agent restart, no TTL enforcement.
    """

    def __init__(self):
        super().__init__("L1_Session")
        self.store: dict[str, Any] = {}

    def write(self, key: str, value: Any, ttl_s: int | None = None) -> bool:
        """Write to session memory (TTL ignored)."""
        self.store[key] = value
        return True

    def read(self, key: str) -> Any | None:
        """Read from session memory."""
        return self.store.get(key)

    def delete(self, key: str) -> bool:
        """Delete from session memory."""
        if key in self.store:
            del self.store[key]
            return True
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix."""
        if prefix:
            return [k for k in self.store.keys() if k.startswith(prefix)]
        return list(self.store.keys())

    def clear(self) -> None:
        """Clear session memory."""
        self.store.clear()


class L2LoopMemory(MemoryTier):
    """
    L2: Loop artifacts.
    Cleared after task completion, short TTL.
    """

    def __init__(self, default_ttl_s: int = 3600):
        super().__init__("L2_Loop")
        self.store: dict[str, tuple[Any, float]] = {}  # key -> (value, expire_time)
        self.default_ttl_s = default_ttl_s

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self.store.items() if exp < now]
        for key in expired_keys:
            del self.store[key]

    def write(self, key: str, value: Any, ttl_s: int | None = None) -> bool:
        """Write to loop memory with TTL."""
        self._cleanup_expired()
        ttl = ttl_s if ttl_s is not None else self.default_ttl_s
        expire_time = time.time() + ttl
        self.store[key] = (value, expire_time)
        return True

    def read(self, key: str) -> Any | None:
        """Read from loop memory (respects TTL)."""
        self._cleanup_expired()
        if key in self.store:
            value, _ = self.store[key]
            return value
        return None

    def delete(self, key: str) -> bool:
        """Delete from loop memory."""
        if key in self.store:
            del self.store[key]
            return True
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all non-expired keys with optional prefix."""
        self._cleanup_expired()
        if prefix:
            return [k for k in self.store.keys() if k.startswith(prefix)]
        return list(self.store.keys())

    def clear(self) -> None:
        """Clear loop memory."""
        self.store.clear()


class L3EphemeralMemory(MemoryTier):
    """
    L3: Ephemeral memory.
    Cleared after each iteration, very short TTL.
    """

    def __init__(self, default_ttl_s: int = 60):
        super().__init__("L3_Ephemeral")
        self.store: dict[str, tuple[Any, float]] = {}
        self.default_ttl_s = default_ttl_s

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self.store.items() if exp < now]
        for key in expired_keys:
            del self.store[key]

    def write(self, key: str, value: Any, ttl_s: int | None = None) -> bool:
        """Write to ephemeral memory with short TTL."""
        self._cleanup_expired()
        ttl = ttl_s if ttl_s is not None else self.default_ttl_s
        expire_time = time.time() + ttl
        self.store[key] = (value, expire_time)
        return True

    def read(self, key: str) -> Any | None:
        """Read from ephemeral memory (respects TTL)."""
        self._cleanup_expired()
        if key in self.store:
            value, _ = self.store[key]
            return value
        return None

    def delete(self, key: str) -> bool:
        """Delete from ephemeral memory."""
        if key in self.store:
            del self.store[key]
            return True
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all non-expired keys with optional prefix."""
        self._cleanup_expired()
        if prefix:
            return [k for k in self.store.keys() if k.startswith(prefix)]
        return list(self.store.keys())

    def clear(self) -> None:
        """Clear ephemeral memory."""
        self.store.clear()


class MemoryManager:
    """
    Unified memory manager coordinating all tiers.
    Provides simple interface for agent kernel.
    """

    def __init__(
        self,
        l0_path: str = "data/memory_l0.db",
        l2_ttl_s: int = 3600,
        l3_ttl_s: int = 60,
    ):
        """
        Initialize memory manager with all tiers.

        Args:
            l0_path: Path to L0 SQLite database
            l2_ttl_s: Default TTL for L2 loop memory
            l3_ttl_s: Default TTL for L3 ephemeral memory
        """
        self.l0 = L0PermanentMemory(l0_path)
        self.l1 = L1SessionMemory()
        self.l2 = L2LoopMemory(l2_ttl_s)
        self.l3 = L3EphemeralMemory(l3_ttl_s)

        self.tiers = {
            "L0": self.l0,
            "L1": self.l1,
            "L2": self.l2,
            "L3": self.l3,
        }

    def write(
        self,
        key: str,
        value: Any,
        tier: str = "L1",
        ttl_s: int | None = None,
    ) -> bool:
        """
        Write to specified memory tier.

        Args:
            key: Memory key
            value: Value to store
            tier: Target tier (L0/L1/L2/L3)
            ttl_s: Optional TTL (ignored for L0/L1)

        Returns:
            True if write succeeded
        """
        if tier not in self.tiers:
            return False

        return self.tiers[tier].write(key, value, ttl_s)

    def read(self, key: str, tier: str = "L1") -> Any | None:
        """
        Read from specified memory tier.

        Args:
            key: Memory key
            tier: Target tier (L0/L1/L2/L3)

        Returns:
            Value or None if not found
        """
        if tier not in self.tiers:
            return None

        return self.tiers[tier].read(key)

    def read_cascade(self, key: str) -> tuple[Any | None, str | None]:
        """
        Read from tiers in cascade (L3 → L2 → L1 → L0).
        Returns first found value and tier name.

        Args:
            key: Memory key

        Returns:
            (value, tier_name) or (None, None) if not found
        """
        for tier_name in ["L3", "L2", "L1", "L0"]:
            value = self.read(key, tier_name)
            if value is not None:
                return value, tier_name

        return None, None

    def delete(self, key: str, tier: str = "L1") -> bool:
        """Delete from specified tier."""
        if tier not in self.tiers:
            return False

        return self.tiers[tier].delete(key)

    def clear_tier(self, tier: str) -> None:
        """Clear all entries in specified tier."""
        if tier in self.tiers:
            self.tiers[tier].clear()

    def clear_session(self) -> None:
        """Clear session-scoped tiers (L1, L2, L3)."""
        self.l1.clear()
        self.l2.clear()
        self.l3.clear()

    def get_stats(self) -> dict[str, int]:
        """Get key counts for all tiers."""
        return {
            tier_name: len(tier.list_keys())
            for tier_name, tier in self.tiers.items()
        }
