"""Tests for nightly refinement integration."""
from __future__ import annotations

import json
from pathlib import Path

from chat_os.services.nightly_tasks import run_nightly_refinement, save_telemetry_snapshot
from chat_os.telemetry import TelemetrySnapshot


def test_save_telemetry_snapshot(tmp_path: Path):
    """Test that telemetry snapshots are saved to JSON."""
    telemetry_dir = tmp_path / "telemetry"
    
    snapshot = TelemetrySnapshot(
        total_tasks=10,
        mode_distribution={"SYMBOLIC": 6, "STATISTICAL": 4},
        p95_latency_ms=150.5,
        rollback_count=1,
        macro_success_rate=0.75,
        emotional_states={"focused": 8, "stressed": 2},
        metadata={"session_id": "test_123"},
    )
    
    save_telemetry_snapshot(snapshot, telemetry_dir)
    
    # Verify file created
    snapshots_file = telemetry_dir / "snapshots.json"
    assert snapshots_file.exists()
    
    # Verify content
    with open(snapshots_file) as f:
        data = json.load(f)
    
    assert "snapshots" in data
    assert len(data["snapshots"]) == 1
    assert data["snapshots"][0]["total_tasks"] == 10
    assert data["snapshots"][0]["p95_latency_ms"] == 150.5


def test_save_multiple_telemetry_snapshots(tmp_path: Path):
    """Test that multiple snapshots accumulate correctly."""
    telemetry_dir = tmp_path / "telemetry"
    
    snapshot1 = TelemetrySnapshot(
        total_tasks=5,
        mode_distribution={"SYMBOLIC": 3, "STATISTICAL": 2},
        p95_latency_ms=100.0,
        rollback_count=0,
        macro_success_rate=0.8,
        emotional_states={},
    )
    
    snapshot2 = TelemetrySnapshot(
        total_tasks=8,
        mode_distribution={"SYMBOLIC": 4, "STATISTICAL": 4},
        p95_latency_ms=120.0,
        rollback_count=1,
        macro_success_rate=0.85,
        emotional_states={},
    )
    
    save_telemetry_snapshot(snapshot1, telemetry_dir)
    save_telemetry_snapshot(snapshot2, telemetry_dir)
    
    # Verify both saved
    snapshots_file = telemetry_dir / "snapshots.json"
    with open(snapshots_file) as f:
        data = json.load(f)
    
    assert len(data["snapshots"]) == 2
    assert data["snapshots"][0]["total_tasks"] == 5
    assert data["snapshots"][1]["total_tasks"] == 8


def test_run_nightly_refinement_no_data(tmp_path: Path):
    """Test refinement handles missing telemetry data gracefully."""
    telemetry_dir = tmp_path / "telemetry"
    refinement_dir = tmp_path / "refinement"
    
    result = run_nightly_refinement(telemetry_dir, refinement_dir)
    
    assert result["status"] == "no_telemetry"
    assert "message" in result


def test_run_nightly_refinement_with_data(tmp_path: Path):
    """Test refinement analysis with real telemetry data."""
    telemetry_dir = tmp_path / "telemetry"
    refinement_dir = tmp_path / "refinement"
    
    # Create telemetry snapshots
    for i in range(5):
        snapshot = TelemetrySnapshot(
            total_tasks=10 + i,
            mode_distribution={"SYMBOLIC": 5 + i, "STATISTICAL": 5},
            p95_latency_ms=150.0 + i * 10,
            rollback_count=i % 2,
            macro_success_rate=0.7 + i * 0.05,
            emotional_states={"focused": 8, "stressed": 2},
        )
        save_telemetry_snapshot(snapshot, telemetry_dir)
    
    # Run refinement
    result = run_nightly_refinement(telemetry_dir, refinement_dir)
    
    assert result["status"] == "success"
    assert "timestamp" in result
    assert result["snapshots_analyzed"] == 5
    assert "metrics_summary" in result
    assert "policy_changes" in result


def test_refinement_report_saved_to_file(tmp_path: Path):
    """Test that refinement reports are saved as JSON files."""
    telemetry_dir = tmp_path / "telemetry"
    refinement_dir = tmp_path / "refinement"

    # Create sample telemetry
    snapshot = TelemetrySnapshot(
        total_tasks=20,
        mode_distribution={"SYMBOLIC": 12, "STATISTICAL": 8},
        p95_latency_ms=200.0,
        rollback_count=2,
        macro_success_rate=0.9,
        emotional_states={"focused": 18, "stressed": 2},
    )
    save_telemetry_snapshot(snapshot, telemetry_dir)

    # Run refinement
    run_nightly_refinement(telemetry_dir, refinement_dir)

    # Verify report file created
    report_files = list(refinement_dir.glob("refinement_report_*.json"))
    assert len(report_files) == 1

    # Verify report content
    with open(report_files[0]) as f:
        report_data = json.load(f)

    assert report_data["status"] == "success"
    assert "metrics_summary" in report_data
    assert "policy_changes" in report_data


def test_refinement_policy_change_structure(tmp_path: Path):
    """Test that policy changes have correct structure."""
    telemetry_dir = tmp_path / "telemetry"
    refinement_dir = tmp_path / "refinement"
    
    # Create telemetry with conditions that trigger policy changes
    # High macro success rate should trigger prefer_procedural change
    for _ in range(3):
        snapshot = TelemetrySnapshot(
            total_tasks=50,
            mode_distribution={"PROCEDURAL": 40, "STATISTICAL": 10},
            p95_latency_ms=100.0,
            rollback_count=0,
            macro_success_rate=0.95,  # Above threshold
            emotional_states={},
        )
        save_telemetry_snapshot(snapshot, telemetry_dir)
    
    result = run_nightly_refinement(telemetry_dir, refinement_dir)
    
    # Check if policy changes were proposed
    if len(result["policy_changes"]) > 0:
        change = result["policy_changes"][0]
        assert "category" in change
        assert "parameter" in change
        assert "old_value" in change
        assert "new_value" in change
        assert "reason" in change
        assert "impact" in change


def test_refinement_metrics_summary(tmp_path: Path):
    """Test that metrics summary is computed correctly."""
    telemetry_dir = tmp_path / "telemetry"
    refinement_dir = tmp_path / "refinement"

    # Create diverse telemetry
    snapshots_count = 7
    for _ in range(snapshots_count):
        snapshot = TelemetrySnapshot(
            total_tasks=10,
            mode_distribution={"SYMBOLIC": 6, "STATISTICAL": 4},
            p95_latency_ms=150.0,
            rollback_count=0,
            macro_success_rate=0.8,
            emotional_states={},
        )
        save_telemetry_snapshot(snapshot, telemetry_dir)

    result = run_nightly_refinement(telemetry_dir, refinement_dir, analysis_window_days=7)

    # Verify metrics summary
    summary = result["metrics_summary"]
    assert "total_tasks" in summary
    assert "avg_p95_latency_ms" in summary
    assert "mode_distribution" in summary
    assert "sessions_analyzed" in summary
    assert summary["sessions_analyzed"] == snapshots_count
