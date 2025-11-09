"""Execute validated CHAT OS plans step-by-step with cognitive fusion."""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from chat_os.cognitive.lucid_protocol import LucidWeights
from chat_os.cognitive.macro_mining import ExecutionTrace, MacroMiner
from chat_os.cognitive.meta_controller import (
    CognitiveGovernor,
    MetaController,
    ReasoningMode,
    RiskLevel,
    Task,
)
from chat_os.plan import Plan, PlanStep
from chat_os.plan_checker import CheckerConfig, validate_plan
from chat_os.telemetry import TelemetryCollector, record_task_telemetry


class ExecutionError(RuntimeError):
    """Raised when plan execution fails."""


@dataclass(slots=True)
class StepResult:
    """Result of a single plan step."""

    step_index: int
    intent: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


def _load_lucid_config() -> tuple[LucidWeights, dict[str, Any]]:
    """Load Lucid Protocol configuration."""
    config_path = Path(__file__).parent.parent / "configs" / "lucid.yaml"
    if not config_path.exists():
        # Defaults
        return (
            LucidWeights(
                truth_compassion=0.5,
                logic_intuition=0.4,
                order_freedom=0.4,
                efficiency_safety=0.6,
            ),
            {
                "prefer_procedural": False,
                "min_macro_confidence": 0.85,
                "budget_per_task_ms": 5000,
            },
        )
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    weights = LucidWeights(**config.get("weights", {}))
    meta_config = config.get("meta_controller", {})
    
    return weights, meta_config


