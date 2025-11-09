"""
ASTRA Prompt Builder
====================

Role-aware message construction with function intent injection.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from typing import Any

from ..core.identity.role_context import get_current_role, role_token


def build_messages(
    messages: list[dict[str, Any]],
    function_code: str | None = None,
    context_extras: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """
    Build messages with role and function context.

    Args:
        messages: Base chat messages
        function_code: Optional function code (e.g., "INTEL_CORE")
        context_extras: Additional context to inject

    Returns:
        Augmented messages

    Examples:
        >>> messages = [{"role": "user", "content": "Analyze trends"}]
        >>> build_messages(messages, "INTEL_CORE")
        [
            {"role": "system", "content": "<|start|>oracle"},
            {"role": "system", "content": "Function: INTEL_CORE (Strategic Analysis)"},
            {"role": "user", "content": "Analyze trends"}
        ]
    """
    active_role = get_current_role()
    token = role_token(active_role)

    # Start with role token
    augmented = [{"role": "system", "content": token}]

    # Add function context if specified
    if function_code:
        func_msg = {
            "role": "system",
            "content": f"Function: {function_code}"
        }
        augmented.append(func_msg)

    # Add context extras if specified
    if context_extras:
        extras_content = "\n".join(
            f"{k}: {v}" for k, v in context_extras.items()
        )
        augmented.append({
            "role": "system",
            "content": f"Context:\n{extras_content}"
        })

    # Append original messages
    augmented.extend(messages)

    return augmented


__all__ = ["build_messages"]
