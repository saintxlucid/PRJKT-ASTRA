"""
ASTRA Identity & Role System
=============================

Multi-persona intelligence with role-based context switching.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from .astra_roles import (
    Role,
    ASTRA_ROLES,
    resolve_role,
    role_token,
    RoleSpec,
    ROLE_SPECS,
)
from .role_context import (
    get_current_role,
    role_scope,
    apply_role_to_messages,
    parse_activation_phrase,
)

__all__ = [
    "Role",
    "ASTRA_ROLES",
    "resolve_role",
    "role_token",
    "RoleSpec",
    "ROLE_SPECS",
    "get_current_role",
    "role_scope",
    "apply_role_to_messages",
    "parse_activation_phrase",
]
