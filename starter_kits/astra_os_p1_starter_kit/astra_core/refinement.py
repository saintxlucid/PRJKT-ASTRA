"""
Nightly Refinement Engine — Self-optimization with operator approval.

Analyzes telemetry to propose tuning changes while maintaining sovereignty
through explicit consent gates.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TelemetrySnapshot:
    """Aggregated metrics from a session."""

    total_tasks: int
    mode_distribution: dict[str, int]
    p95_latency_ms: float
    token_denials: int
    rollback_count: int
    macro_success_rate: float
    emotional_states: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyChange:
    """Proposed change to system configuration."""

    category: str
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    impact: str


@dataclass
class RefinementReport:
    """Results of nightly optimization analysis."""

    timestamp: str
    changes: list[PolicyChange]
    metrics_summary: dict[str, Any]
    signature: str = ""


class RefinementEngine:
    """Analyzes telemetry and proposes optimization changes."""

    def __init__(self, thresholds: Mapping[str, float] | None = None) -> None:
        self._thresholds = dict(thresholds or self._default_thresholds())
        self._history: list[TelemetrySnapshot] = []

    @staticmethod
    def _default_thresholds() -> dict[str, float]:
        return {
            "budget_headroom_pct": 0.15,
            "macro_success_threshold": 0.85,
            "high_latency_ms": 1200.0,
            "token_denial_rate": 0.05,
        }

    def ingest_telemetry(self, snapshot: TelemetrySnapshot) -> None:
        """Record a telemetry snapshot for analysis."""
        self._history.append(snapshot)

    def analyze(self) -> RefinementReport:
        """Analyze recent telemetry and propose optimizations."""
        if not self._history:
            return RefinementReport(
                timestamp=self._now(),
                changes=[],
                metrics_summary={"status": "no_data"},
            )

        recent = self._history[-7:]  # Last week
        changes: list[PolicyChange] = []

        changes.extend(self._analyze_budget_pressure(recent))
        changes.extend(self._analyze_macro_performance(recent))
        changes.extend(self._analyze_latency(recent))
        changes.extend(self._analyze_emotional_trends(recent))

        summary = self._compute_summary(recent)

        return RefinementReport(
            timestamp=self._now(),
            changes=changes,
            metrics_summary=summary,
        )

    def _analyze_budget_pressure(self, snapshots: Sequence[TelemetrySnapshot]) -> list[PolicyChange]:
        changes = []
        avg_rollbacks = sum(s.rollback_count for s in snapshots) / len(snapshots)

        if avg_rollbacks > 2.0:
            changes.append(
                PolicyChange(
                    category="budget",
                    parameter="default_time_ms",
                    old_value=5000,
                    new_value=6000,
                    reason=f"Average {avg_rollbacks:.1f} rollbacks/session due to timeout",
                    impact="Reduces rollback frequency by ~20%",
                )
            )
        return changes

    def _analyze_macro_performance(self, snapshots: Sequence[TelemetrySnapshot]) -> list[PolicyChange]:
        changes = []
        avg_success = sum(s.macro_success_rate for s in snapshots) / len(snapshots)

        if avg_success > self._thresholds["macro_success_threshold"]:
            changes.append(
                PolicyChange(
                    category="routing",
                    parameter="prefer_procedural",
                    old_value=False,
                    new_value=True,
                    reason=f"Macro success rate {avg_success:.1%} exceeds threshold",
                    impact="Routes more deterministic tasks to macros, reducing LLM calls",
                )
            )
        return changes

    def _analyze_latency(self, snapshots: Sequence[TelemetrySnapshot]) -> list[PolicyChange]:
        changes = []
        avg_p95 = sum(s.p95_latency_ms for s in snapshots) / len(snapshots)

        if avg_p95 > self._thresholds["high_latency_ms"]:
            changes.append(
                PolicyChange(
                    category="performance",
                    parameter="llm_temperature",
                    old_value=0.7,
                    new_value=0.5,
                    reason=f"P95 latency {avg_p95:.0f}ms above {self._thresholds['high_latency_ms']:.0f}ms threshold",
                    impact="Reduces LLM generation time by ~15%",
                )
            )
        return changes

    def _analyze_emotional_trends(self, snapshots: Sequence[TelemetrySnapshot]) -> list[PolicyChange]:
        changes = []
        state_totals: dict[str, int] = {}
        for snap in snapshots:
            for state, count in snap.emotional_states.items():
                state_totals[state] = state_totals.get(state, 0) + count

        total = sum(state_totals.values())
        if total > 0:
            stressed_pct = state_totals.get("stressed", 0) / total
            if stressed_pct > 0.3:
                changes.append(
                    PolicyChange(
                        category="emotion",
                        parameter="ui_warmth_baseline",
                        old_value=0.6,
                        new_value=0.75,
                        reason=f"Operator stressed {stressed_pct:.1%} of sessions",
                        impact="Increases empathetic tone to reduce cognitive load",
                    )
                )
        return changes

    def _compute_summary(self, snapshots: Sequence[TelemetrySnapshot]) -> dict[str, Any]:
        total_tasks = sum(s.total_tasks for s in snapshots)
        avg_p95 = sum(s.p95_latency_ms for s in snapshots) / len(snapshots)
        avg_denials = sum(s.token_denials for s in snapshots) / len(snapshots)

        mode_total: dict[str, int] = {}
        for snap in snapshots:
            for mode, count in snap.mode_distribution.items():
                mode_total[mode] = mode_total.get(mode, 0) + count

        return {
            "total_tasks": total_tasks,
            "avg_p95_latency_ms": avg_p95,
            "avg_token_denials": avg_denials,
            "mode_distribution": mode_total,
            "sessions_analyzed": len(snapshots),
        }

    @staticmethod
    def _now() -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()


def format_report(report: RefinementReport) -> str:
    """Generate human-readable refinement report."""
    lines = [
        "╔════════════════════════════════════════════════════════════╗",
        "║         ASTRA Nightly Refinement Report                   ║",
        "╚════════════════════════════════════════════════════════════╝",
        "",
        f"Generated: {report.timestamp}",
        "",
        "Metrics Summary:",
        f"  • Total tasks: {report.metrics_summary.get('total_tasks', 0)}",
        f"  • Avg P95 latency: {report.metrics_summary.get('avg_p95_latency_ms', 0):.0f}ms",
        f"  • Sessions analyzed: {report.metrics_summary.get('sessions_analyzed', 0)}",
        "",
    ]

    if not report.changes:
        lines.append("✓ No optimization changes recommended. System performing optimally.")
    else:
        lines.append(f"Proposed Changes ({len(report.changes)}):")
        lines.append("")
        for idx, change in enumerate(report.changes, 1):
            lines.extend(
                [
                    f"{idx}. [{change.category.upper()}] {change.parameter}",
                    f"   Current: {change.old_value}",
                    f"   Proposed: {change.new_value}",
                    f"   Reason: {change.reason}",
                    f"   Impact: {change.impact}",
                    "",
                ]
            )

    lines.extend(
        [
            "─" * 60,
            "Review these changes and approve/deny in your morning ritual.",
            "No changes will be applied without explicit consent.",
        ]
    )

    return "\n".join(lines)
