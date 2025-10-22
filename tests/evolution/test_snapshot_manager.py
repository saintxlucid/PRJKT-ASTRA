"""
Tests for snapshot and recovery functionality.
"""

import pytest
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from astra.evolution.backend.snapshot_manager import (
    SnapshotManager,
    SnapshotManifest,
    SnapshotConfig,
)

@pytest.fixture
def model_path(tmp_path):
    """Create a test model file."""
    model_file = tmp_path / "test_model.gguf"
    model_file.write_bytes(b"test model data")
    return model_file

@pytest.fixture
def snapshot_dir(tmp_path):
    """Create snapshot directory."""
    snapshot_path = tmp_path / "snapshots"
    snapshot_path.mkdir()
    return snapshot_path

@pytest.fixture
def manager(model_path, snapshot_dir):
    """Create SnapshotManager instance."""
    return SnapshotManager(model_path, snapshot_dir)

class TestSnapshotManager:
    def test_create_snapshot(self, manager):
        """Test snapshot creation."""
        config = SnapshotConfig(
            description="Test snapshot",
            metadata={"operation": "test"}
        )
        result = manager.create_snapshot(config)
        assert result.success
        assert result.manifest
        assert result.snapshot_path.exists()
        assert result.manifest.timestamp

    def test_restore_snapshot(self, manager):
        """Test snapshot restoration."""
        # Create snapshot first
        snap = manager.create_snapshot(SnapshotConfig())
        
        # Modify original file
        with open(manager.model_path, "wb") as f:
            f.write(b"modified data")
            
        # Restore snapshot
        result = manager.restore_snapshot(snap.manifest.id)
        assert result.success
        
        # Verify restoration
        with open(manager.model_path, "rb") as f:
            assert f.read() == b"test model data"

    def test_list_snapshots(self, manager):
        """Test snapshot listing."""
        # Create multiple snapshots
        for i in range(3):
            manager.create_snapshot(SnapshotConfig(
                description=f"Snapshot {i}"
            ))
            
        snapshots = manager.list_snapshots()
        assert len(snapshots) == 3
        assert all(isinstance(s, SnapshotManifest) for s in snapshots)
        assert all(s.description for s in snapshots)

    def test_cleanup_old_snapshots(self, manager):
        """Test old snapshot cleanup."""
        # Create snapshots with different ages
        for i in range(3):
            snap = manager.create_snapshot(SnapshotConfig())
            # Modify timestamp to simulate age
            manifest_path = snap.manifest_path
            manifest = json.loads(manifest_path.read_text())
            manifest["timestamp"] = (
                datetime.now(timezone.utc)
                .replace(day=datetime.now().day - i)
                .isoformat()
            )
            manifest_path.write_text(json.dumps(manifest))
            
        manager.cleanup_old_snapshots(max_age_days=2)
        remaining = manager.list_snapshots()
        assert len(remaining) == 2

    def test_manifest_validation(self, manager):
        """Test manifest validation."""
        snap = manager.create_snapshot(SnapshotConfig())
        
        # Corrupt manifest
        manifest_path = snap.manifest_path
        manifest = json.loads(manifest_path.read_text())
        del manifest["timestamp"]
        manifest_path.write_text(json.dumps(manifest))
        
        with pytest.raises(ValueError, match="Invalid manifest"):
            manager.restore_snapshot(snap.manifest.id)

    def test_atomic_operations(self, manager):
        """Test operation atomicity."""
        original_data = b"test model data"
        
        # Create snapshot with intentional failure
        try:
            with manager._atomic_operation():
                manager.create_snapshot(SnapshotConfig())
                raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass
            
        # Verify no partial changes
        with open(manager.model_path, "rb") as f:
            assert f.read() == original_data
        
        # Verify no partial manifests
        assert len(list(manager.snapshot_dir.glob("*.manifest"))) == 0

    def test_concurrent_access(self, manager):
        """Test concurrent access handling."""
        import threading
        
        # Simulate concurrent snapshots
        def create_snapshot():
            try:
                manager.create_snapshot(SnapshotConfig())
            except Exception as e:
                print(f"Thread error: {e}")
                
        threads = [
            threading.Thread(target=create_snapshot)
            for _ in range(3)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # Verify all snapshots were created
        assert len(manager.list_snapshots()) == 3