"""Static validation for CHAT OS plans."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from chat_os.plan import Plan, PlanStep


class PlanValidationError(RuntimeError):
    """Raised when a plan fails static checks."""


@dataclass(slots=True)
class CheckerConfig:
    """Policy and budget configuration for static checks."""

    allowed_policies: tuple[str, ...] = ("info", "action", "admin")
    max_time_ms: int = 60000
    max_tokens_per_extract: int = 1200
    max_paginate_pages: int = 6
    allow_network_channels: tuple[str, ...] = ("telegram", "mailto", "slack")


KNOWN_INTENTS: set[str] = {
    "browser.navigate",
    "browser.extract_markdown",
    "browser.query",
    "browser.click",
    "browser.type",
    "compose.document",
    "compose.summarize",
    "compose.rewrite",
    "memory.save",
    "memory.get",
    "memory.search",
    "memory.delete",
    "notify.push",
    "approval.request",
    "observe.context",
    "os.window.focus",
    "os.window.tile",
    # Test intents for integration testing
    "test.echo",
    "test.increment",
}


def _validate_policy(plan: Plan, config: CheckerConfig) -> None:
    if plan.meta.policy not in config.allowed_policies:
        raise PlanValidationError(
            f"Policy '{plan.meta.policy}' not in allowed set {config.allowed_policies}"
        )

    if plan.meta.max_time_ms > config.max_time_ms:
        raise PlanValidationError(
            f"Plan max_time_ms {plan.meta.max_time_ms} exceeds limit {config.max_time_ms}"
        )


def _check_known_intents(steps: Iterable[PlanStep]) -> None:
    for step in steps:
        if step.intent not in KNOWN_INTENTS:
            raise PlanValidationError(f"Unknown intent '{step.intent}' in plan")


def _check_step_args(plan: Plan, config: CheckerConfig) -> None:
    for step in plan.steps:
        args = step.args
        if step.intent == "browser.extract_markdown":
            max_tokens = int(args.get("max_tokens", config.max_tokens_per_extract))
            if max_tokens > config.max_tokens_per_extract:
                raise PlanValidationError(
                    f"browser.extract_markdown max_tokens {max_tokens} exceeds {config.max_tokens_per_extract}"
                )
            if args.get("paginate"):
                pages = int(args.get("max_pages", config.max_paginate_pages))
                if pages > config.max_paginate_pages:
                    raise PlanValidationError(
                        f"browser.extract_markdown paginate pages {pages} exceeds {config.max_paginate_pages}"
                    )

        if step.intent == "memory.save":
            path = args.get("path", "")
            if not isinstance(path, str) or not path.startswith("/"):
                raise PlanValidationError("memory.save path must be absolute within memory FS (starts with '/')")

        if step.intent == "notify.push":
            channel = args.get("channel", "console")
            if not isinstance(channel, str):
                raise PlanValidationError("notify.push channel must be a string")
            
            # Allow local channels without ://, require scheme for network channels
            if "://" in channel:
                scheme = channel.split(":", 1)[0]
                if scheme not in config.allow_network_channels and scheme not in ("console", "system", "webhook"):
                    raise PlanValidationError(
                        f"notify.push scheme '{scheme}' not allowed (allowed {config.allow_network_channels})"
                    )

        if step.intent == "approval.request":
            summary = args.get("summary")
            if not summary:
                raise PlanValidationError("approval.request requires a summary for operator review")


def validate_plan(plan: Plan, config: CheckerConfig | None = None) -> None:
    """Run static checks on a plan."""
    config = config or CheckerConfig()
    _validate_policy(plan, config)
    _check_known_intents(plan.steps)
    _check_step_args(plan, config)
