"""
ASTRA Provider Hook
===================

LLM provider integration with role injection.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from typing import Any

from ..core.identity.role_context import (
    apply_role_to_messages,
    parse_activation_phrase,
)
from ..core.identity.tokenizer_adapter import TokenizerAdapter


class ProviderHook:
    """Hook for LLM providers with role injection."""

    def __init__(self, provider: str = "vllm"):
        """
        Initialize provider hook.

        Args:
            provider: LLM provider ("vllm", "openai", "llamacpp")
        """
        self.adapter = TokenizerAdapter(provider)

    def prepare_messages(
        self,
        messages: list[dict[str, Any]],
        role_name: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Prepare messages with role injection.

        Args:
            messages: Chat messages
            role_name: Override role (None = use current)

        Returns:
            Modified messages with role token

        Examples:
            >>> hook = ProviderHook("vllm")
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> hook.prepare_messages(messages, "angel")
            [{"role": "system", "content": "<|start|>angel"}, {"role": "user", "content": "Hello"}]
        """
        return apply_role_to_messages(
            messages,
            role_name=role_name,
            provider=self.adapter.provider
        )

    def maybe_activate_from_user_text(self, text: str) -> str | None:
        """
        Parse activation phrase from user input.

        Args:
            text: User message

        Returns:
            Role name if activation phrase found, None otherwise

        Examples:
            >>> hook = ProviderHook()
            >>> hook.maybe_activate_from_user_text("I invoke the Angelic Layer — Role: <|start|>angel")
            'angel'
        """
        return parse_activation_phrase(text)


__all__ = ["ProviderHook"]
