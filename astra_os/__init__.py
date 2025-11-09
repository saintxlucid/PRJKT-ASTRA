"""
ASTRA OS — AI-Native Operating System Layer

Phase A: AI-Augmented OS Layer (Windows host + privilege mediation)
Phase B: Virtualization Stratum (Type-1 hypervisor readying)
Phase C: Microkernel Spine (Bare-metal bootable kernel)
Phase D: Rehosting OS Services (Native ASTRA services)
Phase E: Distributed OS Mesh (Multi-node cooperation)
Phase F: Full AI Governance (Kernel-level lucid protocol)

Core Principle: "Everything privileged passes the Gate."

Token → Scope → Danger → Consent → Audit → Decision
"""
from __future__ import annotations

from astra_os.gate import (
    Action,
    AuditEvent,
    Decision,
    GateVerifier,
    Scope,
    Token,
    get_gate,
)

__all__ = [
    "Action",
    "AuditEvent",
    "Decision",
    "GateVerifier",
    "Scope",
    "Token",
    "get_gate",
]

__version__ = "0.1.0-alpha"
__phase__ = "A"  # AI-Augmented Layer
