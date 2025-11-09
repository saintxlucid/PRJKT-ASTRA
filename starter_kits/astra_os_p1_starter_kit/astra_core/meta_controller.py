from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSet
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class ReasoningMode(Enum):
    """Reasoning pathways supported by the meta-controller."""

    SYMBOLIC = auto()
    STATISTICAL = auto()
    PROCEDURAL = auto()


class RiskLevel(Enum):
    """Risk profile used to steer creativity and safeguards."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Task:
    """Light-weight task container shared across engines."""

    name: str
    deterministic: bool
    risk: RiskLevel
    kind: str
    payload: dict[str, Any]


EngineResult = dict[str, Any]


class SymbolicEngine:
    """Placeholder for rule-based or program verification tooling."""

    def execute(self, task: Task) -> EngineResult:
        return {"mode": "SYMBOLIC", "ok": True, "notes": "Symbolic path taken."}


class StatisticalEngine:
    """LLM-backed reasoning routed through the governor."""

    def __init__(self, governor: CognitiveGovernor) -> None:
        self._governor = governor

    def execute(self, task: Task) -> EngineResult:
        temperature = self._governor.temperature_for(task)
        return {
            "mode": "STATISTICAL",
            "ok": True,
            "temp": temperature,
            "notes": "LLM path (mock).",
        }


class ProceduralEngine:
    """Macro playback or deterministic orchestration."""

    def execute(self, task: Task) -> EngineResult:
        return {"mode": "PROCEDURAL", "ok": True, "notes": "Macro/plan executed."}


class CognitiveGovernor:
    """Risk-aware creativity gate that blends Lucid Protocol weights."""

    def __init__(self, lucid_weights: Mapping[str, float]) -> None:
        self._lucid = dict(lucid_weights)

    def temperature_for(self, task: Task) -> float:
        base = 0.2 if task.risk is RiskLevel.HIGH else (0.5 if task.risk is RiskLevel.MEDIUM else 0.8)
        logic_vs_intuition = float(self._lucid.get("logic_intuition", 0.5))
        steered = base * (0.5 + logic_vs_intuition)
        return max(0.05, min(1.0, steered))


class MetaController:
    """Central router selecting the most appropriate reasoning mode."""

    def __init__(
        self,
        symbolic: SymbolicEngine,
        statistical: StatisticalEngine,
        procedural: ProceduralEngine,
        governor: CognitiveGovernor,
    ) -> None:
        self._symbolic = symbolic
        self._statistical = statistical
        self._procedural = procedural
        self._governor = governor
        self._macro_index: MutableSet[str] = set()

    def learn_macro(self, task_name: str) -> None:
        self._macro_index.add(task_name)

    def known_macros(self) -> Iterable[str]:
        return tuple(self._macro_index)

    def route(self, task: Task) -> ReasoningMode:
        if task.deterministic:
            if task.name in self._macro_index:
                return ReasoningMode.PROCEDURAL
            return ReasoningMode.SYMBOLIC
        if task.risk is RiskLevel.HIGH:
            return ReasoningMode.SYMBOLIC
        return ReasoningMode.STATISTICAL

    def run(self, task: Task) -> EngineResult:
        mode = self.route(task)
        if mode is ReasoningMode.PROCEDURAL:
            return self._procedural.execute(task)
        if mode is ReasoningMode.SYMBOLIC:
            return self._symbolic.execute(task)
        return self._statistical.execute(task)
