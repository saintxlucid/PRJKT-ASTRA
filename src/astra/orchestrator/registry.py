"""
ASTRA Orchestrator Registry.
Handles action registration and deterministic execution.
"""
import functools
import json
import time
import uuid
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()

_REGISTRY: dict[str, dict] = {}
_DRY_RUN_PLANS: dict[str, List[Dict[str, Any]]] = {}

def action(name: str, timeout_s: int = 10, deterministic: bool = False):
    """Decorator for registering an action with the orchestrator.
    
    Args:
        name: Unique identifier for the action
        timeout_s: Maximum execution time allowed (for monitoring)
        deterministic: Whether the action is deterministic (same inputs = same outputs)
    
    Example:
        @action("multi_rag.retrieval", timeout_s=8)
        def retrieve(query: str, k: int = 12):
            ...
    """
    def wrap(fn):
        _REGISTRY[name] = {
            "fn": fn,
            "timeout": timeout_s,
            "deterministic": deterministic,
        }
        @functools.wraps(fn)
        def runner(*args, **kwargs):
            # Check for dry run context
            dry_run_id = kwargs.pop("_dry_run_id", None)
            if dry_run_id:
                # Record the action plan without executing
                _DRY_RUN_PLANS.setdefault(dry_run_id, []).append({
                    "name": name,
                    "args": args,
                    "kwargs": kwargs,
                    "deterministic": deterministic
                })
                return {
                    "ok": True,
                    "name": name,
                    "dry_run": True,
                    "plan_id": dry_run_id
                }
            
            # Normal execution
            start = time.time()
            try:
                out = fn(*args, **kwargs)
                duration_ms = int((time.time() - start) * 1000)
                logger.info(
                    "action_complete",
                    name=name,
                    latency_ms=duration_ms
                )
                return {
                    "ok": True,
                    "name": name,
                    "latency_ms": duration_ms,
                    "result": out,
                }
            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                logger.error(
                    "action_failed",
                    name=name,
                    error=str(e),
                    latency_ms=duration_ms
                )
                return {
                    "ok": False,
                    "name": name,
                    "error": repr(e),
                    "latency_ms": duration_ms,
                }
        return runner
    return wrap

def get_action(name: str):
    """Get a registered action by name."""
    if name not in _REGISTRY:
        raise KeyError(f"Action {name} not found in registry")
    return _REGISTRY[name]["fn"]

def list_actions() -> list[str]:
    """List all registered action names."""
    return sorted(_REGISTRY.keys())

def get_action_timeout(name: str) -> int:
    """Get the timeout setting for an action."""
    if name not in _REGISTRY:
        raise KeyError(f"Action {name} not found in registry")
    return _REGISTRY[name]["timeout"]

def start_dry_run() -> str:
    """Start a new dry run session.
    
    Returns:
        str: Unique ID for the dry run session
    """
    plan_id = str(uuid.uuid4())
    _DRY_RUN_PLANS[plan_id] = []
    return plan_id

def get_dry_run_plan(plan_id: str) -> List[Dict[str, Any]]:
    """Get the recorded action plan for a dry run session.
    
    Args:
        plan_id: Unique ID for the dry run session
        
    Returns:
        List of planned actions with their arguments
    """
    if plan_id not in _DRY_RUN_PLANS:
        raise KeyError(f"No dry run plan found with ID {plan_id}")
    return _DRY_RUN_PLANS[plan_id]

def clear_dry_run(plan_id: str) -> None:
    """Clear a dry run session and its recorded plan.
    
    Args:
        plan_id: Unique ID for the dry run session to clear
    """
    if plan_id in _DRY_RUN_PLANS:
        del _DRY_RUN_PLANS[plan_id]