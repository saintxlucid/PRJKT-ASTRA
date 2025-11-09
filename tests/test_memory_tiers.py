# tests/test_memory_tiers.py
"""
Tests for agent_kernel.memory module.
Validates L0-L3 memory tiers and MemoryManager.
"""
import tempfile
import time
from pathlib import Path

import pytest

from agent_kernel.memory import (
    L0PermanentMemory,
    L1SessionMemory,
    L2LoopMemory,
    L3EphemeralMemory,
    MemoryManager,
)


class TestL0PermanentMemory:
    """Tests for L0 (SQLite) permanent memory."""

    def test_write_read(self):
        """Test basic write and read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_l0.db"
            mem = L0PermanentMemory(str(db_path))

            # Write
            mem.write("user.name", "Alice")
            mem.write("user.age", 30)

            # Read
            assert mem.read("user.name") == "Alice"
            assert mem.read("user.age") == 30
            assert mem.read("nonexistent") is None

    def test_persistence(self):
        """Test that data persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_l0.db"

            # Write in first instance
            mem1 = L0PermanentMemory(str(db_path))
            mem1.write("persistent.key", "persistent_value")

            # Read in second instance
            mem2 = L0PermanentMemory(str(db_path))
            assert mem2.read("persistent.key") == "persistent_value"

    def test_upsert(self):
        """Test that writing same key updates value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_l0.db"
            mem = L0PermanentMemory(str(db_path))

            mem.write("key", "value1")
            assert mem.read("key") == "value1"

            mem.write("key", "value2")
            assert mem.read("key") == "value2"

    def test_delete(self):
        """Test deleting keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_l0.db"
            mem = L0PermanentMemory(str(db_path))

            mem.write("key", "value")
            assert mem.read("key") == "value"

            mem.delete("key")
            assert mem.read("key") is None

    def test_list_keys(self):
        """Test listing all keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_l0.db"
            mem = L0PermanentMemory(str(db_path))

            mem.write("key1", "value1")
            mem.write("key2", "value2")
            mem.write("key3", "value3")

            keys = mem.list_keys()
            assert set(keys) == {"key1", "key2", "key3"}

    def test_clear(self):
        """Test clearing all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_l0.db"
            mem = L0PermanentMemory(str(db_path))

            mem.write("key1", "value1")
            mem.write("key2", "value2")
            assert len(mem.list_keys()) == 2

            mem.clear()
            assert len(mem.list_keys()) == 0


class TestL1SessionMemory:
    """Tests for L1 (dict) session memory."""

    def test_write_read(self):
        """Test basic write and read."""
        mem = L1SessionMemory()

        mem.write("session.id", "12345")
        mem.write("session.user", "Bob")

        assert mem.read("session.id") == "12345"
        assert mem.read("session.user") == "Bob"
        assert mem.read("nonexistent") is None

    def test_no_persistence(self):
        """Test that data doesn't persist across instances."""
        mem1 = L1SessionMemory()
        mem1.write("key", "value")

        mem2 = L1SessionMemory()
        assert mem2.read("key") is None

    def test_delete_and_clear(self):
        """Test delete and clear operations."""
        mem = L1SessionMemory()

        mem.write("key1", "value1")
        mem.write("key2", "value2")

        mem.delete("key1")
        assert mem.read("key1") is None
        assert mem.read("key2") == "value2"

        mem.clear()
        assert len(mem.list_keys()) == 0


class TestL2LoopMemory:
    """Tests for L2 (TTL dict) loop memory."""

    def test_write_read(self):
        """Test basic write and read."""
        mem = L2LoopMemory(default_ttl_s=10)

        mem.write("loop.var", "temp_value")
        assert mem.read("loop.var") == "temp_value"

    def test_ttl_expiry(self):
        """Test that values expire after TTL."""
        mem = L2LoopMemory(default_ttl_s=1)  # 1 second TTL

        mem.write("key", "value")
        assert mem.read("key") == "value"

        # Wait for expiry
        time.sleep(1.1)

        # Should be None after expiry
        assert mem.read("key") is None

    def test_custom_ttl(self):
        """Test custom TTL per write."""
        mem = L2LoopMemory(default_ttl_s=10)

        mem.write("short", "value", ttl_s=1)
        mem.write("long", "value", ttl_s=5)

        # Short should expire first
        time.sleep(1.1)
        assert mem.read("short") is None
        assert mem.read("long") == "value"

    def test_cleanup_on_access(self):
        """Test that expired entries are cleaned up."""
        mem = L2LoopMemory(default_ttl_s=1)

        mem.write("key1", "value1")
        mem.write("key2", "value2")

        time.sleep(1.1)

        # Access should trigger cleanup
        mem.read("key1")

        # list_keys should only show non-expired keys
        assert len(mem.list_keys()) == 0


class TestL3EphemeralMemory:
    """Tests for L3 (short TTL dict) ephemeral memory."""

    def test_short_ttl(self):
        """Test that ephemeral memory has short TTL."""
        mem = L3EphemeralMemory(default_ttl_s=1)

        mem.write("temp", "value")
        assert mem.read("temp") == "value"

        time.sleep(1.1)
        assert mem.read("temp") is None


class TestMemoryManager:
    """Tests for unified MemoryManager."""

    def test_write_read_tiers(self):
        """Test writing and reading from different tiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_manager.db"
            mgr = MemoryManager(l0_path=str(db_path))

            # Write to different tiers
            mgr.write("perm.key", "perm_value", tier="L0")
            mgr.write("sess.key", "sess_value", tier="L1")
            mgr.write("loop.key", "loop_value", tier="L2")
            mgr.write("temp.key", "temp_value", tier="L3")

            # Read from specific tiers
            assert mgr.read("perm.key", tier="L0") == "perm_value"
            assert mgr.read("sess.key", tier="L1") == "sess_value"
            assert mgr.read("loop.key", tier="L2") == "loop_value"
            assert mgr.read("temp.key", tier="L3") == "temp_value"

    def test_cascade_read(self):
        """Test cascade read (L3 -> L2 -> L1 -> L0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_manager.db"
            mgr = MemoryManager(l0_path=str(db_path))

            # Write to L0 only
            mgr.write("key", "l0_value", tier="L0")
            value, tier = mgr.read_cascade("key")
            assert value == "l0_value"
            assert tier == "L0"

            # Write to L2 (should shadow L0)
            mgr.write("key", "l2_value", tier="L2")
            value, tier = mgr.read_cascade("key")
            assert value == "l2_value"
            assert tier == "L2"

            # Write to L3 (should shadow L2 and L0)
            mgr.write("key", "l3_value", tier="L3")
            value, tier = mgr.read_cascade("key")
            assert value == "l3_value"
            assert tier == "L3"

    def test_clear_tier(self):
        """Test clearing individual tiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_manager.db"
            mgr = MemoryManager(l0_path=str(db_path))

            mgr.write("key", "value", tier="L1")
            mgr.write("key", "value", tier="L2")

            mgr.clear_tier("L2")

            assert mgr.read("key", tier="L1") == "value"
            assert mgr.read("key", tier="L2") is None

    def test_stats(self):
        """Test memory statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_manager.db"
            mgr = MemoryManager(l0_path=str(db_path))

            mgr.write("l0.key", "value", tier="L0")
            mgr.write("l1.key1", "value", tier="L1")
            mgr.write("l1.key2", "value", tier="L1")
            mgr.write("l2.key", "value", tier="L2")

            stats = mgr.get_stats()

            assert stats["L0"] == 1
            assert stats["L1"] == 2
            assert stats["L2"] == 1
            assert stats["L3"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
