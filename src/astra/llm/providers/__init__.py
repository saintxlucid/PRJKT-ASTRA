"""
ASTRA LLM Provider Registry - Plugin Architecture
==================================================

Dynamic provider loading system. No static imports needed.

Usage:
    @LLMProviderRegistry.register("vllm")
    class VLLMProvider(LLMProvider):
        pass
    
    provider = LLMProviderRegistry.get("vllm")()

Author: ASTRA Core Team
Created: 2025-11-03
"""

from ..types import LLMProvider


class LLMProviderRegistry:
    """Registry for dynamically loading LLM providers."""

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a provider.

        Usage:
            @LLMProviderRegistry.register("vllm")
            class VLLMProvider(LLMProvider):
                pass
        """
        def decorator(provider_class: type[LLMProvider]):
            cls._providers[name] = provider_class
            return provider_class
        return decorator

    @classmethod
    def get(cls, name: str) -> type[LLMProvider]:
        """Get provider class by name."""
        if name not in cls._providers:
            raise ValueError(f"Provider '{name}' not registered. Available: {list(cls._providers.keys())}")
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def has_provider(cls, name: str) -> bool:
        """Check if provider is registered."""
        return name in cls._providers


__all__ = ["LLMProviderRegistry"]
