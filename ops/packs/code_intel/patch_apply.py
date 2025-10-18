"""
ASTRA Patch Apply
Guarded unified patch application with allowlist and size caps.
"""
import os
from pathlib import Path

MAX_LINES = int(os.getenv("ASTRA_CODE_MAX_PATCH_LINES", "800"))
ALLOWLIST = [Path(p.strip()) for p in os.getenv("ASTRA_CODE_ROOTS", "src,ui,plugins,ops,tests").split(",")]


def in_allow(path: Path) -> bool:
    """Check if path is within allowed roots."""
    try:
        rp = path.resolve()
    except Exception:
        return False
    
    for base in ALLOWLIST:
        try:
            base_resolved = base.resolve()
            if base_resolved in rp.parents or rp == base_resolved:
                return True
        except Exception:
            continue
    return False


def apply_simple_replacement(target: Path, new_text: str):
    """Apply simple full-file replacement."""
    if not in_allow(target):
        raise PermissionError(f"path not allowed: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_text, encoding="utf-8")


def apply_unified_patch(target: Path, original: str, patched: str):
    """
    Guarded apply: requires both original and patched content.
    Avoids external patch utilities and keeps it deterministic.
    """
    if not in_allow(target):
        raise PermissionError(f"path not allowed: {target}")
    
    if len(patched.splitlines()) - len(original.splitlines()) > MAX_LINES:
        raise ValueError("patch too large")
    
    # Verify on-disk content matches original
    on_disk = ""
    try:
        on_disk = target.read_text(encoding="utf-8")
    except Exception:
        pass
    
    if on_disk.strip() != original.strip():
        raise RuntimeError("on-disk content diverged; rebase required")
    
    target.write_text(patched, encoding="utf-8")
    return True
