"""Tests for snapshot and recovery functionality."""

import pytest
import tempfile
import json
import os
from pathlib import Path
import shutil
from typing import Dict, Any, Optional
import threading
import time
from unittest.mock import Mock, patch

from evolution.core.snapshot import (
    SnapshotConfig,
    SnapshotManager,
    SnapshotError,
    Manifest,
    validate_snapshot_config
)

@pytest.fixture
def test_data() -> bytes:
    """Create sample test data."""
    return b"Test model data for snapshots"

@pytest.fixture
def snapshot_dir(tmp_path) -> Path:
    """Create a temporary snapshot directory."""
    path = tmp_path / "snapshots"
    path.mkdir()
    return path

@pytest.fixture
def manager(snapshot_dir) -> SnapshotManager:
    """Create a SnapshotManager instance."""
    return SnapshotManager(
        config=SnapshotConfig(
            path=snapshot_dir,
            max_snapshots=5,
            retention_days=7
        )
    )

class TestSnapshotCreation:
    """Test snapshot creation functionality."""
    
    def test_basic_snapshot(self, manager, test_data):
        """Test basic snapshot creation."""
        snapshot_id = manager.create_snapshot(test_data)
        
        assert snapshot_id is not None
        assert manager.get_snapshot_path(snapshot_id).exists()
        
    def test_with_metadata(self, manager, test_data):
        """Test snapshot creation with metadata."""
        metadata = {
            "operation": "quantize",
            "format": "Q4_K_M",
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        snapshot_id = manager.create_snapshot(
            test_data,
            metadata=metadata
        )
        
        loaded_metadata = manager.get_snapshot_metadata(snapshot_id)
        assert loaded_metadata == metadata
        
    def test_concurrent_creation(self, manager, test_data):
        """Test concurrent snapshot creation."""
        def create_snapshot():
            return manager.create_snapshot(test_data)
            
        threads = [
            threading.Thread(target=create_snapshot)
            for _ in range(5)
        ]
        
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # All snapshots should exist
        assert len(list(manager.list_snapshots())) == 5
        
    @pytest.mark.parametrize("size_mb", [1, 10, 100])
    def test_large_snapshots(self, manager, size_mb):
        """Test creation of large snapshots."""
        large_data = b"x" * (size_mb * 1024 * 1024)
        snapshot_id = manager.create_snapshot(large_data)
        
        snapshot_path = manager.get_snapshot_path(snapshot_id)
        assert snapshot_path.exists()
        assert snapshot_path.stat().st_size == len(large_data)

class TestSnapshotRetrieval:
    """Test snapshot retrieval functionality."""
    
    def test_get_snapshot(self, manager, test_data):
        """Test retrieving snapshot data."""
        snapshot_id = manager.create_snapshot(test_data)
        retrieved = manager.get_snapshot(snapshot_id)
        
        assert retrieved == test_data
        
    def test_list_snapshots(self, manager, test_data):
        """Test listing snapshots."""
        ids = [
            manager.create_snapshot(test_data)
            for _ in range(3)
        ]
        
        snapshots = list(manager.list_snapshots())
        assert len(snapshots) == 3
        assert all(s["id"] in ids for s in snapshots)
        
    def test_get_nonexistent(self, manager):
        """Test retrieving nonexistent snapshot."""
        with pytest.raises(SnapshotError):
            manager.get_snapshot("nonexistent")
            
    def test_metadata_retrieval(self, manager, test_data):
        """Test metadata retrieval."""
        metadata = {"operation": "test"}
        snapshot_id = manager.create_snapshot(test_data, metadata)
        
        retrieved = manager.get_snapshot_metadata(snapshot_id)
        assert retrieved == metadata

class TestSnapshotCleanup:
    """Test snapshot cleanup functionality."""
    
    def test_max_snapshots(self, manager, test_data):
        """Test enforcing maximum snapshots."""
        # Create more than max_snapshots
        for _ in range(10):
            manager.create_snapshot(test_data)
            
        snapshots = list(manager.list_snapshots())
        assert len(snapshots) <= manager.config.max_snapshots
        
    def test_retention_cleanup(self, manager, test_data):
        """Test cleanup based on retention period."""
        # Create old snapshots
        with patch("time.time") as mock_time:
            mock_time.return_value = time.time() - (8 * 24 * 3600)  # 8 days ago
            old_id = manager.create_snapshot(test_data)
            
            mock_time.return_value = time.time()  # Now
            new_id = manager.create_snapshot(test_data)
            
            manager.cleanup_old_snapshots()
            
            # Old snapshot should be gone
            assert not manager.get_snapshot_path(old_id).exists()
            assert manager.get_snapshot_path(new_id).exists()
            
    def test_manual_cleanup(self, manager, test_data):
        """Test manual snapshot cleanup."""
        snapshot_id = manager.create_snapshot(test_data)
        manager.delete_snapshot(snapshot_id)
        
        with pytest.raises(SnapshotError):
            manager.get_snapshot(snapshot_id)

class TestManifestHandling:
    """Test manifest handling functionality."""
    
    def test_manifest_creation(self, manager, test_data):
        """Test manifest creation and updating."""
        snapshot_id = manager.create_snapshot(test_data)
        manifest = manager.get_manifest()
        
        assert snapshot_id in manifest.snapshots
        assert manifest.snapshots[snapshot_id]["size"] == len(test_data)
        
    def test_manifest_persistence(self, manager, test_data):
        """Test manifest persistence across restarts."""
        snapshot_id = manager.create_snapshot(test_data)
        
        # Create new manager instance
        new_manager = SnapshotManager(
            config=SnapshotConfig(
                path=manager.config.path,
                max_snapshots=5,
                retention_days=7
            )
        )
        
        manifest = new_manager.get_manifest()
        assert snapshot_id in manifest.snapshots
        
    def test_manifest_corruption(self, manager):
        """Test handling of manifest corruption."""
        manifest_path = manager.config.path / "manifest.json"
        
        # Corrupt manifest file
        with open(manifest_path, "w") as f:
            f.write("invalid json")
            
        # Should create new manifest
        manifest = manager.get_manifest()
        assert isinstance(manifest, Manifest)
        assert manifest.snapshots == {}

class TestAtomicOperations:
    """Test atomic operation guarantees."""
    
    def test_failed_creation(self, manager, test_data):
        """Test handling of failed snapshot creation."""
        class FailingWriter:
            def write(self, _):
                raise IOError("Write failed")
                
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value = FailingWriter()
            
            with pytest.raises(SnapshotError):
                manager.create_snapshot(test_data)
                
            # No partial snapshots should exist
            assert len(list(manager.list_snapshots())) == 0
            
    def test_concurrent_manifest(self, manager, test_data):
        """Test concurrent manifest operations."""
        def create_and_delete():
            """Create and immediately delete a snapshot."""
            snapshot_id = manager.create_snapshot(test_data)
            manager.delete_snapshot(snapshot_id)
            
        threads = [
            threading.Thread(target=create_and_delete)
            for _ in range(5)
        ]
        
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # Manifest should be consistent
        manifest = manager.get_manifest()
        assert len(manifest.snapshots) == 0

class TestErrorHandling:
    """Test error handling in snapshot operations."""
    
    def test_invalid_config(self):
        """Test validation of invalid config."""
        with pytest.raises(SnapshotError):
            SnapshotManager(
                config=SnapshotConfig(
                    path=Path("nonexistent"),
                    max_snapshots=-1,  # Invalid
                    retention_days=7
                )
            )
            
    def test_disk_full(self, manager, test_data):
        """Test handling of disk full condition."""
        def mock_write_fail(*args, **kwargs):
            raise OSError(28, "No space left on device")
            
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.write = mock_write_fail
            
            with pytest.raises(SnapshotError, match="disk space"):
                manager.create_snapshot(test_data)
                
    def test_permission_error(self, manager, test_data):
        """Test handling of permission errors."""
        # Make snapshot directory read-only
        os.chmod(manager.config.path, 0o444)
        
        with pytest.raises(SnapshotError, match="permission"):
            manager.create_snapshot(test_data)
            
        # Restore permissions
        os.chmod(manager.config.path, 0o777)

class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.benchmark
    def test_creation_speed(self, manager, benchmark):
        """Benchmark snapshot creation speed."""
        data = b"x" * (1024 * 1024)  # 1MB
        
        def create():
            return manager.create_snapshot(data)
            
        result = benchmark(create)
        assert result.stats.mean < 0.1  # Should take less than 0.1 seconds
        
    def test_memory_usage(self, manager):
        """Test memory usage during snapshot operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large snapshot
        data = b"x" * (50 * 1024 * 1024)  # 50MB
        manager.create_snapshot(data)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Should use reasonable memory
        assert memory_increase < 100  # Less than 100MB increase