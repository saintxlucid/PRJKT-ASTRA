from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astra_core.refinement import (  # noqa: E402
    RefinementEngine,
    TelemetrySnapshot,
    format_report,
)


def test_budget_increase_on_high_rollbacks() -> None:
    """Verify budget adjustments when rollbacks are frequent."""
    engine = RefinementEngine()

    for _ in range(5):
        engine.ingest_telemetry(
            TelemetrySnapshot(
                total_tasks=10,
                mode_distribution={"STATISTICAL": 8, "SYMBOLIC": 2},
                p95_latency_ms=800.0,
                token_denials=0,
                rollback_count=3,
                macro_success_rate=0.7,
                emotional_states={"focused": 5, "stressed": 5},
            )
        )

    report = engine.analyze()
    budget_changes = [c for c in report.changes if c.category == "budget"]

    assert len(budget_changes) >= 1
    assert budget_changes[0].new_value > budget_changes[0].old_value


def test_macro_preference_on_high_success() -> None:
    """Verify procedural routing preference when macros succeed."""
    engine = RefinementEngine()

    for _ in range(5):
        engine.ingest_telemetry(
            TelemetrySnapshot(
                total_tasks=10,
                mode_distribution={"PROCEDURAL": 7, "STATISTICAL": 3},
                p95_latency_ms=500.0,
                token_denials=0,
                rollback_count=0,
                macro_success_rate=0.92,
                emotional_states={"focused": 10},
            )
        )

    report = engine.analyze()
    routing_changes = [c for c in report.changes if c.category == "routing"]

    assert len(routing_changes) >= 1
    assert routing_changes[0].parameter == "prefer_procedural"
    assert routing_changes[0].new_value is True


def test_empathy_increase_on_stress() -> None:
    """Verify warmth adjustment when operator is frequently stressed."""
    engine = RefinementEngine()

    for _ in range(5):
        engine.ingest_telemetry(
            TelemetrySnapshot(
                total_tasks=10,
                mode_distribution={"STATISTICAL": 10},
                p95_latency_ms=700.0,
                token_denials=0,
                rollback_count=0,
                macro_success_rate=0.8,
                emotional_states={"stressed": 8, "focused": 2},
            )
        )

    report = engine.analyze()
    emotion_changes = [c for c in report.changes if c.category == "emotion"]

    assert len(emotion_changes) >= 1
    assert emotion_changes[0].parameter == "ui_warmth_baseline"
    assert emotion_changes[0].new_value > emotion_changes[0].old_value


def test_report_formatting() -> None:
    """Verify report output is human-readable."""
    engine = RefinementEngine()
    engine.ingest_telemetry(
        TelemetrySnapshot(
            total_tasks=100,
            mode_distribution={"STATISTICAL": 50, "PROCEDURAL": 50},
            p95_latency_ms=650.0,
            token_denials=2,
            rollback_count=1,
            macro_success_rate=0.88,
            emotional_states={"focused": 80, "exploratory": 20},
        )
    )

    report = engine.analyze()
    text = format_report(report)

    assert "ASTRA Nightly Refinement Report" in text
    assert "Total tasks: 100" in text
    assert "No changes will be applied without explicit consent" in text
