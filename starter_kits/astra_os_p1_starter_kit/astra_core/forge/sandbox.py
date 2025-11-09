from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

try:  # pragma: no cover - resource is missing on Windows
    import resource
except ImportError:  # pragma: no cover
    resource = None  # type: ignore


class SandboxError(RuntimeError):
    """Raised when sandbox execution fails."""


@dataclass
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str


def run_sandboxed(code: str, timeout_sec: int = 5) -> SandboxResult:
    """Execute untrusted Python with strict resource limits."""

    def _apply_limits() -> None:
        if resource is None:
            return
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (timeout_sec, timeout_sec))
            resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        except (ValueError, OSError):
            pass

    with tempfile.TemporaryDirectory() as tmp_dir:
        script_path = os.path.join(tmp_dir, "user_code.py")
        with open(script_path, "w", encoding="utf-8") as handle:
            handle.write(code)

        try:
            completed = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                preexec_fn=_apply_limits if resource is not None and os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - smoke-level guard
            raise SandboxError("Execution exceeded timeout") from exc

    return SandboxResult(
        returncode=completed.returncode,
        stdout=completed.stdout[:5000],
        stderr=completed.stderr[:5000],
    )
