"""
ASTRA API Models
================

Pydantic request/response models.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RoleSwitchRequest(BaseModel):
    """Request to switch active role."""

    role: str = Field(..., description="Target role name (e.g., 'angel', 'ASTRA')")


class InvokeRequest(BaseModel):
    """Request to invoke a universal function."""

    args: dict[str, Any] | None = Field(default_factory=dict, description="Function arguments")


__all__ = ["RoleSwitchRequest", "InvokeRequest"]
