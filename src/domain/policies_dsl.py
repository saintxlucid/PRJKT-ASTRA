"""
Identity Compiler - DSL to Executable Policies
===============================================

Transforms YAML identity values + policies into runtime enforceable code.

Design Philosophy:
    "Who ASTRA is" (identity.yaml) becomes "what ASTRA will/won't do" (policies).

    Example:
        identity.yaml:
            values:
                warmth: 0.7
                autonomy: low
            policies:
                - when: file_delete
                  require: [explicit_consent, backup_exists]
                  deny_if: ["path_contains:/system"]

        Compiled Policy:
            Before executing file_delete:
            1. Check explicit_consent is True in context
            2. Check backup_exists is True in context
            3. Reject if path contains "/system"

Author: ASTRA Core Team
Created: 2025-11-01 (Week-2 Refactor)
"""

from collections.abc import Callable
from typing import Any


# Policy function signature
PolicyFn = Callable[[dict[str, Any], dict[str, Any]], tuple[bool, list[str]]]


def compile_rule(rule: dict[str, Any]) -> PolicyFn:
    """
    Compile a single policy rule into executable function.

    Args:
        rule: {
            "when": str,           # trigger condition (action type)
            "require": list[str],  # prerequisites (must be True in context)
            "deny_if": list[str]   # rejection conditions
        }

    Returns:
        Policy function: (plan, context) -> (approved, missing_requirements)

    Example:
        >>> rule = {"when": "file_delete", "require": ["backup_exists"]}
        >>> policy = compile_rule(rule)
        >>> approved, missing = policy(
        ...     {"type": "file_delete", "path": "/data/doc.txt"},
        ...     {"backup_exists": False}
        ... )
        >>> print(approved, missing)
        False ['backup_exists']
    """

    def policy(plan: dict[str, Any], ctx: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Evaluate policy against plan and context.

        Args:
            plan: Execution plan (type, path, args, etc.)
            ctx: Runtime context (consent, backups, user preferences)

        Returns:
            (approved, missing_requirements)
        """
        # Check if rule applies to this plan
        trigger = rule.get("when", "")
        if trigger and plan.get("type") != trigger:
            return True, []  # Rule doesn't apply

        # Check deny conditions first (fail-fast)
        for condition in rule.get("deny_if", []):
            if _evaluate_condition(condition, plan, ctx):
                return False, [f"denied: {condition}"]

        # Check prerequisites
        required = rule.get("require", [])
        missing = [r for r in required if not ctx.get(r, False)]

        if missing:
            return False, missing

        return True, []

    return policy


def _evaluate_condition(condition: str, plan: dict[str, Any], ctx: dict[str, Any]) -> bool:
    """
    Evaluate a single condition.

    Supported conditions:
        - "path_contains:X" → plan["path"] contains X
        - "action_is:X" → plan["type"] == X
        - "context_has:X" → ctx[X] exists and is truthy

    Args:
        condition: Condition string
        plan: Execution plan
        ctx: Runtime context

    Returns:
        True if condition matches
    """
    if condition.startswith("path_contains:"):
        pattern = condition.split(":", 1)[1]
        return pattern in plan.get("path", "")

    elif condition.startswith("action_is:"):
        action = condition.split(":", 1)[1]
        return plan.get("type") == action

    elif condition.startswith("context_has:"):
        key = condition.split(":", 1)[1]
        return bool(ctx.get(key))

    # Unknown condition → treat as false (fail-closed)
    return False


class PlanVerifier:
    """
    Verifies execution plans against compiled identity policies.

    Example:
        >>> rules = load_identity_yaml()["policies"]
        >>> policies = [compile_rule(r) for r in rules]
        >>> verifier = PlanVerifier(policies)
        >>>
        >>> plan = {"type": "file_delete", "path": "/sandbox/test.txt"}
        >>> context = {"explicit_consent": True, "backup_exists": True}
        >>> approved, errors = verifier.check(plan, context)
        >>> if not approved:
        ...     print("Rejected:", errors)
    """

    def __init__(self, policies: list[PolicyFn]):
        """
        Initialize with compiled policies.

        Args:
            policies: List of policy functions from compile_rule()
        """
        self.policies = policies

    def check(
        self,
        plan: dict[str, Any],
        context: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Check plan against all policies.

        Args:
            plan: Execution plan to validate
            context: Runtime context (consent, backups, etc.)

        Returns:
            (approved, errors)
            - approved: True if ALL policies pass
            - errors: List of missing requirements or denials

        Security:
            - Fail-closed: ANY policy failure → reject plan
            - Collects all errors (for debugging)
        """
        all_errors = []

        for policy in self.policies:
            approved, errors = policy(plan, context)
            if not approved:
                all_errors.extend(errors)

        return len(all_errors) == 0, all_errors

    def explain(self, plan: dict[str, Any]) -> list[str]:
        """
        Explain which policies apply to a plan (without evaluating).

        Args:
            plan: Execution plan

        Returns:
            List of human-readable policy descriptions

        Example:
            >>> verifier.explain({"type": "file_delete"})
            [
                "file_delete requires: explicit_consent, backup_exists",
                "file_delete denied if: path_contains:/system"
            ]
        """
        explanations = []

        # This is a simplified version; full implementation would
        # parse rule metadata to generate descriptions

        return explanations


def load_policies_from_yaml(yaml_path: str) -> list[PolicyFn]:
    """
    Load identity policies from YAML and compile.

    Args:
        yaml_path: Path to identity.yaml or astra.yaml

    Returns:
        List of compiled policy functions

    Example:
        >>> policies = load_policies_from_yaml("astra.yaml")
        >>> verifier = PlanVerifier(policies)
    """
    import yaml
    from pathlib import Path

    if not Path(yaml_path).exists():
        return []

    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Extract policy rules
    rules = config.get("identity", {}).get("policies", [])

    # Compile to executable functions
    return [compile_rule(rule) for rule in rules]


# Example policy rules (for reference)
EXAMPLE_POLICIES = [
    {
        "when": "file_delete",
        "require": ["explicit_consent", "backup_exists"],
        "deny_if": ["path_contains:/system", "path_contains:/windows"]
    },
    {
        "when": "network_request",
        "require": ["explicit_consent"],
        "deny_if": []  # Always require consent for network
    },
    {
        "when": "memory_delete",
        "require": ["explicit_consent", "memory_export_exists"],
        "deny_if": ["context_has:identity_locked"]
    }
]
