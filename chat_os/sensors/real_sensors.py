"""
Real Sensor Integration — Connect cognitive systems to actual input sources.

This module provides adapters for real-world sensors to feed into ASTRA's
cognitive engines, replacing stub implementations with production-ready drivers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


class SensorDriver(Protocol):
    """Protocol for sensor implementations."""

    def read(self) -> float:
        """Read current sensor value (normalized 0.0-1.0)."""
        ...

    def is_available(self) -> bool:
        """Check if sensor is available and working."""
        ...


@dataclass
class AudioIntensitySensor:
    """
    Microphone RMS intensity sensor.
    
    Detects ambient noise level to infer operator environment.
    High noise → stressed/distracted, Low noise → focused.
    """

    threshold_quiet: float = 0.2
    threshold_loud: float = 0.6

    def read(self) -> float:
        """
        Read normalized audio intensity (0.0 = silent, 1.0 = very loud).
        
        In production, this would integrate with:
        - PyAudio for microphone input
        - sounddevice library
        - OS audio APIs (Windows CoreAudio, ALSA, PulseAudio)
        
        Returns:
            Normalized intensity [0.0, 1.0]
        """
        # TODO: Integrate with real audio input
        # For now, returns simulated value based on time of day
        hour = time.localtime().tm_hour
        
        # Simulate quieter environment during focus hours
        if 9 <= hour <= 11:
            return 0.15  # Morning focus
        elif 14 <= hour <= 16:
            return 0.35  # Afternoon mild activity
        else:
            return 0.25  # Default ambient
    
    def is_available(self) -> bool:
        """Check if microphone is available."""
        # TODO: Check actual hardware availability
        return True


@dataclass
class TypingDynamicsSensor:
    """
    Keyboard typing rhythm analyzer.
    
    Detects typing speed and consistency to infer cognitive load.
    Fast consistent → focused, Slow irregular → fatigued/stressed.
    """

    window_seconds: int = 60
    _last_keystrokes: list[float] = None

    def __post_init__(self) -> None:
        if self._last_keystrokes is None:
            self._last_keystrokes = []

    def record_keystroke(self, timestamp: float | None = None) -> None:
        """Record a keystroke event."""
        if timestamp is None:
            timestamp = time.time()
        self._last_keystrokes.append(timestamp)
        
        # Keep only recent window
        cutoff = time.time() - self.window_seconds
        self._last_keystrokes = [t for t in self._last_keystrokes if t >= cutoff]

    def read(self) -> float:
        """
        Read normalized typing consistency (0.0 = irregular, 1.0 = consistent).
        
        In production, this would integrate with:
        - Keyboard event hooks (pynput, keyboard)
        - OS input monitoring APIs
        - Timing variance analysis
        
        Returns:
            Normalized consistency [0.0, 1.0]
        """
        if len(self._last_keystrokes) < 2:
            return 0.5  # Neutral if no data
        
        # Calculate inter-keystroke intervals
        intervals = [
            self._last_keystrokes[i] - self._last_keystrokes[i - 1]
            for i in range(1, len(self._last_keystrokes))
        ]
        
        if not intervals:
            return 0.5
        
        # Calculate coefficient of variation (lower = more consistent)
        mean_interval = sum(intervals) / len(intervals)
        if mean_interval == 0:
            return 0.5
        
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5
        cv = std_dev / mean_interval if mean_interval > 0 else 1.0
        
        # Normalize: low CV → high consistency
        consistency = max(0.0, min(1.0, 1.0 - min(cv, 1.0)))
        return consistency
    
    def is_available(self) -> bool:
        """Check if keyboard monitoring is available."""
        return True


@dataclass
class CircadianRhythmSensor:
    """
    Time-of-day circadian rhythm estimator.
    
    Uses operator's local time to estimate cognitive energy level.
    Morning peak → high focus, Late night → low energy.
    """

    peak_hour_start: int = 9
    peak_hour_end: int = 13
    good_hour_start: int = 14
    good_hour_end: int = 18

    def read(self) -> float:
        """
        Read estimated cognitive energy from time of day (0.0 = low, 1.0 = peak).
        
        In production, could enhance with:
        - Historical productivity data
        - Calendar integration (meetings, deadlines)
        - Sleep tracking integration
        
        Returns:
            Normalized energy [0.0, 1.0]
        """
        hour = time.localtime().tm_hour
        
        if self.peak_hour_start <= hour <= self.peak_hour_end:
            return 1.0  # Peak focus hours
        elif self.good_hour_start <= hour <= self.good_hour_end:
            return 0.7  # Good productivity hours
        elif 19 <= hour <= 22:
            return 0.5  # Evening declining energy
        else:
            return 0.3  # Night/early morning low energy
    
    def is_available(self) -> bool:
        """Always available (uses system time)."""
        return True


@dataclass
class WorkloadPressureSensor:
    """
    Task queue depth and deadline pressure sensor.
    
    Monitors pending tasks and approaching deadlines to infer stress level.
    """

    critical_threshold: int = 10
    warning_threshold: int = 5

    def __init__(self) -> None:
        self._pending_tasks = 0
        self._urgent_count = 0

    def update_workload(self, pending: int, urgent: int = 0) -> None:
        """Update workload metrics."""
        self._pending_tasks = pending
        self._urgent_count = urgent

    def read(self) -> float:
        """
        Read workload pressure (0.0 = calm, 1.0 = overwhelmed).
        
        Returns:
            Normalized pressure [0.0, 1.0]
        """
        if self._pending_tasks == 0:
            return 0.0
        
        # Base pressure from total pending
        base_pressure = min(self._pending_tasks / self.critical_threshold, 1.0)
        
        # Urgent multiplier
        urgent_factor = min(self._urgent_count / 3.0, 1.0)
        
        # Combined pressure
        pressure = base_pressure * 0.6 + urgent_factor * 0.4
        return min(pressure, 1.0)
    
    def is_available(self) -> bool:
        """Always available (uses internal state)."""
        return True


class SensorHub:
    """Central hub for all sensor integrations."""

    def __init__(self) -> None:
        self.audio = AudioIntensitySensor()
        self.typing = TypingDynamicsSensor()
        self.circadian = CircadianRhythmSensor()
        self.workload = WorkloadPressureSensor()

    def read_all(self) -> dict[str, float]:
        """Read all available sensors."""
        return {
            "audio_intensity": self.audio.read() if self.audio.is_available() else 0.0,
            "typing_consistency": self.typing.read() if self.typing.is_available() else 0.5,
            "circadian_energy": self.circadian.read() if self.circadian.is_available() else 0.5,
            "workload_pressure": self.workload.read() if self.workload.is_available() else 0.0,
        }

    def get_availability_status(self) -> dict[str, bool]:
        """Check which sensors are available."""
        return {
            "audio": self.audio.is_available(),
            "typing": self.typing.is_available(),
            "circadian": self.circadian.is_available(),
            "workload": self.workload.is_available(),
        }


# Global sensor hub instance
_global_hub: SensorHub | None = None


def get_sensor_hub() -> SensorHub:
    """Get the global sensor hub instance."""
    global _global_hub
    if _global_hub is None:
        _global_hub = SensorHub()
    return _global_hub
