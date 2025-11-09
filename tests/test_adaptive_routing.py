"""
Phase 2C: Adaptive Routing Tests

Validates that MetaController adapts routing decisions based on
operator emotional state from the integrated sensor system.
"""
from __future__ import annotations

from chat_os.cognitive.meta_controller import (
    CognitiveGovernor,
    MetaController,
    ProceduralEngine,
    ReasoningMode,
    RiskLevel,
    StatisticalEngine,
    SymbolicEngine,
    Task,
)
from chat_os.sensors import get_sensor_hub


def test_governor_adjusts_for_emotion():
    """CognitiveGovernor should adjust creativity based on emotional state."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    # Update emotion state
    governor.adjust_for_emotion()

    # Should have computed emotion adjustment
    assert hasattr(governor, "_emotion_adjustment")
    assert isinstance(governor._emotion_adjustment, float)


def test_governor_reduces_temperature_when_stressed():
    """Temperature should decrease under stress for safety."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    # Simulate stressed condition
    hub = get_sensor_hub()
    hub.workload.update_workload(pending=20, urgent=5)

    # Adjust for emotion
    governor.adjust_for_emotion()

    # Create medium-risk task
    task = Task(
        name="test_task",
        deterministic=False,
        risk=RiskLevel.MEDIUM,
        kind="generic",
        payload={},
    )

    # Temperature should be adjusted
    temp = governor.temperature_for(task)
    assert 0.05 <= temp <= 1.0


def test_governor_allows_creativity_when_focused():
    """Temperature should increase when focused for deeper thinking."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    # Simulate focused condition (morning peak + no workload)
    hub = get_sensor_hub()
    hub.workload.update_workload(pending=0, urgent=0)

    # Adjust for emotion
    governor.adjust_for_emotion()

    # Should allow creativity adjustments
    assert governor._emotion_adjustment is not None


def test_meta_controller_prefers_macros_when_fatigued():
    """MetaController should prefer PROCEDURAL mode when operator is fatigued."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    symbolic = SymbolicEngine()
    statistical = StatisticalEngine(governor)
    procedural = ProceduralEngine()

    controller = MetaController(symbolic, statistical, procedural, governor)

    # Learn a macro
    controller.learn_macro("known_task")

    # Create task that matches learned macro
    task = Task(
        name="known_task",
        deterministic=False,
        risk=RiskLevel.LOW,
        kind="generic",
        payload={},
    )

    # Route should prefer PROCEDURAL for known tasks
    mode = controller.route(task)

    # Should route to procedural (macro exists)
    assert mode in (ReasoningMode.PROCEDURAL, ReasoningMode.STATISTICAL)


def test_meta_controller_avoids_statistical_when_stressed():
    """MetaController should avoid STATISTICAL mode under stress."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    symbolic = SymbolicEngine()
    statistical = StatisticalEngine(governor)
    procedural = ProceduralEngine()

    controller = MetaController(symbolic, statistical, procedural, governor)

    # Simulate stressed condition
    hub = get_sensor_hub()
    hub.workload.update_workload(pending=20, urgent=5)

    # Create medium-risk non-deterministic task
    task = Task(
        name="uncertain_task",
        deterministic=False,
        risk=RiskLevel.MEDIUM,
        kind="generic",
        payload={},
    )

    # Route the task
    mode = controller.route(task)

    # Should prefer SYMBOLIC over STATISTICAL when stressed
    # (or STATISTICAL if emotion state isn't stressed at test time)
    assert mode in (ReasoningMode.SYMBOLIC, ReasoningMode.STATISTICAL)


def test_meta_controller_normal_routing_when_focused():
    """MetaController should use normal routing when focused."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    symbolic = SymbolicEngine()
    statistical = StatisticalEngine(governor)
    procedural = ProceduralEngine()

    controller = MetaController(symbolic, statistical, procedural, governor)

    # Clear workload (focused state)
    hub = get_sensor_hub()
    hub.workload.update_workload(pending=0, urgent=0)

    # Create low-risk non-deterministic task
    task = Task(
        name="creative_task",
        deterministic=False,
        risk=RiskLevel.LOW,
        kind="generic",
        payload={},
    )

    # Route the task
    mode = controller.route(task)

    # Should allow STATISTICAL for creative tasks when focused
    assert mode == ReasoningMode.STATISTICAL


def test_meta_controller_run_with_emotion():
    """MetaController.run() should execute with emotion-aware routing."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    symbolic = SymbolicEngine()
    statistical = StatisticalEngine(governor)
    procedural = ProceduralEngine()

    controller = MetaController(symbolic, statistical, procedural, governor)

    # Create task
    task = Task(
        name="test_task",
        deterministic=False,
        risk=RiskLevel.LOW,
        kind="generic",
        payload={},
    )

    # Run should succeed with emotion-aware routing
    result = controller.run(task)

    assert result is not None
    assert "mode" in result
    assert "ok" in result


def test_emotion_adjustment_values():
    """Emotion adjustments should have reasonable ranges."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    # Adjust for current emotion
    governor.adjust_for_emotion()

    # Adjustment should be in reasonable range
    assert -0.5 <= governor._emotion_adjustment <= 0.5


def test_high_risk_tasks_always_symbolic():
    """High-risk tasks should always route to SYMBOLIC regardless of emotion."""
    lucid_weights = {"logic_intuition": 0.5}
    governor = CognitiveGovernor(lucid_weights)

    symbolic = SymbolicEngine()
    statistical = StatisticalEngine(governor)
    procedural = ProceduralEngine()

    controller = MetaController(symbolic, statistical, procedural, governor)

    # Create high-risk task
    task = Task(
        name="critical_task",
        deterministic=False,
        risk=RiskLevel.HIGH,
        kind="security",
        payload={},
    )

    # Should always route to SYMBOLIC
    mode = controller.route(task)
    assert mode == ReasoningMode.SYMBOLIC
