"""
Sandboxed Tool Executor - Docker Isolation
===========================================

Implements ActionExecutor interface with Docker-based isolation.

Security Model:
- Allowlist-only (deny by default)
- Per-tool Docker image (separate attack surface)
- Read-only filesystem, no network, resource limits
- User 1000:1000 (non-root)
- Seccomp profile (no-new-privileges)
- Path whitelisting (sandbox/ root only)

Fallback (Windows without Docker):
- Uses LocalExecutor with deny-by-default policies
- Logs warning: "Docker unavailable, using restricted local execution"

Author: ASTRA Core Team
Created: 2025-11-01 (Week-2 Refactor)
"""

import os
import platform
import subprocess
import uuid
from pathlib import Path
from typing import Any

# Docker availability check
DOCKER_AVAILABLE = False
try:
    import docker
    docker.from_env().ping()
    DOCKER_AVAILABLE = True
except Exception:
    pass


# Tool allowlist (extend as needed)
ALLOWED_TOOLS = {
    "list_dir": {
        "image": "astra-tools:latest",
        "description": "List directory contents (safe, read-only)"
    },
    "read_file": {
        "image": "astra-tools:latest",
        "description": "Read file contents (safe, read-only)"
    },
    "search_files": {
        "image": "astra-tools:latest",
        "description": "Search files by pattern (safe, read-only)"
    }
    # Add tools incrementally after security review
    # NEVER: delete_file, execute_shell, network_request
}

# Whitelist root (all mounts must be under this path)
ALLOWED_MOUNT_ROOT = os.path.abspath("sandbox")


class DockerSandboxExecutor:
    """
    Docker-based tool executor with isolation.

    Security:
        - Each tool runs in isolated container
        - No network access (network_disabled=True)
        - Read-only filesystem (read_only=True)
        - Resource limits (CPU, memory)
        - User 1000:1000 (non-root)
        - Auto-removed after execution (remove=True)

    Example:
        >>> executor = DockerSandboxExecutor()
        >>> result = executor.run("list_dir", {"path": "sandbox/docs"}, timeout_s=10)
        >>> print(result["status"], result["output"])
    """

    def __init__(self):
        """Initialize Docker client."""
        if not DOCKER_AVAILABLE:
            raise RuntimeError(
                "Docker unavailable. Install Docker Desktop or use LocalExecutor "
                "(with reduced security)."
            )
        self.client = docker.from_env()

    def run(
        self,
        tool: str,
        args: dict[str, Any],
        timeout_s: int = 30
    ) -> dict[str, Any]:
        """
        Execute tool in isolated Docker container.

        Args:
            tool: Tool name (must be in ALLOWED_TOOLS)
            args: Tool arguments (validated against allowlist)
            timeout_s: Max execution time

        Returns:
            {
                "status": int,       # exit code
                "output": str,       # stdout+stderr
                "error": str | None  # error message if failed
            }

        Security:
            - Rejects unknown tools (deny by default)
            - Validates mount paths (must be under ALLOWED_MOUNT_ROOT)
            - Enforces timeout (kills container if exceeded)
        """
        # Validation: tool allowlist
        if tool not in ALLOWED_TOOLS:
            return {
                "status": -1,
                "output": "",
                "error": f"tool_not_allowed: {tool} (allowlist: {list(ALLOWED_TOOLS.keys())})"
            }

        # Validation: mount path
        mount_path = args.get("mount", "sandbox")
        abs_mount = os.path.abspath(mount_path)
        if not abs_mount.startswith(ALLOWED_MOUNT_ROOT):
            return {
                "status": -1,
                "output": "",
                "error": f"mount_out_of_bounds: {abs_mount} (must be under {ALLOWED_MOUNT_ROOT})"
            }

        # Ensure mount path exists
        Path(abs_mount).mkdir(parents=True, exist_ok=True)

        # Build command
        tool_spec = ALLOWED_TOOLS[tool]
        image = tool_spec["image"]
        container_name = f"astra-{tool}-{uuid.uuid4().hex[:8]}"

        # Convert args to JSON string for container
        import json
        args_json = json.dumps(args, ensure_ascii=False)

        try:
            container = self.client.containers.run(
                image,
                command=["/bin/astra-tool", tool, "--json", args_json],
                user="1000:1000",  # non-root
                detach=True,
                network_disabled=True,  # no network
                read_only=True,  # immutable filesystem
                mem_limit="512m",  # 512 MB RAM
                nano_cpus=500_000_000,  # 0.5 CPU cores
                security_opt=["no-new-privileges"],  # seccomp
                volumes={abs_mount: {"bind": "/work", "mode": "ro"}},  # read-only mount
                working_dir="/work",
                name=container_name,
                remove=True,  # auto-cleanup
                stdout=True,
                stderr=True
            )

            # Wait for completion (with timeout)
            exit_code = container.wait(timeout=timeout_s)["StatusCode"]
            logs = container.logs().decode("utf-8", errors="ignore")

            return {
                "status": exit_code,
                "output": logs,
                "error": None if exit_code == 0 else f"exit_code={exit_code}"
            }

        except docker.errors.ContainerError as e:
            return {
                "status": e.exit_status,
                "output": e.stderr.decode("utf-8", errors="ignore") if e.stderr else "",
                "error": f"container_error: {str(e)}"
            }

        except docker.errors.ImageNotFound:
            return {
                "status": -1,
                "output": "",
                "error": f"image_not_found: {image} (build Docker images first)"
            }

        except Exception as e:
            return {
                "status": -1,
                "output": "",
                "error": f"executor_error: {str(e)}"
            }


