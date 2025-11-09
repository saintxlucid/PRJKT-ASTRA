"""Plan schema and loader for CHAT OS deterministic plans."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class PlanMeta:
    """Metadata for a deterministic plan."""

    id: str
    policy: str
    max_time_ms: int


@dataclass(slots=True)
class PlanStep:
    """One typed step in a plan."""

    intent: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Plan:
    """Loaded plan with metadata and ordered steps."""

    version: str
    meta: PlanMeta
    steps: list[PlanStep]


class PlanLoadError(RuntimeError):
    """Raised when a plan file is malformed."""


SUPPORTED_VERSION = "0.3"


def _normalise_step(raw_step: dict[str, Any]) -> PlanStep:
    if len(raw_step) != 1:
        raise PlanLoadError(f"Step must contain exactly one intent, got: {raw_step}")

    intent, args = next(iter(raw_step.items()))
    if args is None:
        args = {}
    elif not isinstance(args, dict):
        raise PlanLoadError(f"Step args for '{intent}' must be a mapping")

    return PlanStep(intent=intent, args=args)


def load_plan(path: str | Path) -> Plan:
    """Load and parse a YAML plan file."""
    plan_path = Path(path)
    if not plan_path.exists():
        raise PlanLoadError(f"Plan file not found: {plan_path}")

    with plan_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise PlanLoadError("Plan file must contain a mapping at the top level")

    version = str(data.get("version", "")).strip()
    if version != SUPPORTED_VERSION:
        raise PlanLoadError(f"Unsupported plan version '{version}', expected '{SUPPORTED_VERSION}'")

    meta_raw = data.get("meta")
    if not isinstance(meta_raw, dict):
        raise PlanLoadError("Plan meta section missing or invalid")

    try:
        meta = PlanMeta(
            id=str(meta_raw["id"]),
            policy=str(meta_raw["policy"]),
            max_time_ms=int(meta_raw["max_time_ms"]),
        )
    except KeyError as exc:
        raise PlanLoadError(f"Plan meta missing field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise PlanLoadError(f"Invalid plan meta values: {exc}") from exc

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PlanLoadError("Plan must define a non-empty 'steps' list")

    steps = [_normalise_step(step) for step in raw_steps]

    return Plan(version=version, meta=meta, steps=steps)
