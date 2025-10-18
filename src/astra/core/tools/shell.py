"""
ASTRA Shell Command Tools
Safe shell command execution with timeouts and output capture.
Created: October 16, 2025
"""
import asyncio
import shlex
from typing import Optional, Dict, Any
import platform
import structlog
from pathlib import Path

from src.astra.core.tool_bus import tool

logger = structlog.get_logger()

# Set shell based on platform
SHELL = "powershell.exe" if platform.system() == "Windows" else "/bin/sh"
SHELL_ARGS = ["-Command"] if platform.system() == "Windows" else ["-c"]

class ShellError(Exception):
    """Shell command execution error"""
    def __init__(self, cmd: str, returncode: int, stdout: str, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"Command failed with exit code {returncode}:\n"
            f"Command: {cmd}\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
        )

async def run_shell_command(
    cmd: str,
    timeout: float,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Run a shell command with timeout.
    Args:
        cmd: Command to execute
        timeout: Timeout in seconds
        cwd: Working directory
        env: Environment variables
    Returns:
        Dict with stdout, stderr, and return code
    """
    if platform.system() == "Windows":
        # Escape quotes for PowerShell
        cmd = cmd.replace('"', '`"')
    else:
        # Split command for Unix shell
        cmd = shlex.quote(cmd)

    process = await asyncio.create_subprocess_exec(
        SHELL,
        *SHELL_ARGS,
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        try:
            process.terminate()
            await asyncio.sleep(0.1)
            process.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(f"Command timed out after {timeout}s: {cmd}")

    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()

    if process.returncode != 0:
        raise ShellError(cmd, process.returncode, stdout, stderr)

    return {
        "stdout": stdout,
        "stderr": stderr,
        "returncode": process.returncode
    }

@tool(
    name="shell_exec",
    description="Execute a shell command safely",
    schema={
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "working_dir": {"type": "string", "optional": True},
            "timeout": {"type": "number", "default": 30},
            "env": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "optional": True
            }
        },
        "required": ["command"]
    },
    timeout=300,  # Maximum global timeout
    isolated=True  # Run in isolated process
)
async def execute_shell(
    command: str,
    working_dir: Optional[str] = None,
    timeout: float = 30,
    env: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Execute a shell command with safety controls.
    Args:
        command: Command to execute
        working_dir: Working directory
        timeout: Command timeout in seconds
        env: Additional environment variables
    Returns:
        Dict with command output
    """
    logger.info(
        "Executing shell command",
        command=command,
        working_dir=working_dir,
        timeout=timeout
    )

    if working_dir:
        working_dir = str(Path(working_dir).resolve())

    try:
        result = await run_shell_command(
            command,
            timeout=timeout,
            cwd=working_dir,
            env=env
        )
        
        return {
            "success": True,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "command": command,
            "working_dir": working_dir
        }

    except TimeoutError as e:
        return {
            "success": False,
            "error": str(e),
            "command": command,
            "working_dir": working_dir
        }
    except ShellError as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "command": command,
            "working_dir": working_dir
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command,
            "working_dir": working_dir
        }