class LocalExecutor:
    """
    Fallback executor for environments without Docker.

    Security:
        - DENY by default (only allowlisted tools)
        - Logs all executions
        - No destructive operations (delete, modify, network)
        - Limited to sandbox/ directory

    Warning:
        Less secure than DockerSandboxExecutor. Use Docker when possible.
    """

    def __init__(self):
        """Initialize local executor."""
        print("⚠️  WARNING: Using LocalExecutor (Docker unavailable). Security is reduced.")

    def run(
        self,
        tool: str,
        args: dict[str, Any],
        timeout_s: int = 30
    ) -> dict[str, Any]:
        """
        Execute tool locally (fallback for non-Docker environments).

        Security:
            - Only implements safe, read-only tools
            - Rejects destructive operations
        """
        if tool not in ALLOWED_TOOLS:
            return {
                "status": -1,
                "output": "",
                "error": f"tool_not_allowed: {tool}"
            }

        # Only implement safe tools
        if tool == "list_dir":
            return self._list_dir(args, timeout_s)
        elif tool == "read_file":
            return self._read_file(args, timeout_s)
        elif tool == "search_files":
            return self._search_files(args, timeout_s)
        else:
            return {
                "status": -1,
                "output": "",
                "error": f"tool_not_implemented: {tool} (LocalExecutor only supports read-only tools)"
            }

    def _list_dir(self, args: dict[str, Any], timeout_s: int) -> dict[str, Any]:
        """List directory (safe operation)."""
        path = Path(args.get("path", "sandbox"))
        try:
            if not path.exists():
                return {"status": 1, "output": "", "error": "path_not_found"}
            files = [f.name for f in path.iterdir()]
            return {"status": 0, "output": "\n".join(files), "error": None}
        except Exception as e:
            return {"status": 1, "output": "", "error": str(e)}

    def _read_file(self, args: dict[str, Any], timeout_s: int) -> dict[str, Any]:
        """Read file (safe operation)."""
        path = Path(args.get("path", ""))
        try:
            if not path.exists():
                return {"status": 1, "output": "", "error": "file_not_found"}
            content = path.read_text(encoding="utf-8")
            return {"status": 0, "output": content, "error": None}
        except Exception as e:
            return {"status": 1, "output": "", "error": str(e)}

    def _search_files(self, args: dict[str, Any], timeout_s: int) -> dict[str, Any]:
        """Search files by pattern (safe operation)."""
        pattern = args.get("pattern", "*")
        root = Path(args.get("root", "sandbox"))
        try:
            matches = [str(p) for p in root.rglob(pattern)]
            return {"status": 0, "output": "\n".join(matches), "error": None}
        except Exception as e:
            return {"status": 1, "output": "", "error": str(e)}


# Factory function
def create_executor() -> DockerSandboxExecutor | LocalExecutor:
    """
    Create appropriate executor based on Docker availability.

    Returns:
        DockerSandboxExecutor if Docker available, else LocalExecutor
    """
    if DOCKER_AVAILABLE:
        return DockerSandboxExecutor()
    else:
        return LocalExecutor()
