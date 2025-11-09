from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astra_core.emotion.context_engine import EmotionalContextEngine, EnergyState  # noqa: E402


def test_emotional_infer_smoke() -> None:
    engine = EmotionalContextEngine()
    result = engine.infer()

    assert result["state"] in {state.value for state in EnergyState}
    assert "ui" in result
    assert set(result["ui"]) == {"warmth", "brightness", "verbosity"}
