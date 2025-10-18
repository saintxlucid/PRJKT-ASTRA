"""Bridge package enabling access to the legacy `astra-local` modules."""
from __future__ import annotations

from pathlib import Path

# Allow imports like `astra_local.backend.*` to resolve to the existing
# `astra-local/` directory that ships with the project.
_pkg_root = Path(__file__).resolve().parents[2] / "astra-local"
if not _pkg_root.exists():
    raise ImportError(
        "astra_local package expects 'astra-local/' directory alongside the source tree"
    )

# Extend the package search path so submodules load from the legacy location.
__path__.append(str(_pkg_root))
