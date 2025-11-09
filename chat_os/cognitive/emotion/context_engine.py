from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from chat_os.sensors import get_sensor_hub


class EnergyState(str, Enum):
    FOCUSED = "focused"
    FATIGUED = "fatigued"
    STRESSED = "stressed"
    EXPLORATORY = "exploratory"


@dataclass
class MicRMSDriver:
    """Legacy driver - now backed by real AudioIntensitySensor."""

    reader: Callable[[], float] | None = None

    def read(self) -> float:
        if self.reader is not None:
            return max(0.0, min(1.0, float(self.reader())))
        # Use real sensor hub
        hub = get_sensor_hub()
        readings = hub.read_all()
        return readings.get("audio_intensity", 0.15)


@dataclass
class TypingRhythmDriver:
    """Legacy driver - now backed by real TypingDynamicsSensor."""

    reader: Callable[[], float] | None = None

    def read(self) -> float:
        if self.reader is not None:
            return max(0.0, min(1.0, float(self.reader())))
        # Use real sensor hub
        hub = get_sensor_hub()
        readings = hub.read_all()
        return readings.get("typing_consistency", 0.5)


@dataclass
class TimeOfDayDriver:
    """Legacy driver - now backed by real CircadianRhythmSensor."""

    reader: Callable[[], float] | None = None

    def read(self) -> float:
        if self.reader is not None:
            return max(0.0, min(1.0, float(self.reader())))
        # Use real sensor hub
        hub = get_sensor_hub()
        readings = hub.read_all()
        return readings.get("circadian_energy", 0.5)


class EmotionalContextEngine:
    """
    Aggregates local-only signals to steer operator experience.

    Now enhanced with real sensor integration from Phase 2A:
    - AudioIntensitySensor for ambient noise detection
    - TypingDynamicsSensor for keystroke rhythm analysis
    - CircadianRhythmSensor for time-based energy estimation
    - WorkloadPressureSensor for task pressure monitoring
    """

    def __init__(self, use_real_sensors: bool = True) -> None:
        self.use_real_sensors = use_real_sensors
        self.mic = MicRMSDriver()
        self.typing = TypingRhythmDriver()
        self.tod = TimeOfDayDriver()

    def infer(self) -> dict[str, Any]:
        """
        Infer operator emotional state from sensor fusion.

        Returns:
            Dict with state, sensor readings, and UI adjustments
        """
        noise = self.mic.read()
        typing = self.typing.read()
        tod = self.tod.read()

        # Get workload pressure from sensor hub
        hub = get_sensor_hub()
        readings = hub.read_all()
        workload = readings.get("workload_pressure", 0.0)

        # Enhanced state inference with workload awareness
        fatigue = 1.0 - tod
        stress = noise * 0.5 + (1.0 - typing) * 0.3 + workload * 0.2

        if stress > 0.6:
            state = EnergyState.STRESSED
        elif fatigue > 0.6:
            state = EnergyState.FATIGUED
        elif tod > 0.9 and typing > 0.7:
            state = EnergyState.FOCUSED
        else:
            state = EnergyState.EXPLORATORY

        ui = {
            "warmth": 0.8 if state in (EnergyState.FATIGUED, EnergyState.STRESSED) else 0.6,
            "brightness": 0.7 if state is EnergyState.FOCUSED else 0.5,
            "verbosity": 0.7 if state is EnergyState.EXPLORATORY else 0.5,
        }
        return {
            "state": state.value,
            "noise": noise,
            "typing": typing,
            "tod": tod,
            "workload": workload,
            "ui": ui,
        }
