"""
ASTRA Sandbox System
Implements isolation and resource controls for untrusted operations
"""
import os
import time
import signal
import subprocess
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
from dataclasses import dataclass

@dataclass
class SandboxLimits:
    max_time_s: int = 10  # Maximum execution time
    max_memory_mb: int = 512  # Maximum memory usage
    max_disk_mb: int = 100  # Maximum disk usage
    max_subprocesses: int = 5  # Maximum number of child processes
    max_files: int = 100  # Maximum number of open files
    max_stdout_size: int = 1024 * 1024  # 1MB stdout limit

class SandboxViolation(Exception):
    """Raised when sandbox constraints are violated"""
    pass

class Sandbox:
    """Enforces isolation and resource limits"""
    
    def __init__(self, 
                 root_path: str,
                 limits: Optional[SandboxLimits] = None):
        self.root = os.path.abspath(root_path)
        self.limits = limits or SandboxLimits()
        self.temp_dir = None
        self._setup()
        
    def _setup(self):
        """Initialize sandbox environment"""
        # Create root if it doesn't exist
        os.makedirs(self.root, exist_ok=True)
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(
            prefix="astra_sandbox_",
            dir=self.root
        )
        
    def _cleanup_temp(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def __del__(self):
        """Cleanup on destruction"""
        self._cleanup_temp()
        
    def validate_path(self, path: str) -> str:
        """Ensure path is within sandbox"""
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self.root):
            raise SandboxViolation(
                f"Path {path} attempts to escape sandbox"
            )
        return abs_path
        
    def get_disk_usage(self, path: str) -> int:
        """Get total disk usage in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total
        
    def check_disk_quota(self, size: int):
        """Check if operation would exceed disk quota"""
        current = self.get_disk_usage(self.root)
        if (current + size) > (self.limits.max_disk_mb * 1024 * 1024):
            raise SandboxViolation("Disk quota exceeded")
            
    def run_command(self,
                    cmd: List[str],
                    env: Optional[Dict[str, str]] = None,
                    cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run command with resource limits"""
        
        if cwd:
            cwd = self.validate_path(cwd)
        else:
            cwd = self.temp_dir
            
        # Basic command validation
        if not isinstance(cmd, list):
            raise ValueError("Command must be list of strings")
            
        # Only allow allowlisted commands
        ALLOWED_COMMANDS = {
            "python": True,
            "pip": True,
            "git": True,
            # Add more as needed
        }
        
        base_cmd = os.path.basename(cmd[0])
        if base_cmd not in ALLOWED_COMMANDS:
            raise SandboxViolation(
                f"Command {base_cmd} not in allowlist"
            )
            
        # Set up clean environment
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "TEMP": self.temp_dir,
            "TMP": self.temp_dir
        }
        if env:
            safe_env.update(env)
            
        try:
            # Start process with resource limits
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=safe_env,
                start_new_session=True  # New process group
            )
            
            stdout = []
            stderr = []
            stdout_size = 0
            
            while True:
                # Check timeout
                if time.time() - start_time > self.limits.max_time_s:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    raise SandboxViolation("Time limit exceeded")
                    
                # Read output with size limit
                if process.stdout in subprocess.select([process.stdout], [], [], 0.1)[0]:
                    chunk = process.stdout.read1(1024)
                    if not chunk:
                        break
                    stdout_size += len(chunk)
                    if stdout_size > self.limits.max_stdout_size:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        raise SandboxViolation("stdout size limit exceeded")
                    stdout.append(chunk)
                    
                if process.stderr in subprocess.select([process.stderr], [], [], 0.1)[0]:
                    chunk = process.stderr.read1(1024)
                    if not chunk:
                        break
                    stderr.append(chunk)
                    
                # Check if process finished
                if process.poll() is not None:
                    break
                    
            return {
                "returncode": process.wait(),
                "stdout": b"".join(stdout).decode(),
                "stderr": b"".join(stderr).decode()
            }
            
        except Exception as e:
            # Ensure process is killed
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except:
                pass
            raise
            
    def write_file(self, path: str, data: bytes):
        """Write file with quota enforcement"""
        abs_path = self.validate_path(path)
        self.check_disk_quota(len(data))
        
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)
            
    def read_file(self, path: str) -> bytes:
        """Read file from sandbox"""
        abs_path = self.validate_path(path)
        with open(abs_path, "rb") as f:
            return f.read()
            
# Initialize global sandbox instance
_SANDBOX = None

def init_sandbox(root_path: Optional[str] = None,
                limits: Optional[SandboxLimits] = None):
    """Initialize global sandbox"""
    global _SANDBOX
    if not root_path:
        root_path = os.path.join(
            os.path.dirname(__file__),
            "sandbox"
        )
    _SANDBOX = Sandbox(root_path, limits)
    
def get_sandbox() -> Sandbox:
    """Get global sandbox instance"""
    global _SANDBOX
    if not _SANDBOX:
        init_sandbox()
    return _SANDBOX