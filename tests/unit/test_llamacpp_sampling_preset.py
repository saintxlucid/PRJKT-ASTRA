"""Unit test for llama.cpp sampling preset integration."""

from __future__ import annotations

from typing import List, Optional, cast

import pytest

from astra.models.config import Settings  # type: ignore[import-untyped]
from astra.infrastructure.llm.llamacpp import LlamaCppProvider  # type: ignore[import-untyped]
from astra.infrastructure.llm.sampling import StopTokenManager  # type: ignore[import-untyped]


class _Req:
    def __init__(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> None:
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.stop = stop


def test_preset_applied_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sampling_preset", "gptoss-strict", raising=False)
    monkeypatch.setattr(
        StopTokenManager,
        "harmony_stops",
        staticmethod(lambda: ["<|stop|>", "<|end|>"]),
        raising=False,
    )

    provider = LlamaCppProvider(base_url="http://127.0.0.1:8001")
    args = provider._build_generation_args(_Req(temperature=0.9, max_tokens=32))  # type: ignore[arg-type]

    assert args["top_p"] == 0.8
    assert args["top_k"] == 20
    assert args["temperature"] == 0.9
    assert args["max_tokens"] == 32
    stops = cast(List[str], args["stop"])  # type: ignore[arg-type]
    assert {"<|stop|>", "<|end|>"}.issubset(set(stops))
    assert len(stops) == len(set(stops))
