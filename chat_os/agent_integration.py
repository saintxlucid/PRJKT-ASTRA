"""Integration layer between CHAT OS executor and ASTRA agent kernel."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chat_os.executor import execute_plan
from chat_os.plan import Plan
from chat_os.plan_checker import CheckerConfig

if TYPE_CHECKING:
    from agent_kernel.tools import ToolRegistry


def tool_execute_plan(args: dict[str, Any]) -> dict[str, Any]:
    """
    Tool handler for executing CHAT OS plans.

    Expected args:
        - plan: Plan dict or Plan object
        - variables: Optional dict of initial variables
        - timeout_ms: Optional execution timeout (default: 60000)
        - admin_mode: Optional bool to skip validation (default: False)

    Returns:
        Dict with keys: ok, result/error, steps, elapsed_ms
    """
    try:
        # Extract arguments
        plan_data = args.get("plan")
        if not plan_data:
            return {"ok": False, "error": "Missing 'plan' argument"}

        # Convert dict to Plan if needed
        if isinstance(plan_data, dict):
            # Transform dict structure to match Plan dataclass
            from chat_os.plan import PlanMeta, PlanStep

            meta_data = plan_data.get("meta", {})
            plan_meta = PlanMeta(
                id=plan_data.get("id", "unknown"),
                policy=meta_data.get("policy", "action"),
                max_time_ms=meta_data.get("max_time_ms", 60000),
            )

            steps_data = plan_data.get("steps", [])
            plan_steps = [
                PlanStep(intent=s["intent"], args=s.get("args", {}))
                for s in steps_data
            ]

            plan = Plan(
                version=plan_data.get("version", "0.3"),
                meta=plan_meta,
                steps=plan_steps,
            )
        elif isinstance(plan_data, Plan):
            plan = plan_data
        else:
            return {"ok": False, "error": f"Invalid plan type: {type(plan_data)}"}

        # Extract optional parameters
        initial_variables = args.get("variables", {})
        admin_mode = args.get("admin_mode", False)

        # Configure checker (use restricted policies unless admin mode)
        checker_config = CheckerConfig(
            allowed_policies=("info", "action", "admin") if admin_mode else ("info", "action"),
        )

        # Execute plan (timeout is in plan.meta.max_time_ms)
        ctx = execute_plan(
            plan=plan,
            checker_config=checker_config,
            initial_variables=initial_variables,
        )

        # Check if execution completed successfully
        if ctx.abort_flag:
            return {
                "ok": False,
                "error": ctx.variables.get("abort_reason", "Execution aborted"),
                "steps": [
                    {
                        "intent": r.intent,
                        "success": r.success,
                        "output": r.output,
                        "error": r.error,
                        "duration_ms": r.duration_ms,
                    }
                    for r in ctx.results
                ],
                "elapsed_ms": int(ctx.elapsed_ms),
            }

        # Check if any step failed
        failed_steps = [r for r in ctx.results if not r.success]
        if failed_steps:
            first_failure = failed_steps[0]
            return {
                "ok": False,
                "error": f"Step {first_failure.step_index} failed: {first_failure.error}",
                "steps": [
                    {
                        "intent": r.intent,
                        "success": r.success,
                        "output": r.output,
                        "error": r.error,
                        "duration_ms": r.duration_ms,
                    }
                    for r in ctx.results
                ],
                "elapsed_ms": int(ctx.elapsed_ms),
            }

        # Success: return aggregated results
        return {
            "ok": True,
            "result": {
                "steps_completed": len(ctx.results),
                "outputs": [r.output for r in ctx.results],
                "final_variables": ctx.variables,
            },
            "steps": [
                {
                    "intent": r.intent,
                    "success": r.success,
                    "output": r.output,
                    "duration_ms": r.duration_ms,
                }
                for r in ctx.results
            ],
            "elapsed_ms": int(ctx.elapsed_ms),
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Plan execution failed: {e}",
        }


def tool_load_plan_from_memory(args: dict[str, Any]) -> dict[str, Any]:
    """
    Tool handler for loading plans from memory.

    Expected args:
        - key: Memory key to load plan from (e.g., "plans.research_workflow")
        - memory: MemoryManager instance to read from

    Returns:
        Dict with keys: ok, result (Plan dict)/error
    """
    try:
        key = args.get("key")
        memory = args.get("memory")

        if not key:
            return {"ok": False, "error": "Missing 'key' argument"}
        if not memory:
            return {"ok": False, "error": "Missing 'memory' argument"}

        # Try to read from memory (check L0-L3 tiers)
        plan_data = None
        for tier in ["L0", "L1", "L2", "L3"]:
            plan_data = memory.read(key, tier=tier)
            if plan_data:
                break

        if not plan_data:
            return {
                "ok": False,
                "error": f"Plan not found in memory: {key}",
            }

        # Validate it's a dict with expected structure
        if not isinstance(plan_data, dict):
            return {
                "ok": False,
                "error": f"Invalid plan data (not a dict): {type(plan_data)}",
            }

        if "id" not in plan_data or "steps" not in plan_data:
            return {
                "ok": False,
                "error": "Plan missing required fields (id, steps)",
            }

        return {
            "ok": True,
            "result": plan_data,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to load plan from memory: {e}",
        }


def register_chat_os_tools(tool_registry: ToolRegistry) -> None:
    """
    Register CHAT OS tools with agent kernel tool registry.

    Args:
        tool_registry: ToolRegistry instance from agent_kernel.tools
    """
    from agent_kernel.tools import Tool

    # Register plan executor tool
    tool_registry.tools["plan.execute"] = Tool(
        name="plan.execute",
        func=tool_execute_plan,
        description="Execute a CHAT OS plan with steps (browser, compose, memory, approval, notify)",
        scope="action",
        policy="action",
        requires_token=True,
    )

    # Register plan loader tool (info scope - read-only)
    tool_registry.tools["plan.load"] = Tool(
        name="plan.load",
        func=tool_load_plan_from_memory,
        description="Load a saved plan from memory by key",
        scope="info",
        policy="info",
        requires_token=True,
    )
