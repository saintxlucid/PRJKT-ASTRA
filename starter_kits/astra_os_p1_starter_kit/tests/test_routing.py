from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astra_core.meta_controller import (  # noqa: E402
    CognitiveGovernor,
    MetaController,
    ProceduralEngine,
    ReasoningMode,
    RiskLevel,
    StatisticalEngine,
    SymbolicEngine,
    Task,
)


def _build_controller(logic_intuition: float = 0.6) -> MetaController:
    governor = CognitiveGovernor({"logic_intuition": logic_intuition})
    return MetaController(SymbolicEngine(), StatisticalEngine(governor), ProceduralEngine(), governor)


def test_routing_deterministic_defaults() -> None:
    controller = _build_controller()
    task = Task("file_checksum", deterministic=True, risk=RiskLevel.MEDIUM, kind="file_op", payload={})
    result = controller.run(task)
    assert result["mode"] in {ReasoningMode.SYMBOLIC.name, ReasoningMode.PROCEDURAL.name}


def test_routing_macro_prefers_procedural() -> None:
    controller = _build_controller()
    controller.learn_macro("file_checksum")
    task = Task("file_checksum", deterministic=True, risk=RiskLevel.LOW, kind="file_op", payload={})
    result = controller.run(task)
    assert result["mode"] == ReasoningMode.PROCEDURAL.name


def test_routing_open_task_prefers_statistical() -> None:
    controller = _build_controller(logic_intuition=0.9)
    task = Task("write_email", deterministic=False, risk=RiskLevel.LOW, kind="dialogue", payload={})
    result = controller.run(task)
    assert result["mode"] == ReasoningMode.STATISTICAL.name