@dataclass(slots=True)
class ExecutionContext:
    """Runtime state for plan execution with cognitive fusion."""

    plan: Plan
    results: list[StepResult] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    start_time_ms: float = field(default_factory=lambda: time.time() * 1000)
    abort_flag: bool = False

    # Cognitive components
    meta_controller: MetaController | None = field(default=None, init=False)
    governor: CognitiveGovernor | None = field(default=None, init=False)
    lucid_weights: LucidWeights | None = field(default=None, init=False)
    macro_miner: MacroMiner | None = field(default=None, init=False)

    # Trace collection for macro learning
    execution_traces: list[ExecutionTrace] = field(default_factory=list, init=False)

    # Telemetry collection for refinement
    telemetry: TelemetryCollector = field(default_factory=TelemetryCollector, init=False)
    
    # Phase 10: TranscendentOS integration
    transcendent_os: Any = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Initialize Phase 10 TranscendentOS - Unified Cognitive System."""
        try:
            # Initialize TranscendentOS - Phase 10 Unified System
            from chat_os.cognitive.transcendent_os import (
                get_transcendent_os,
                CognitiveMode,
            )
            
            self.transcendent_os = get_transcendent_os()
            
            # Set proactive mode for plan execution (balances speed and quality)
            self.transcendent_os.set_cognitive_mode(CognitiveMode.PROACTIVE)
            
            # Legacy components (kept for backward compatibility)
            self.lucid_weights, meta_config = _load_lucid_config()
            
            # Initialize emotion engine for adaptive routing (Phase 2C)
            from chat_os.cognitive.emotion.context_engine import EmotionalContextEngine
            emotion_engine = EmotionalContextEngine()
            
            # Initialize governor with emotion awareness
            self.governor = CognitiveGovernor(
                lucid_weights={
                    "truth_compassion": self.lucid_weights.truth_compassion,
                    "logic_intuition": self.lucid_weights.logic_intuition,
                    "order_freedom": self.lucid_weights.order_freedom,
                    "efficiency_safety": self.lucid_weights.efficiency_safety,
                },
                emotion_engine=emotion_engine,
            )
            
            # Placeholder engines (will be replaced with actual implementations)
            from chat_os.cognitive.meta_controller import (
                ProceduralEngine,
                StatisticalEngine,
                SymbolicEngine,
            )
            symbolic = SymbolicEngine()
            statistical = StatisticalEngine(self.governor)
            procedural = ProceduralEngine()

            self.meta_controller = MetaController(
                governor=self.governor,
                symbolic=symbolic,
                statistical=statistical,
                procedural=procedural,
            )

            # Initialize macro miner for trace collection
            self.macro_miner = MacroMiner(
                min_confidence=meta_config.get("min_macro_confidence", 0.85),
                min_occurrences=3,
            )
        except Exception as e:
            # Graceful degradation if cognitive system unavailable
            self.transcendent_os = None
            self.meta_controller = None
            self.governor = None
            self.lucid_weights = None
            self.macro_miner = None

    @property
    def elapsed_ms(self) -> float:
        return (time.time() * 1000) - self.start_time_ms

    def abort(self, reason: str) -> None:
        """Signal abort and record reason."""
        self.abort_flag = True
        self.variables["abort_reason"] = reason

    def _step_to_task(self, step: PlanStep) -> Task:
        """Convert a PlanStep to a Task for meta-controller routing."""
        # Extract risk indicators from intent and args
        intent_lower = step.intent.lower()
        args_str = str(step.args).lower()

        # Determine determinism
        deterministic = "query" in intent_lower or "get" in intent_lower or "read" in intent_lower

        # Determine risk level
        high_risk_keywords = ["delete", "remove", "drop", "truncate", "uninstall", "rm", "format"]
        medium_risk_keywords = ["update", "modify", "rename", "move", "deploy", "publish"]

        if any(kw in intent_lower or kw in args_str for kw in high_risk_keywords):
            risk = RiskLevel.HIGH
        elif any(kw in intent_lower or kw in args_str for kw in medium_risk_keywords):
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        return Task(
            name=step.intent,
            deterministic=deterministic,
            risk=risk,
            kind="plan_step",
            payload=step.args,
        )


# Intent handler registry
IntentHandler = Callable[[PlanStep, ExecutionContext], Any]
_INTENT_HANDLERS: dict[str, IntentHandler] = {}


def register_intent(intent: str) -> Callable[[IntentHandler], IntentHandler]:
    """Decorator to register an intent handler."""

    def decorator(func: IntentHandler) -> IntentHandler:
        _INTENT_HANDLERS[intent] = func
        return func

    return decorator


def _resolve_variable(value: Any, ctx: ExecutionContext) -> Any:
    """Resolve {{variable}} references in step arguments."""
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        var_name = value[2:-2].strip()
        if var_name not in ctx.variables:
            raise ExecutionError(f"Undefined variable: {var_name}")
        return ctx.variables[var_name]
    if isinstance(value, dict):
        return {k: _resolve_variable(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_variable(item, ctx) for item in value]
    return value


def _execute_step(step: PlanStep, step_index: int, ctx: ExecutionContext) -> StepResult:
    """Execute a single plan step with cognitive routing."""
    start = time.time() * 1000

    if step.intent not in _INTENT_HANDLERS:
        return StepResult(
            step_index=step_index,
            intent=step.intent,
            success=False,
            error=f"No handler registered for intent '{step.intent}'",
            duration_ms=0.0,
        )

    try:
        # Resolve variable references in args
        resolved_args = _resolve_variable(step.args, ctx)
        step_with_resolved = PlanStep(intent=step.intent, args=resolved_args)

        # Route through meta-controller with emotion-aware adaptation (Phase 2C)
        reasoning_mode = "UNKNOWN"
        if ctx.meta_controller is not None:
            task = ctx._step_to_task(step_with_resolved)
            # MetaController.route() now adjusts for operator emotional state
            mode = ctx.meta_controller.route(task)
            reasoning_mode = mode.name
            ctx.variables[f"step.{step_index}.mode"] = mode.name

        handler = _INTENT_HANDLERS[step.intent]
        output = handler(step_with_resolved, ctx)

        # Store output as indexed variable
        ctx.variables[f"step.{step_index}"] = output

        duration = (time.time() * 1000) - start

        # Record execution trace for successful steps
        if ctx.macro_miner is not None:
            trace = ExecutionTrace(
                task_name=step.intent,
                steps=[{"intent": step.intent, "args": resolved_args}],
                duration_ms=duration,
                mode=reasoning_mode,
                success=True,
                metadata={
                    "step_index": step_index,
                    "output_summary": str(output)[:200] if output else "",
                },
            )
            ctx.execution_traces.append(trace)

        # Record telemetry for successful execution
        used_macro = reasoning_mode == "PROCEDURAL"
        ctx.telemetry.record_task(
            mode=reasoning_mode,
            latency_ms=duration,
            success=True,
            used_macro=used_macro,
        )

        return StepResult(
            step_index=step_index,
            intent=step.intent,
            success=True,
            output=output,
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() * 1000) - start

        # Record telemetry for failed execution
        if ctx.meta_controller:
            mode_name = ctx.variables.get(f"step.{step_index}.mode", "UNKNOWN")
            ctx.telemetry.record_task(mode=mode_name, latency_ms=duration, success=False)

        return StepResult(
            step_index=step_index,
            intent=step.intent,
            success=False,
            error=str(e),
            duration_ms=duration,
        )


def execute_plan(
    plan: Plan,
    checker_config: CheckerConfig | None = None,
    initial_variables: dict[str, Any] | None = None,
) -> ExecutionContext:
    """Execute a validated plan and return execution context with trace collection."""
    # Static validation first
    validate_plan(plan, checker_config)

    ctx = ExecutionContext(plan=plan, variables=initial_variables or {})

    for step_index, step in enumerate(plan.steps):
        # Check timeout
        if ctx.elapsed_ms > plan.meta.max_time_ms:
            ctx.abort(f"Plan timeout exceeded {plan.meta.max_time_ms}ms")
            break

        # Check abort flag
        if ctx.abort_flag:
            break

        # Execute step
        result = _execute_step(step, step_index, ctx)
        ctx.results.append(result)

        # Abort on failure if policy is strict
        if not result.success and plan.meta.policy == "admin":
            ctx.abort(f"Step {step_index} ('{step.intent}') failed in admin policy")
            break

    # Run macro mining on collected traces after plan completion
    if ctx.macro_miner is not None and len(ctx.execution_traces) > 0:
        try:
            # Ingest all collected traces
            for trace in ctx.execution_traces:
                ctx.macro_miner.ingest_trace(trace)

            # Mine macros from ingested traces
            learned_macros = ctx.macro_miner.mine_macros()
            ctx.variables["learned_macros"] = learned_macros
            ctx.variables["learned_macros_count"] = len(learned_macros)
        except Exception as e:
            # Don't fail plan execution if macro mining fails
            ctx.variables["macro_mining_error"] = str(e)

    # Capture telemetry snapshot for refinement analysis
    telemetry_snapshot = ctx.telemetry.snapshot()
    ctx.variables["telemetry_snapshot"] = telemetry_snapshot

    return ctx


# Stub intent handlers for known intents
@register_intent("observe.context")
def _handle_observe_context(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Capture current context variables."""
    return {"variables": dict(ctx.variables), "elapsed_ms": ctx.elapsed_ms}


@register_intent("memory.save")
def _handle_memory_save(step: PlanStep, ctx: ExecutionContext) -> str:
    """Placeholder: save to memory FS."""
    path = step.args.get("path", "")
    content = step.args.get("content", "")
    # TODO: integrate with agent_kernel/memory.py
    ctx.variables[f"memory:{path}"] = content
    return str(path)


@register_intent("memory.get")
def _handle_memory_get(step: PlanStep, ctx: ExecutionContext) -> Any:
    """Placeholder: retrieve from memory FS."""
    path = step.args.get("path", "")
    # TODO: integrate with agent_kernel/memory.py
    return ctx.variables.get(f"memory:{path}", None)


@register_intent("approval.request")
def _handle_approval_request(step: PlanStep, ctx: ExecutionContext) -> bool:
    """Placeholder: request operator approval."""
    summary = step.args.get("summary", "")
    # TODO: integrate consent UI and token issuance
    # For now, auto-approve in test mode
    ctx.variables["last_approval_summary"] = summary
    return True
