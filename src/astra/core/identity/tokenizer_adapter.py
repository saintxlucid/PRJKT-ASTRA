"""
ASTRA Tokenizer Adapters
=========================

Provider-specific role token injection.

Supported providers:
- OpenAI/vLLM: System message injection
- llama.cpp: Inline first-turn injection

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from typing import Any


class TokenizerAdapter:
    """Adapter for provider-specific role injection."""

    def __init__(self, provider: str = "vllm"):
        """
        Initialize adapter.

        Args:
            provider: Provider type ("vllm", "openai", "llamacpp")
        """
        self.provider = provider.lower()

    def inject_role(
        self,
        messages: list[dict[str, Any]],
        role_token: str
    ) -> list[dict[str, Any]]:
        """
        Inject role token into messages.

        Args:
            messages: Chat message list
            role_token: Role token (e.g., "<|start|>angel")

        Returns:
            Modified message list

        Examples:
            >>> adapter = TokenizerAdapter("vllm")
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> adapter.inject_role(messages, "<|start|>angel")
            [{"role": "system", "content": "<|start|>angel"}, {"role": "user", "content": "Hello"}]
        """
        if self.provider in ("vllm", "openai"):
            # System message prefix
            return self._inject_system(messages, role_token)
        elif self.provider == "llamacpp":
            # Inline first-turn injection
            return self._inject_inline(messages, role_token)
        else:
            # Unknown provider: default to system message
            return self._inject_system(messages, role_token)

    def _inject_system(
        self,
        messages: list[dict[str, Any]],
        role_token: str
    ) -> list[dict[str, Any]]:
        """Inject as system message."""
        system_msg = {"role": "system", "content": role_token}
        return [system_msg] + messages

    def _inject_inline(
        self,
        messages: list[dict[str, Any]],
        role_token: str
    ) -> list[dict[str, Any]]:
        """Inject inline in first user message."""
        if messages and messages[0].get("role") == "user":
            messages[0]["content"] = f"{role_token}\n\n{messages[0]['content']}"
        return messages


__all__ = ["TokenizerAdapter"]
