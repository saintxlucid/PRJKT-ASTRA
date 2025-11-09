"""
ASTRA 2.0 System Bridge - Core Windows API Integration
"""
import subprocess
import psutil
import platform
from typing import Dict, List, Optional
from ..security.permission_kernel import require_permission
from ..security.activity_audit import audit_action

class SystemBridge:
    def __init__(self):
        self.os_type = platform.system()
        self.is_windows = self.os_type == "Windows"
        
    @require_permission("system.process.list")
    def list_processes(self) -> List[Dict]:
        """List all running processes with details"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
    
    @require_permission("system.process.kill")
    def kill_process(self, pid: int) -> bool:
        """Safely terminate a process by PID"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            audit_action("process.kill", {"pid": pid, "name": proc.name()})
            return True
        except psutil.NoSuchProcess:
            return False
    
    @require_permission("system.command.execute")
    def execute_command(self, command: str, timeout: int = 30) -> Dict:
        """Execute a system command with safety checks"""
        audit_action("command.execute", {"command": command})
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "code": -1
            }