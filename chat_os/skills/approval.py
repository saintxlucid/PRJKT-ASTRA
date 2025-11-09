"""
Approval workflow skill for CHAT OS.
Handles approval.request intent for human-in-the-loop workflows.
"""
from __future__ import annotations

import logging
from typing import Any

from chat_os.executor import ExecutionContext, register_intent
from chat_os.plan import PlanStep

logger = logging.getLogger(__name__)


@register_intent("approval.request")
def handle_approval_request(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Request human approval before proceeding.

    This is a critical safety mechanism for high-risk actions. The handler
    will pause execution and wait for explicit user consent.

    Args:
        step.args:
            - summary: Brief description of what needs approval
            - scope: What action/scope requires approval (e.g., "notify.push", "file.write")
            - reason: Optional detailed explanation
            - timeout_s: Optional timeout in seconds (default: 300)
            - auto_approve: Optional flag for testing (default: False)

    Returns:
        Dict with keys: ok, approved, scope, reason (if denied)
    """
    summary = step.args.get("summary", "")
    scope = step.args.get("scope", "unknown")
    reason = step.args.get("reason", "")
    timeout_s = int(step.args.get("timeout_s", 300))
    auto_approve = step.args.get("auto_approve", False)

    if not summary:
        return {"ok": False, "error": "Missing required arg: summary"}

    # For testing: auto-approve if flag set
    if auto_approve:
        logger.info(f"Auto-approved (testing): {summary} [scope: {scope}]")
        return {
            "ok": True,
            "approved": True,
            "scope": scope,
            "auto_approved": True,
        }

    try:
        # Check if we're in interactive mode
        if _is_interactive():
            # Terminal-based approval prompt
            approved = _prompt_terminal_approval(summary, scope, reason, timeout_s)
        else:
            # Non-interactive mode: Check for pre-approved scopes
            approved = _check_preapproved_scope(scope, ctx)

        if approved:
            logger.info(f"Approval granted: {summary} [scope: {scope}]")
            return {
                "ok": True,
                "approved": True,
                "scope": scope,
            }
        else:
            logger.warning(f"Approval denied: {summary} [scope: {scope}]")
            return {
                "ok": True,
                "approved": False,
                "scope": scope,
                "reason": "User denied approval",
            }

    except TimeoutError:
        logger.warning(f"Approval timeout: {summary} [scope: {scope}]")
        return {
            "ok": True,
            "approved": False,
            "scope": scope,
            "reason": f"Approval timeout after {timeout_s}s",
        }
    except Exception as e:
        logger.error(f"Approval request failed: {e}", exc_info=True)
        return {
            "ok": False,
            "error": f"Approval request failed: {e}",
            "scope": scope,
        }


def _is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    import sys

    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompt_terminal_approval(
    summary: str, scope: str, reason: str, timeout_s: int
) -> bool:
    """
    Prompt user for approval via terminal.

    Returns:
        True if approved, False if denied
    """
    # Display approval request
    print("\n" + "=" * 70)
    print("🔐 APPROVAL REQUIRED")
    print("=" * 70)
    print(f"Summary:  {summary}")
    print(f"Scope:    {scope}")
    if reason:
        print(f"Reason:   {reason}")
    print(f"Timeout:  {timeout_s}s")
    print("=" * 70)
    print()

    # Simple yes/no prompt
    try:
        response = input("Approve this action? (yes/no): ").strip().lower()
        return response in ("yes", "y")
    except (KeyboardInterrupt, EOFError):
        print("\n[Approval cancelled]")
        return False


def _check_preapproved_scope(scope: str, ctx: ExecutionContext) -> bool:
    """
    Check if scope is in pre-approved list.

    In non-interactive mode, certain scopes can be pre-approved based on
    the plan's policy level.
    """
    # Get plan policy from context
    policy = ctx.variables.get("_plan_policy", "user")

    # Pre-approved scopes by policy level
    preapproved = {
        "info": {
            "memory.get",
            "memory.search",
            "browser.navigate",
            "browser.extract_markdown",
        },
        "user": {
            "memory.save",
            "compose.document",
            "notify.push",
            "observe.context",
        },
        "admin": {
            "memory.delete",
            "os.window.focus",
            "os.window.tile",
        },
    }

    # Check if scope is pre-approved for this policy level
    for level in ["info", "user", "admin"]:
        if scope in preapproved.get(level, set()):
            if _policy_allows(policy, level):
                logger.info(
                    f"Scope '{scope}' pre-approved for policy '{policy}' (level: {level})"
                )
                return True

    # Not pre-approved
    logger.warning(f"Scope '{scope}' not pre-approved for policy '{policy}'")
    return False


def _policy_allows(current_policy: str, required_level: str) -> bool:
    """Check if current policy meets required level."""
    hierarchy = {"info": 0, "user": 1, "admin": 2}
    return hierarchy.get(current_policy, 0) >= hierarchy.get(required_level, 0)
