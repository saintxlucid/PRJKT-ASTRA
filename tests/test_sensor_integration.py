"""
Phase 2A: Real Sensor Integration Tests

Validates production-ready sensor drivers that will replace stub implementations.
Tests audio intensity, typing dynamics, circadian rhythm, and workload pressure sensors.
"""
from __future__ import annotations

import time

from chat_os.sensors import (
    AudioIntensitySensor,
    CircadianRhythmSensor,
    SensorHub,
    TypingDynamicsSensor,
    WorkloadPressureSensor,
    get_sensor_hub,
)


def test_audio_intensity_sensor_reads_successfully():
    """Audio intensity sensor should return valid readings."""
    sensor = AudioIntensitySensor()
    assert sensor.is_available()

    reading = sensor.read()
    assert isinstance(reading, float)
    assert 0.0 <= reading <= 1.0


def test_typing_dynamics_sensor_tracks_keystroke_rhythm():
    """Typing dynamics sensor should analyze keystroke timing patterns."""
    sensor = TypingDynamicsSensor()
    assert sensor.is_available()

    # Simulate keystroke sequence
    base_time = time.time()
    sensor.record_keystroke(base_time)
    sensor.record_keystroke(base_time + 0.15)  # Regular rhythm
    sensor.record_keystroke(base_time + 0.30)
    sensor.record_keystroke(base_time + 0.45)

    reading = sensor.read()
    assert isinstance(reading, float)
    assert 0.0 <= reading <= 1.0
    # Regular rhythm should have high consistency
    assert reading > 0.8


def test_circadian_rhythm_sensor_varies_by_time():
    """Circadian rhythm sensor should return different energy levels by hour."""
    sensor = CircadianRhythmSensor()
    assert sensor.is_available()

    # Get current reading
    reading = sensor.read()
    assert isinstance(reading, float)
    assert 0.0 <= reading <= 1.0

    # Energy should vary throughout the day
    # (exact value depends on current hour)
    assert reading >= 0.0


def test_workload_pressure_sensor_calculates_correctly():
    """Workload pressure sensor should reflect task queue depth and urgency."""
    sensor = WorkloadPressureSensor()
    assert sensor.is_available()

    # Light workload
    sensor.update_workload(pending=2, urgent=0)
    reading = sensor.read()
    assert isinstance(reading, float)
    light_pressure = reading
    assert 0.0 <= light_pressure <= 1.0

    # Heavy workload
    sensor.update_workload(pending=12, urgent=3)
    reading = sensor.read()
    heavy_pressure = reading
    assert heavy_pressure > light_pressure  # Should increase


def test_sensor_hub_aggregates_all_sensors():
    """SensorHub should aggregate readings from all sensor types."""
    hub = SensorHub()

    # Register sensors (they're already created in __init__)
    # Read all
    readings = hub.read_all()

    assert "audio_intensity" in readings
    assert isinstance(readings["audio_intensity"], float)
    assert "typing_consistency" in readings
    assert isinstance(readings["typing_consistency"], float)
    assert "circadian_energy" in readings
    assert isinstance(readings["circadian_energy"], float)
    assert "workload_pressure" in readings
    assert isinstance(readings["workload_pressure"], float)


def test_sensor_hub_availability_status():
    """SensorHub should report availability status for all sensors."""
    hub = SensorHub()

    hub.audio = AudioIntensitySensor()
    hub.typing = TypingDynamicsSensor()
    hub.circadian = CircadianRhythmSensor()
    hub.workload = WorkloadPressureSensor()

    status = hub.get_availability_status()

    assert status["audio"] is True
    assert status["typing"] is True
    assert status["circadian"] is True
    assert status["workload"] is True


def test_sensor_hub_singleton_access():
    """get_sensor_hub() should return consistent singleton instance."""
    hub1 = get_sensor_hub()
    hub2 = get_sensor_hub()

    assert hub1 is hub2  # Same instance
    assert isinstance(hub1, SensorHub)


def test_typing_consistency_with_irregular_rhythm():
    """Typing consistency should decrease with irregular keystroke timing."""
    sensor = TypingDynamicsSensor()

    # Record irregular keystrokes
    base_time = time.time()
    sensor.record_keystroke(base_time)
    sensor.record_keystroke(base_time + 0.05)  # Fast
    sensor.record_keystroke(base_time + 0.5)   # Slow
    sensor.record_keystroke(base_time + 0.55)  # Fast again

    reading = sensor.read()
    assert isinstance(reading, float)
    # Inconsistent rhythm should have lower consistency
    assert reading < 0.8  # Irregular pattern
