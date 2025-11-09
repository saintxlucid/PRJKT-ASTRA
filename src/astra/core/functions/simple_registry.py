"""
Simplified function registry for ASTRA v2.5 universal functions.
Direct registration without complex protocol requirements.
"""

from typing import Any

# Simple registry: code -> (instance, metadata)
FUNCTION_REGISTRY: dict[str, dict[str, Any]] = {}


def register_function(code: str, instance: Any, role_hint: str, description: str):
    """Register a universal function instance."""
    FUNCTION_REGISTRY[code] = {
        "instance": instance,
        "code": code,
        "role_hint": role_hint,
        "description": description
    }


def get_function(code: str) -> Any | None:
    """Get function instance by code."""
    entry = FUNCTION_REGISTRY.get(code)
    return entry["instance"] if entry else None


def list_all_functions() -> list[dict[str, Any]]:
    """List all registered functions."""
    return [
        {
            "code": entry["code"],
            "role_hint": entry["role_hint"],
            "description": entry["description"]
        }
        for entry in FUNCTION_REGISTRY.values()
    ]
