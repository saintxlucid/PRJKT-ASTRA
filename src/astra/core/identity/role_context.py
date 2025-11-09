"""
ASTRA Role Context Management
==============================

Thread-safe role tracking using Python contextvars.

Features:
- get_current_role(): Retrieve active role
- role_scope(): Context manager for role switching
- apply_role_to_messages(): Inject role tokens
- parse_activation_phrase(): Parse console invocations

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Any, Iterator

from .astra_roles import Role, resolve_role, role_token


# Thread-local role context (default: ASTRA)
_current_role: ContextVar[str] = ContextVar("current_role", default="ASTRA")


def get_current_role() -> str:
    """
    Get currently active role.

    Returns:
        Role name (canonical)

    Examples:
        >>> get_current_role()
        'ASTRA'
    """
    return _current_role.get()


@contextmanager
def role_scope(role_name: str) -> Iterator[None]:
    """
    Context manager for temporary role switching.

    Args:
        role_name: Target role (will be resolved)

    Yields:
        None

    Examples:
        >>> with role_scope("angel"):
        ...     print(get_current_role())
        angel
    """
    canonical = resolve_role(role_name)
    token = _current_role.set(canonical)
    try:
        yield
    finally:
        _current_role.reset(token)


def apply_role_to_messages(
    messages: list[dict[str, Any]],
    role_name: str | None = None,
    provider: str = "vllm"
) -> list[dict[str, Any]]:
    """
    Inject role token into message list.

    Args:
        messages: Chat messages
        role_name: Override role (None = use current)
        provider: LLM provider ("vllm", "openai", "llamacpp")

    Returns:
        Modified message list

    Examples:
        >>> messages = [{"role": "user", "content": "Hello"}]
        >>> apply_role_to_messages(messages, "angel")
        [{"role": "system", "content": "<|start|>angel"}, {"role": "user", "content": "Hello"}]
    """
    active_role = role_name if role_name else get_current_role()
    token = role_token(active_role)

    # Provider-specific injection
    if provider in ("vllm", "openai"):
        # System message injection
        system_msg = {"role": "system", "content": token}
        return [system_msg] + messages
    elif provider == "llamacpp":
        # Inline first-turn injection
        if messages and messages[0]["role"] == "user":
            messages[0]["content"] = f"{token}\n\n{messages[0]['content']}"
        return messages
    else:
        # Unknown provider: prepend as system message
        return [{"role": "system", "content": token}] + messages


# Activation phrase regex
_ACTIVATION_REGEX = re.compile(
    r"I\s+invoke.*?Role:\s*(?P<token><\|start\|>[a-zA-Z_]+)",
    re.IGNORECASE
)


def parse_activation_phrase(text: str) -> str | None:
    """
    Parse activation phrase from user input.

    Args:
        text: User message

    Returns:
        Role name if found, None otherwise

    Examples:
        >>> parse_activation_phrase("I invoke the Angelic Layer of ASTRA — Role: <|start|>angel")
        'angel'
        >>> parse_activation_phrase("Hello ASTRA")
        None
    """
    match = _ACTIVATION_REGEX.search(text)
    if not match:
        return None

    token = match.group("token")
    # Extract role name from token (e.g., "<|start|>angel" -> "angel")
    role_name = token.split(">", 1)[1] if ">" in token else None
    return role_name


__all__ = [
    "get_current_role",
    "role_scope",
    "apply_role_to_messages",
    "parse_activation_phrase",
]
