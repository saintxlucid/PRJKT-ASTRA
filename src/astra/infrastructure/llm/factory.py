"""
LLM provider factory.

This module provides a factory for creating LLM provider instances
based on configuration.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from astra.config import settings as global_settings
from astra.infrastructure.llm.base import LLMProvider
from astra.infrastructure.llm.llamacpp import LlamaCppProvider
from astra.utils.errors import ConfigurationError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from astra.models.config import Settings


def create_llm_provider(app_settings: Settings) -> LLMProvider:
    """
    Create an LLM provider instance based on configuration.

    Args:
        settings: Application settings

    Returns:
        LLMProvider instance

    Raises:
        ConfigurationError: If provider is not supported
    """
    provider_name = app_settings.llm.provider.lower()

    if provider_name == "llamacpp":
        base = os.getenv("ASTRA_LLM_BASE_URL", "http://127.0.0.1:8001")
        gguf = os.getenv("ASTRA_ACTIVE_GGUF")
        if not gguf:
            raise RuntimeError(
                "ASTRA_ACTIVE_GGUF is not set (GPT-OSS GGUF path required)."
            )

        logger.info(
            "provider_select",
            extra={
                "provider": "llamacpp",
                "base": base,
                "gguf": gguf,
                "preset": global_settings.sampling_preset,
            },
        )
        return LlamaCppProvider(
            base_url=base,
            timeout=app_settings.llm.timeout,
            retry_attempts=app_settings.llm.retry_attempts,
            use_harmony_format=app_settings.llm.use_harmony_format,
            sampling_preset=global_settings.sampling_preset,
            model_path=gguf,
        )
    elif provider_name == "openai":
        # Future: OpenAI provider
        raise ConfigurationError(
            f"Provider '{provider_name}' not yet implemented",
            code="PROVIDER_NOT_IMPLEMENTED",
        )
    elif provider_name == "anthropic":
        # Future: Anthropic provider
        raise ConfigurationError(
            f"Provider '{provider_name}' not yet implemented",
            code="PROVIDER_NOT_IMPLEMENTED",
        )
    else:
        raise ConfigurationError(
            f"Unknown LLM provider: {provider_name}",
            code="UNKNOWN_PROVIDER",
            details={"provider": provider_name, "supported": ["llamacpp"]},
        )
