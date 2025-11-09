from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass
class LucidWeights:
    """Lucid Protocol steering vector with basic validation."""

    truth_compassion: float = 0.5
    logic_intuition: float = 0.5
    order_freedom: float = 0.5
    efficiency_safety: float = 0.5

    def clamp(self) -> LucidWeights:
        for key, value in vars(self).items():
            bounded = 0.0 if value < 0.0 else (1.0 if value > 1.0 else float(value))
            setattr(self, key, bounded)
        return self


def steer_tone(error: bool, weights: LucidWeights) -> str:
    weights.clamp()
    if not error:
        return "Proceeding smoothly."
    if weights.truth_compassion < 0.4:
        return "Error: invalid input. Check signature."
    if weights.truth_compassion > 0.6:
        return "I couldn’t complete that—let’s try a safer path."
    return "That didn’t work—token invalid."


def prioritize(actions: Iterable[dict[str, Any]], weights: LucidWeights) -> list[dict[str, Any]]:
    weights.clamp()
    ordered = list(actions)
    if weights.order_freedom < 0.4:
        ordered.sort(key=lambda action: action.get("sequence", 0))
    elif weights.order_freedom > 0.6:
        ordered.sort(key=lambda action: action.get("preference", 0), reverse=True)
    return ordered
