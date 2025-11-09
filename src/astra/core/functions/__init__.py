"""
ASTRA Universal Functions
=========================

Function registry and implementations.
"""

from .registry import (
    FunctionMeta,
    UniversalFunction,
    register,
    get_meta,
    get_impl,
)

__all__ = [
    "FunctionMeta",
    "UniversalFunction",
    "register",
    "get_meta",
    "get_impl",
]
