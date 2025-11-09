from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EnergyState(str, Enum):
    FOCUSED = "focused"
    FATIGUED = "fatigued"
    STRESSED = "stressed"
    EXPLORATORY = "exploratory"


@dataclass
class MicRMSDriver:
    reader: Callable[[], float] | None = None

    def read(self) -> float:
        if self.reader is not None:
            return max(0.0, min(1.0, float(self.reader())))
        return 0.15


@dataclass
class TypingRhythmDriver:
    reader: Callable[[], float] | None = None

    def read(self) -> float:
        if self.reader is not None:
            return max(0.0, min(1.0, float(self.reader())))
        return 0.5


@dataclass
class TimeOfDayDriver:
    reader: Callable[[], float] | None = None

    def read(self) -> float:
        if self.reader is not None:
            return max(0.0, min(1.0, float(self.reader())))
        hour = time.localtime().tm_hour
        if 9 <= hour <= 13:
            return 1.0
        if 14 <= hour <= 18:
            return 0.7
        return 0.4


class EmotionalContextEngine:
    """Aggregates local-only signals to steer operator experience."""

    def __init__(self) -> None:
        self.mic = MicRMSDriver()
        self.typing = TypingRhythmDriver()
        self.tod = TimeOfDayDriver()

    def infer(self) -> dict[str, Any]:
        noise = self.mic.read()
        typing = self.typing.read()
        tod = self.tod.read()

        fatigue = 1.0 - tod
        stress = noise * 0.7 + (1.0 - typing) * 0.3
        if stress > 0.6:
            state = EnergyState.STRESSED
        elif fatigue > 0.6:
            state = EnergyState.FATIGUED
        elif tod > 0.9:
            state = EnergyState.FOCUSED
        else:
            state = EnergyState.EXPLORATORY

        ui = {
            "warmth": 0.8 if state in (EnergyState.FATIGUED, EnergyState.STRESSED) else 0.6,
            "brightness": 0.7 if state is EnergyState.FOCUSED else 0.5,
            "verbosity": 0.7 if state is EnergyState.EXPLORATORY else 0.5,
        }
        return {"state": state.value, "noise": noise, "typing": typing, "tod": tod, "ui": ui}
