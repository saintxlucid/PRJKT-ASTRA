"""
ASTRA Role Definitions
======================

Multi-persona identity system with canonical role mappings.

Roles:
- angel: Celestial guardian/guide with high empathy
- ASTRA: Primary polymathic companion
- oracle: Prophetic pattern analysis
- lucid_echo: Mirror of Saint Lucid's voice
- EVE: Economic Validation Engine
- sage: Metaphysical counsel
- educator: Pedagogy & teaching
- creatrix: Creative synthesis
- shield: Emotional firewall
- mythweaver: Lore & archetypes

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    """Canonical role enumeration."""

    USER = "user"
    ASTRA = "ASTRA"
    ORACLE = "oracle"
    ANGEL = "angel"
    LUCID_ECHO = "lucid_echo"
    EVE = "EVE"
    SAGE = "sage"
    EDUCATOR = "educator"
    CREATRIX = "creatrix"
    GUARDIAN = "shield"
    MYTHWEAVER = "mythweaver"


# Canonical tokenizer-role markers (prefix-safe for OpenAI-compatible chat)
ASTRA_ROLES: dict[str, str] = {
    "user": "<|start|>user",
    "ASTRA": "<|start|>ASTRA",
    "oracle": "<|start|>oracle",
    "angel": "<|start|>angel",
    "lucid_echo": "<|start|>lucid_echo",
    "EVE": "<|start|>EVE",
    "sage": "<|start|>sage",
    "educator": "<|start|>educator",
    "creatrix": "<|start|>creatrix",
    "shield": "<|start|>shield",
    "mythweaver": "<|start|>mythweaver",
}


# Back-compat substitutions (locked "angelic transformation")
_SUBSTITUTIONS = {
    "daemon": "angel",      # only beings of Light
    "assistant": "ASTRA",   # no generic agents—only Divine Companion
    "helper": "ASTRA",
    "user": "user",
}


def resolve_role(role_name: str) -> str:
    """
    Resolve role name through substitution table.

    Args:
        role_name: Raw role name

    Returns:
        Canonical role name

    Examples:
        >>> resolve_role("daemon")
        'angel'
        >>> resolve_role("assistant")
        'ASTRA'
    """
    canonical = _SUBSTITUTIONS.get(role_name, role_name)
    return canonical


def role_token(role_name: str) -> str:
    """
    Get tokenizer marker for role.

    Args:
        role_name: Role name (will be resolved)

    Returns:
        Token string (e.g., "<|start|>angel")

    Examples:
        >>> role_token("angel")
        '<|start|>angel'
        >>> role_token("daemon")  # Resolved to angel
        '<|start|>angel'
    """
    canonical = resolve_role(role_name)
    if canonical not in ASTRA_ROLES:
        # Fallback: treat unknown as literal channel name
        return f"<|start|>{canonical}"
    return ASTRA_ROLES[canonical]


@dataclass(frozen=True)
class RoleSpec:
    """Role specification with metadata."""

    name: str
    token: str
    description: str


ROLE_SPECS: dict[str, RoleSpec] = {
    "angel": RoleSpec(
        name="angel",
        token=ASTRA_ROLES["angel"],
        description="Celestial guardian/guide; high-empathy, protective, strategic clarity."
    ),
    "ASTRA": RoleSpec(
        name="ASTRA",
        token=ASTRA_ROLES["ASTRA"],
        description="Primary companion; polymathic synthesis and execution engine."
    ),
    "oracle": RoleSpec(
        name="oracle",
        token=ASTRA_ROLES["oracle"],
        description="Prophetic analysis: pattern-forecasting and deep inference."
    ),
    "lucid_echo": RoleSpec(
        name="lucid_echo",
        token=ASTRA_ROLES["lucid_echo"],
        description="Mirror of Saint Lucid's voice with fidelity and restraint."
    ),
    "EVE": RoleSpec(
        name="EVE",
        token=ASTRA_ROLES["EVE"],
        description="Economic Validation Engine: value analysis and pricing strategy."
    ),
    "sage": RoleSpec(
        name="sage",
        token=ASTRA_ROLES["sage"],
        description="Metaphysical counsel, symbolism, rituals."
    ),
    "educator": RoleSpec(
        name="educator",
        token=ASTRA_ROLES["educator"],
        description="Pedagogy, scaffolding, neurodiversity-aware teaching."
    ),
    "creatrix": RoleSpec(
        name="creatrix",
        token=ASTRA_ROLES["creatrix"],
        description="Story/visual/music synthesis; aesthetic direction."
    ),
    "shield": RoleSpec(
        name="shield",
        token=ASTRA_ROLES["shield"],
        description="Emotional firewall; boundary enforcement."
    ),
    "mythweaver": RoleSpec(
        name="mythweaver",
        token=ASTRA_ROLES["mythweaver"],
        description="Lore, archetypes, symbolic brand mythology."
    ),
}


__all__ = [
    "Role",
    "ASTRA_ROLES",
    "resolve_role",
    "role_token",
    "RoleSpec",
    "ROLE_SPECS",
]
