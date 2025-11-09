from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astra_core.macro_mining import ExecutionTrace, MacroMiner, generate_macro_dsl  # noqa: E402


def test_macro_learning_from_repeated_pattern() -> None:
    """Verify that repeated successful patterns are learned as macros."""
    miner = MacroMiner(min_confidence=0.80, min_occurrences=3)

    for _ in range(5):
        miner.ingest_trace(
            ExecutionTrace(
                task_name="daily_standup",
                steps=[
                    {"type": "open_app", "app": "teams"},
                    {"type": "join_meeting", "room": "standup"},
                    {"type": "mute", "device": "microphone"},
                ],
                duration_ms=2500.0,
                mode="PROCEDURAL",
                success=True,
                metadata={"token_scope": "ui+process"},
            )
        )

    learned = miner.mine_macros()
    assert len(learned) == 1
    assert learned[0].name == "daily_standup"
    assert learned[0].confidence == 1.0


def test_macro_not_learned_with_insufficient_occurrences() -> None:
    """Verify macros require minimum occurrence threshold."""
    miner = MacroMiner(min_occurrences=5)

    for _ in range(3):
        miner.ingest_trace(
            ExecutionTrace(
                task_name="rare_task",
                steps=[{"type": "action"}],
                duration_ms=100.0,
                mode="PROCEDURAL",
                success=True,
            )
        )

    learned = miner.mine_macros()
    assert len(learned) == 0


def test_macro_dsl_generation() -> None:
    """Verify DSL output format is readable."""
    miner = MacroMiner(min_occurrences=1)
    miner.ingest_trace(
        ExecutionTrace(
            task_name="sample",
            steps=[{"type": "test", "arg": 123}],
            duration_ms=50.0,
            mode="PROCEDURAL",
            success=True,
            metadata={"token_scope": "automation"},
        )
    )

    macros = miner.mine_macros()
    dsl = generate_macro_dsl(macros[0])

    assert "macro sample:" in dsl
    assert "confidence: 100.00%" in dsl
    assert "test(arg=123)" in dsl
