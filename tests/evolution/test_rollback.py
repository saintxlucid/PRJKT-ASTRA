"""
Tests for evolution rollback functionality.

Covers:
- Snapshot management
- Rollback operations
- Cleanup policies
- Error recovery
"""

import json
import pytest
from pathlib import Path
from astra.evolution.backend.rollback import (
    SnapshotManager,
    RollbackManager,
    RollbackError,
    Snapshot,
    CleanupPolicy
)

class TestSnapshotManagement:
    def test_create_snapshot(self, evolution_workspace, sample_model):
        """Test creating a model snapshot."""
        snapshot_mgr = SnapshotManager(evolution_workspace)
        
        # Create snapshot
        snapshot = snapshot_mgr.create_snapshot(
            model_path=sample_model,
            description="Test snapshot",
            metadata={
                "operation": "test",
                "version": "1.0"
            }
        )
        
        # Verify snapshot was created
        assert snapshot.id is not None
        assert snapshot.manifest_path.exists()
        assert snapshot.model_path.exists()
        
    def test_list_snapshots(self, evolution_workspace, sample_model):
        """Test listing available snapshots."""
        snapshot_mgr = SnapshotManager(evolution_workspace)
        
        # Create multiple snapshots
        for i in range(3):
            snapshot_mgr.create_snapshot(
                model_path=sample_model,
                description=f"Snapshot {i}",
                metadata={"index": i}
            )
            
        # List snapshots
        snapshots = snapshot_mgr.list_snapshots()
        assert len(snapshots) == 3
        
        # Verify order (newest first)
        assert snapshots[0].metadata["index"] == 2
        
    def test_snapshot_verification(self, evolution_workspace, sample_model):
        """Test snapshot integrity verification."""
        snapshot_mgr = SnapshotManager(evolution_workspace)
        
        # Create snapshot
        snapshot = snapshot_mgr.create_snapshot(
            model_path=sample_model,
            description="Test snapshot"
        )
        
        # Verify snapshot
        verification = snapshot_mgr.verify_snapshot(snapshot.id)
        assert verification.valid
        assert verification.model_hash == snapshot.model_hash
        
        # Tamper with snapshot
        with open(snapshot.model_path, "ab") as f:
            f.write(b"TAMPERED")
            
        # Verification should fail
        verification = snapshot_mgr.verify_snapshot(snapshot.id)
        assert not verification.valid

class TestRollbackOperations:
    def test_rollback_to_snapshot(self, evolution_workspace, sample_model):
        """Test rolling back to a specific snapshot."""
        rollback_mgr = RollbackManager(evolution_workspace)
        
        # Create initial snapshot
        snapshot = rollback_mgr.create_snapshot(sample_model)
        original_hash = snapshot.model_hash
        
        # Modify model
        with open(sample_model, "ab") as f:
            f.write(b"MODIFICATION")
            
        # Rollback
        result = rollback_mgr.rollback_to_snapshot(snapshot.id)
        assert result.success
        
        # Verify model was restored
        with open(sample_model, "rb") as f:
            restored_data = f.read()
        assert hash(restored_data) == original_hash
        
    def test_automatic_snapshots(self, evolution_workspace, sample_model):
        """Test automatic snapshot creation during operations."""
        rollback_mgr = RollbackManager(evolution_workspace)
        
        # Enable auto-snapshots
        rollback_mgr.enable_auto_snapshots()
        
        # Simulate operations
        for i in range(3):
            with rollback_mgr.operation_context(f"Operation {i}"):
                # Modify model
                with open(sample_model, "ab") as f:
                    f.write(f"MOD_{i}".encode())
                    
        # Should have created snapshots
        snapshots = rollback_mgr.list_snapshots()
        assert len(snapshots) == 3
        
    def test_rollback_validation(self, evolution_workspace, sample_model):
        """Test rollback validation gates."""
        rollback_mgr = RollbackManager(evolution_workspace)
        
        # Create snapshot
        snapshot = rollback_mgr.create_snapshot(
            sample_model,
            validation_required=True
        )
        
        # Try rollback without validation
        with pytest.raises(RollbackError) as exc:
            rollback_mgr.rollback_to_snapshot(
                snapshot.id,
                skip_validation=False
            )
        assert "Validation required" in str(exc.value)
        
        # Rollback with validation
        result = rollback_mgr.rollback_to_snapshot(
            snapshot.id,
            skip_validation=False,
            validation_fn=lambda model: True  # Mock validation
        )
        assert result.success

class TestCleanupPolicies:
    def test_keep_n_policy(self, evolution_workspace, sample_model):
        """Test keeping N most recent snapshots."""
        snapshot_mgr = SnapshotManager(evolution_workspace)
        
        # Create cleanup policy
        policy = CleanupPolicy.keep_last_n(n=2)
        snapshot_mgr.set_cleanup_policy(policy)
        
        # Create multiple snapshots
        for i in range(5):
            snapshot_mgr.create_snapshot(
                model_path=sample_model,
                description=f"Snapshot {i}"
            )
            
        # Run cleanup
        cleaned = snapshot_mgr.cleanup()
        
        # Should only have 2 snapshots left
        remaining = snapshot_mgr.list_snapshots()
        assert len(remaining) == 2
        assert cleaned == 3
        
    def test_age_based_policy(self, evolution_workspace, sample_model):
        """Test age-based snapshot cleanup."""
        snapshot_mgr = SnapshotManager(evolution_workspace)
        
        # Create cleanup policy
        policy = CleanupPolicy.max_age(days=30)
        snapshot_mgr.set_cleanup_policy(policy)
        
        # Create snapshots with different ages
        timestamps = [
            "2025-09-22T10:00:00Z",  # 30+ days old
            "2025-10-01T10:00:00Z",  # ~21 days old
            "2025-10-15T10:00:00Z",  # ~7 days old
        ]
        
        for ts in timestamps:
            snapshot_mgr.create_snapshot(
                model_path=sample_model,
                timestamp=ts
            )
            
        # Run cleanup
        cleaned = snapshot_mgr.cleanup()
        
        # Should have removed old snapshots
        remaining = snapshot_mgr.list_snapshots()
        assert len(remaining) == 2  # Only recent ones remain
        assert cleaned == 1