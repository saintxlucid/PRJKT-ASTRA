from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSet
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from chat_os.cognitive.emotion.context_engine import EmotionalContextEngine, EnergyState


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
    """
    Risk-aware creativity gate that blends Lucid Protocol weights.

    Enhanced in Phase 2C to adapt based on operator emotional state:
    - STRESSED → reduce creativity (safety priority)
    - FATIGUED → reduce creativity (avoid errors)
    - FOCUSED → allow higher creativity (deep thinking enabled)
    - EXPLORATORY → moderate creativity (balanced)
    """

    def __init__(
        self,
        lucid_weights: Mapping[str, float],
        emotion_engine: EmotionalContextEngine | None = None,
    ) -> None:
        self._lucid = dict(lucid_weights)
        self._emotion_engine = emotion_engine or EmotionalContextEngine()
        self._base_temperature: float = 0.5
        self._emotion_adjustment: float = 0.0

    def adjust_for_emotion(self) -> None:
        """
        Adjust creativity parameters based on current emotional state.

        Called before routing decisions to ensure emotion-aware behavior.
        """
        emotion = self._emotion_engine.infer()
        state = emotion["state"]

        # Emotion-based adjustments
        if state == EnergyState.STRESSED.value:
            # Reduce creativity under stress (safety priority)
            self._emotion_adjustment = -0.3
        elif state == EnergyState.FATIGUED.value:
            # Reduce creativity when fatigued (avoid errors)
            self._emotion_adjustment = -0.2
        elif state == EnergyState.FOCUSED.value:
            # Allow higher creativity when focused (deep thinking)
            self._emotion_adjustment = +0.1
        else:  # EXPLORATORY
            # Moderate creativity for exploration
            self._emotion_adjustment = 0.0

    def temperature_for(self, task: Task) -> float:
        """
        Calculate temperature for a task based on risk and emotional state.

        Returns:
            Temperature value [0.05, 1.0]
        """
        # Base temperature from risk level
        base = 0.2 if task.risk is RiskLevel.HIGH else (0.5 if task.risk is RiskLevel.MEDIUM else 0.8)

        # Apply Lucid Protocol steering
        logic_vs_intuition = float(self._lucid.get("logic_intuition", 0.5))
        steered = base * (0.5 + logic_vs_intuition)

        # Apply emotion adjustment
        adjusted = steered + self._emotion_adjustment

        return max(0.05, min(1.0, adjusted))


class MetaController:
    """
    Central router selecting the most appropriate reasoning mode.

    Enhanced in Phase 2C to adapt routing based on emotional state:
    - FATIGUED → prefer PROCEDURAL (fast, safe macros)
    - STRESSED → prefer PROCEDURAL or SYMBOLIC (avoid LLM uncertainty)
    - FOCUSED → allow STATISTICAL (deep LLM reasoning)
    """

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
        """
        Route task to appropriate reasoning mode.

        Enhanced routing considers emotional state for adaptive behavior.
        """
        # Update governor with current emotion
        self._governor.adjust_for_emotion()

        # Get current emotional state
        emotion = self._governor._emotion_engine.infer()
        state = emotion["state"]

        # Prefer macros when fatigued or stressed (fast, safe)
        if state in (EnergyState.FATIGUED.value, EnergyState.STRESSED.value):
            if task.name in self._macro_index:
                return ReasoningMode.PROCEDURAL

        # Original routing logic
        if task.deterministic:
            if task.name in self._macro_index:
                return ReasoningMode.PROCEDURAL
            return ReasoningMode.SYMBOLIC

        if task.risk is RiskLevel.HIGH:
            return ReasoningMode.SYMBOLIC

        # Avoid statistical reasoning when stressed (unless necessary)
        if state == EnergyState.STRESSED.value and task.risk is RiskLevel.MEDIUM:
            return ReasoningMode.SYMBOLIC

        return ReasoningMode.STATISTICAL

    def run(self, task: Task) -> EngineResult:
        mode = self.route(task)
        if mode is ReasoningMode.PROCEDURAL:
            return self._procedural.execute(task)
        if mode is ReasoningMode.SYMBOLIC:
            return self._symbolic.execute(task)
        return self._statistical.execute(task)
