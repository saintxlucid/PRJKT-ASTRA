"""
ASTRA Gateway Client Example
=============================

Example OpenAI-compatible client with identity system integration.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from typing import Any

from ..core.identity.role_context import role_scope
from .provider_hook import ProviderHook


class OpenAICompatClient:
    """OpenAI-compatible client with ASTRA identity system."""

    def __init__(self, provider: str = "vllm", base_url: str = "http://localhost:8000"):
        """
        Initialize client.

        Args:
            provider: Provider type ("vllm", "openai", "llamacpp")
            base_url: Base URL for API
        """
        self.provider = provider
        self.base_url = base_url
        self.hook = ProviderHook(provider)

    def chat(
        self,
        messages: list[dict[str, Any]],
        role: str | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """
        Chat completion with role injection.

        Args:
            messages: Chat messages
            role: Override role (None = use current)
            **kwargs: Additional API parameters

        Returns:
            Chat completion response

        Examples:
            >>> client = OpenAICompatClient()
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> response = client.chat(messages, role="angel")
        """
        # Check for activation phrase in last message
        if messages and messages[-1]["role"] == "user":
            detected_role = self.hook.maybe_activate_from_user_text(
                messages[-1]["content"]
            )
            if detected_role:
                role = detected_role

        # Prepare messages with role injection
        prepared = self.hook.prepare_messages(messages, role_name=role)

        # TODO: Actual API call implementation
        # For now, return placeholder response
        return {
            "id": "chat-placeholder",
            "model": self.provider,
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"Response with role: {role or 'ASTRA'}"
                }
            }],
            "prepared_messages": prepared  # Debug info
        }


__all__ = ["OpenAICompatClient"]
