"""
Telemetry Collection System — Track execution metrics for refinement.

This module collects performance and behavioral metrics from plan execution
to enable nightly refinement analysis and optimization proposals.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TelemetrySnapshot:
    """Aggregated metrics from a period of execution."""

    total_tasks: int
    mode_distribution: dict[str, int]
    p95_latency_ms: float
    rollback_count: int
    macro_success_rate: float
    emotional_states: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)


class TelemetryCollector:
    """Collects and aggregates execution metrics over time."""

    def __init__(self) -> None:
        self._task_count = 0
        self._mode_counts: dict[str, int] = defaultdict(int)
        self._latencies: list[float] = []
        self._rollback_count = 0
        self._macro_successes = 0
        self._macro_attempts = 0
        self._emotional_states: dict[str, int] = defaultdict(int)
        self._metadata: dict[str, Any] = {}

    def record_task(
        self,
        mode: str,
        latency_ms: float,
        success: bool,
        used_macro: bool = False,
        emotional_state: str | None = None,
    ) -> None:
        """
        Record metrics for a single task execution.

        Args:
            mode: Reasoning mode used (SYMBOLIC/STATISTICAL/PROCEDURAL)
            latency_ms: Task execution time in milliseconds
            success: Whether task completed successfully
            used_macro: Whether a learned macro was used
            emotional_state: Detected operator emotional state
        """
        self._task_count += 1
        self._mode_counts[mode] += 1
        self._latencies.append(latency_ms)

        if used_macro:
            self._macro_attempts += 1
            if success:
                self._macro_successes += 1

        if emotional_state:
            self._emotional_states[emotional_state] += 1

    def record_rollback(self) -> None:
        """Record a plan rollback event."""
        self._rollback_count += 1

    def set_metadata(self, key: str, value: Any) -> None:
        """Store additional context metadata."""
        self._metadata[key] = value

    def snapshot(self) -> TelemetrySnapshot:
        """
        Generate a snapshot of current metrics.

        Returns:
            TelemetrySnapshot with aggregated metrics
        """
        # Calculate p95 latency
        if len(self._latencies) == 0:
            p95_latency = 0.0
        else:
            sorted_latencies = sorted(self._latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]

        # Calculate macro success rate
        if self._macro_attempts == 0:
            macro_success_rate = 0.0
        else:
            macro_success_rate = self._macro_successes / self._macro_attempts

        return TelemetrySnapshot(
            total_tasks=self._task_count,
            mode_distribution=dict(self._mode_counts),
            p95_latency_ms=p95_latency,
            rollback_count=self._rollback_count,
            macro_success_rate=macro_success_rate,
            emotional_states=dict(self._emotional_states),
            metadata=self._metadata.copy(),
        )

    def reset(self) -> None:
        """Clear all collected metrics."""
        self._task_count = 0
        self._mode_counts.clear()
        self._latencies.clear()
        self._rollback_count = 0
        self._macro_successes = 0
        self._macro_attempts = 0
        self._emotional_states.clear()
        self._metadata.clear()


# Global collector instance for session-wide tracking
_global_collector = TelemetryCollector()


def get_global_collector() -> TelemetryCollector:
    """Get the global telemetry collector instance."""
    return _global_collector


def record_task_telemetry(
    mode: str,
    latency_ms: float,
    success: bool,
    used_macro: bool = False,
    emotional_state: str | None = None,
) -> None:
    """
    Convenience function to record task metrics to global collector.

    Args:
        mode: Reasoning mode used
        latency_ms: Task execution time
        success: Whether task succeeded
        used_macro: Whether a macro was used
        emotional_state: Detected emotional state
    """
    _global_collector.record_task(mode, latency_ms, success, used_macro, emotional_state)


def record_rollback() -> None:
    """Record a rollback event to global collector."""
    _global_collector.record_rollback()


def get_session_snapshot() -> TelemetrySnapshot:
    """Get a snapshot of session-wide telemetry."""
    return _global_collector.snapshot()
