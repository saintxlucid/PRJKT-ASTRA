"""
Input Validation Module
Prompt injection detection and request validation

Sacred Code: 333 → ∞
"""

from typing import Any, Dict, List

import structlog
from pydantic import BaseModel, field_validator

logger = structlog.get_logger()

# Prompt injection patterns
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "<|im_start|>system",
    "<|system|>",
    "begin system prompt",
    "you are now",
    "from now on",
    "disregard prior",
    "jailbreak",
]


class ChatRequest(BaseModel):
    """Validated chat request with prompt injection guard."""

    messages: List[Dict[str, Any]]
    max_tokens: int = 768
    temperature: float = 0.3

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v):
        """Validate messages for safety."""
        # Extract text content
        text_parts = []
        for msg in v:
            content = msg.get("content", "")
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                # Multimodal content
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

        full_text = " ".join(text_parts).lower()

        # Length check
        if len(full_text) > 20000:
            raise ValueError("Prompt too long (max 20K chars)")

        # Prompt injection detection
        for pattern in INJECTION_PATTERNS:
            if pattern in full_text:
                logger.warning("prompt_injection_detected", pattern=pattern)
                raise ValueError("Potential prompt injection detected")

        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        """Validate max_tokens within limits."""
        if v > 4096:
            raise ValueError("max_tokens exceeds limit (4096)")
        if v < 1:
            raise ValueError("max_tokens must be positive")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        """Validate temperature range."""
        if not 0 <= v <= 2.0:
            raise ValueError("temperature must be between 0 and 2.0")
        return v


class PromptValidator:
    """Static prompt validation utility."""

    @staticmethod
    def validate_prompt(messages: List[Dict]) -> bool:
        """Validate prompt for injection attempts."""
        try:
            ChatRequest(messages=messages)
            return True
        except ValueError:
            return False
