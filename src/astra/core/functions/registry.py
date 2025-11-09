"""
ASTRA Universal Function Registry
==================================

Protocol-based plugin system for specialized intelligence engines.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class FunctionMeta:
    """Function metadata."""

    code: str                          # Function identifier (e.g., "INTEL_CORE")
    role_hint: str                     # Suggested role (e.g., "oracle")
    activation: str                    # Activation intent (e.g., "strategic_analysis")
    boundaries: list[str]              # Scope boundaries
    description: str                   # Human-readable description


class UniversalFunction(Protocol):
    """Protocol for universal function implementations."""

    meta: FunctionMeta

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute function with context.

        Args:
            context: Execution context

        Returns:
            Result dict
        """
        ...


# Global registry
_REGISTRY: dict[str, FunctionMeta] = {}
_IMPLEMENTATIONS: dict[str, type[UniversalFunction]] = {}


def register(func_cls: type[UniversalFunction]) -> type[UniversalFunction]:
    """
    Register function class.

    Args:
        func_cls: Function class

    Returns:
        Registered class

    Examples:
        >>> @register
        ... class IntelCore:
        ...     meta = FunctionMeta(code="INTEL_CORE", ...)
        ...     def execute(self, context):
        ...         return {"result": "analysis"}
    """
    instance = func_cls()
    _REGISTRY[instance.meta.code] = instance.meta
    _IMPLEMENTATIONS[instance.meta.code] = func_cls
    return func_cls


def get_meta(code: str) -> FunctionMeta | None:
    """
    Get function metadata.

    Args:
        code: Function code

    Returns:
        Function metadata or None
    """
    return _REGISTRY.get(code)


def get_impl(code: str) -> type[UniversalFunction] | None:
    """
    Get function implementation class.

    Args:
        code: Function code

    Returns:
        Function class or None
    """
    return _IMPLEMENTATIONS.get(code)


__all__ = [
    "FunctionMeta",
    "UniversalFunction",
    "register",
    "get_meta",
    "get_impl",
]
