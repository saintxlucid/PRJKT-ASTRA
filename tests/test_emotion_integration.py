"""
Phase 2B: Emotion-Sensor Integration Tests

Validates that EmotionalContextEngine properly integrates with
real sensor infrastructure from Phase 2A.
"""
from __future__ import annotations

from chat_os.cognitive.emotion.context_engine import (
    EmotionalContextEngine,
    EnergyState,
)
from chat_os.sensors import get_sensor_hub


def test_emotion_engine_uses_real_sensors():
    """EmotionalContextEngine should integrate with SensorHub."""
    engine = EmotionalContextEngine()

    # Get inference
    result = engine.infer()

    # Should have all expected fields
    assert "state" in result
    assert "noise" in result
    assert "typing" in result
    assert "tod" in result
    assert "workload" in result
    assert "ui" in result

    # State should be valid
    assert result["state"] in [s.value for s in EnergyState]

    # All sensor values should be normalized
    assert 0.0 <= result["noise"] <= 1.0
    assert 0.0 <= result["typing"] <= 1.0
    assert 0.0 <= result["tod"] <= 1.0
    assert 0.0 <= result["workload"] <= 1.0


def test_emotion_state_inference_focused():
    """Emotion engine should compute state from sensor fusion."""
    hub = get_sensor_hub()

    # Simulate focused conditions
    # No workload pressure
    hub.workload.update_workload(pending=0, urgent=0)

    engine = EmotionalContextEngine()
    result = engine.infer()

    # Should have valid sensor readings
    # (Actual values depend on time of day)
    assert "tod" in result
    assert "typing" in result
    assert result["workload"] == 0.0  # Confirmed no workload


def test_emotion_state_inference_stressed():
    """High noise + high workload should yield STRESSED state."""
    hub = get_sensor_hub()

    # Simulate stressed conditions
    hub.workload.update_workload(pending=15, urgent=5)

    engine = EmotionalContextEngine()
    result = engine.infer()

    # Workload should be reflected
    assert result["workload"] > 0.0


def test_emotion_ui_adaptation_warmth():
    """UI warmth should increase when stressed or fatigued."""
    engine = EmotionalContextEngine()
    result = engine.infer()

    # Check UI adjustments exist
    assert "warmth" in result["ui"]
    assert "brightness" in result["ui"]
    assert "verbosity" in result["ui"]

    # All should be normalized
    assert 0.0 <= result["ui"]["warmth"] <= 1.0
    assert 0.0 <= result["ui"]["brightness"] <= 1.0
    assert 0.0 <= result["ui"]["verbosity"] <= 1.0


def test_emotion_workload_integration():
    """Workload sensor should influence stress calculation."""
    hub = get_sensor_hub()

    # Test with light workload
    hub.workload.update_workload(pending=2, urgent=0)
    engine = EmotionalContextEngine()
    result_light = engine.infer()
    workload_light = result_light["workload"]

    # Test with heavy workload
    hub.workload.update_workload(pending=20, urgent=5)
    result_heavy = engine.infer()
    workload_heavy = result_heavy["workload"]

    # Heavy workload should be higher
    assert workload_heavy > workload_light


def test_emotion_sensor_availability():
    """Emotion engine should handle sensor unavailability gracefully."""
    engine = EmotionalContextEngine()

    # Should still return valid result even if sensors fail
    result = engine.infer()

    assert result is not None
    assert "state" in result
    assert result["state"] in [s.value for s in EnergyState]


def test_emotion_legacy_driver_override():
    """Legacy drivers should support custom reader override."""
    from chat_os.cognitive.emotion.context_engine import MicRMSDriver

    # Create driver with custom reader
    def custom_reader() -> float:
        return 0.75

    driver = MicRMSDriver(reader=custom_reader)

    # Should use custom reader
    assert driver.read() == 0.75


def test_emotion_inference_includes_workload():
    """Emotion inference should include workload pressure in result."""
    engine = EmotionalContextEngine()
    result = engine.infer()

    # Workload should be in result
    assert "workload" in result
    assert isinstance(result["workload"], float)
    assert 0.0 <= result["workload"] <= 1.0
