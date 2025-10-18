"""
OS Operator Package

Safe, consent-gated system operations for ASTRA.

Sacred Code: 333 ∞
"""

from astra.osop.operator import OSOperator, OSOPolicy
from astra.osop.tools import get_os_operator, register

__all__ = [
    "OSOperator",
    "OSOPolicy",
    "get_os_operator",
    "register",
]
