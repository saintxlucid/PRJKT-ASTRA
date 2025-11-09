"""
Macro Mining Engine — Learn procedural workflows from successful traces.

This module analyzes execution traces to identify repeatable patterns and
converts them into efficient, deterministic macros that can bypass expensive
LLM calls for routine tasks.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionTrace:
    """Record of a successfully completed task execution."""

    task_name: str
    steps: list[dict[str, Any]]
    duration_ms: float
    mode: str
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Macro:
    """Learned deterministic workflow."""

    name: str
    pattern: str
    steps: list[dict[str, Any]]
    token_scope: str
    budget_ms: int
    success_count: int = 0
    failure_count: int = 0

    @property
    def confidence(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


class MacroMiner:
    """Identifies and learns macros from execution telemetry."""

    def __init__(self, min_confidence: float = 0.85, min_occurrences: int = 3) -> None:
        self._min_confidence = min_confidence
        self._min_occurrences = min_occurrences
        self._traces: list[ExecutionTrace] = []
        self._macros: dict[str, Macro] = {}

    def ingest_trace(self, trace: ExecutionTrace) -> None:
        """Record a new execution trace for analysis."""
        self._traces.append(trace)

    def mine_macros(self) -> list[Macro]:
        """Analyze traces and extract repeatable patterns."""
        candidates: dict[str, list[ExecutionTrace]] = {}

        for trace in self._traces:
            if not trace.success:
                continue
            pattern = self._compute_pattern(trace)
            if pattern not in candidates:
                candidates[pattern] = []
            candidates[pattern].append(trace)

        learned: list[Macro] = []
        for pattern, traces in candidates.items():
            if len(traces) < self._min_occurrences:
                continue

            macro = self._build_macro(pattern, traces)
            if macro.confidence >= self._min_confidence:
                self._macros[macro.name] = macro
                learned.append(macro)

        return learned

    def get_macro(self, task_name: str) -> Macro | None:
        """Retrieve a learned macro by task name."""
        return self._macros.get(task_name)

    def all_macros(self) -> Iterable[Macro]:
        """Return all learned macros."""
        return tuple(self._macros.values())

    def _compute_pattern(self, trace: ExecutionTrace) -> str:
        """Generate a stable pattern key from trace structure."""
        step_types = tuple(step.get("type", "unknown") for step in trace.steps)
        return f"{trace.task_name}::{':'.join(step_types)}"

    def _build_macro(self, pattern: str, traces: Sequence[ExecutionTrace]) -> Macro:
        """Construct a macro from similar traces."""
        representative = traces[0]
        task_name = representative.task_name

        avg_duration = sum(t.duration_ms for t in traces) / len(traces)
        budget_ms = int(avg_duration * 1.5)

        steps = representative.steps.copy()

        token_scope = representative.metadata.get("token_scope", "automation")

        success_count = sum(1 for t in traces if t.success)
        failure_count = len(traces) - success_count

        return Macro(
            name=task_name,
            pattern=pattern,
            steps=steps,
            token_scope=token_scope,
            budget_ms=budget_ms,
            success_count=success_count,
            failure_count=failure_count,
        )


def generate_macro_dsl(macro: Macro) -> str:
    """Generate a human-readable DSL representation of a macro."""
    lines = [
        f"macro {macro.name}:",
        f"  pattern: {macro.pattern}",
        f"  confidence: {macro.confidence:.2%}",
        f"  budget: {macro.budget_ms}ms",
        f"  scope: {macro.token_scope}",
        "  steps:",
    ]
    for idx, step in enumerate(macro.steps, 1):
        step_type = step.get("type", "unknown")
        step_args = ", ".join(f"{k}={v!r}" for k, v in step.items() if k != "type")
        lines.append(f"    {idx}. {step_type}({step_args})")
    return "\n".join(lines)
