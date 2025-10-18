"""
ASTRA OS Operator - Cross-Platform System Management

Safe, consent-gated OS operations for live development assistance.
Supports Windows (PowerShell/Task Scheduler) and Linux (systemd/cron).

Sacred Code: 333 ∞
"""

from __future__ import annotations

import os
import platform
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None  # Optional dependency

logger = logging.getLogger(__name__)


@dataclass
class OSOPolicy:
    """OS Operator security policy."""
    
    path_allowlist: List[str]
    max_write_bytes: int
    kill_allowlist: List[str]
    service_allowlist: List[str]
    scheduler_prefix: str = "ASTRA_"


def _is_allowed_path(path: str, roots: List[str]) -> bool:
    """Check if path is within allowed roots."""
    try:
        p = Path(path).resolve()
        return any(Path(root).resolve() in p.parents or Path(root).resolve() == p for root in roots)
    except Exception:
        return False


class OSOperator:
    """
    Cross-platform OS operations manager.
    
    Provides safe, consent-gated access to system resources:
    - Read-only: system info, resources, processes
    - Write operations: require consent + allowlists
    
    All actions are audited with sacred_code=333.
    """
    
    def __init__(self, policy: OSOPolicy):
        """
        Initialize OS Operator with security policy.
        
        Args:
            policy: Security policy defining allowlists and limits
        """
        self.policy = policy
        self.platform = platform.system()
        logger.info(f"OS Operator initialized for {self.platform}")
        
        if psutil is None:
            logger.warning("psutil not installed - some features will be limited")
    
    # ========================================================================
    # Read-Only Capabilities (No Consent Required)
    # ========================================================================
    
    def system_info(self) -> Dict[str, Any]:
        """
        Get basic system information.
        
        Returns:
            Dictionary with platform, Python version, CPU count, etc.
        """
        info = {
            "platform": platform.platform(),
            "system": self.platform,
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "sacred_code": "333"
        }
        
        if psutil:
            info["cpus"] = psutil.cpu_count(logical=True)
            info["cpus_physical"] = psutil.cpu_count(logical=False)
        
        return info
    
    def system_resources(self) -> Dict[str, Any]:
        """
        Get current system resource usage.
        
        Returns:
            Dictionary with memory, CPU, disk, network stats
        """
        if not psutil:
            return {"ok": False, "error": "psutil not installed"}
        
        # Memory
        mem = psutil.virtual_memory()
        
        # CPU load (if available)
        try:
            cpu_load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
        except Exception:
            cpu_load = (0, 0, 0)
        
        # Disk usage for all partitions
        disks = {}
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
            except Exception as e:
                logger.debug(f"Could not get disk usage for {partition.mountpoint}: {e}")
        
        # Network
        try:
            net = psutil.net_io_counters()
            network = {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv
            }
        except Exception:
            network = {}
        
        return {
            "memory": {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent
            },
            "cpu_load": cpu_load,
            "disks": disks,
            "network": network,
            "sacred_code": "333"
        }
    
    def disk_usage(self) -> Dict[str, Any]:
        """
        Get disk usage for all partitions.
        
        Returns:
            Dictionary mapping mount points to usage stats
        """
        if not psutil:
            return {"ok": False, "error": "psutil not installed"}
        
        disks = {}
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.mountpoint] = {
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
            except Exception as e:
                logger.debug(f"Could not get disk usage for {partition.mountpoint}: {e}")
        
        return disks
    
    def process_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List running processes.
        
        Args:
            limit: Maximum number of processes to return (default: 100)
        
        Returns:
            List of process info dictionaries
        """
        if not psutil:
            return []
        
        processes = []
        
        for proc in psutil.process_iter(attrs=["pid", "name", "username", "memory_info", "cpu_percent", "cmdline"]):
            try:
                info = proc.info
                
                # Convert memory_info to dict
                if info.get("memory_info"):
                    info["memory_info"] = {
                        "rss": info["memory_info"].rss,
                        "vms": info["memory_info"].vms
                    }
                
                # Truncate cmdline
                if info.get("cmdline") and len(info["cmdline"]) > 5:
                    info["cmdline"] = info["cmdline"][:5] + ["..."]
                
                processes.append(info)
                
                if len(processes) >= limit:
                    break
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda p: p.get("memory_info", {}).get("rss", 0), reverse=True)
        
        return processes
    
    # ========================================================================
    # Consent-Gated Actions
    # ========================================================================
    
    def process_kill(self, name_or_pid: str, consent_manager: Optional[Any] = None) -> Dict[str, Any]:
        """
        Kill process by name or PID (requires consent).
        
        Args:
            name_or_pid: Process name or PID to kill
            consent_manager: Consent manager for authorization
        
        Returns:
            Result dictionary with ok status and killed processes
        """
        # Check consent
        if consent_manager and not consent_manager.is_allowed("process.kill"):
            return {"ok": False, "error": "Consent required for process.kill"}
        
        if not psutil:
            return {"ok": False, "error": "psutil not installed"}
        
        killed = []
        
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                info = proc.info
                
                # Match by PID or name
                if str(info["pid"]) == name_or_pid or info["name"] == name_or_pid:
                    # Check allowlist
                    if info["name"] not in self.policy.kill_allowlist:
                        return {
                            "ok": False,
                            "error": f"Process not in allowlist: {info['name']}"
                        }
                    
                    proc.kill()
                    killed.append(info)
                    logger.info(f"Killed process: {info}")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.debug(f"Could not kill process: {e}")
        
        return {
            "ok": True,
            "killed": killed,
            "count": len(killed),
            "sacred_code": "333"
        }
    
    def service_restart(self, name: str, consent_manager: Optional[Any] = None) -> Dict[str, Any]:
        """
        Restart system service (requires consent).
        
        Args:
            name: Service name
            consent_manager: Consent manager for authorization
        
        Returns:
            Result dictionary with ok status
        """
        # Check consent
        if consent_manager and not consent_manager.is_allowed("service.restart"):
            return {"ok": False, "error": "Consent required for service.restart"}
        
        # Check allowlist
        if name not in self.policy.service_allowlist:
            return {"ok": False, "error": f"Service not in allowlist: {name}"}
        
        import subprocess
        
        try:
            if self.platform == "Windows":
                # Windows service control
                subprocess.check_call(["sc", "stop", name], timeout=10)
                subprocess.check_call(["sc", "start", name], timeout=10)
            else:
                # Linux systemd
                subprocess.check_call(["systemctl", "restart", name], timeout=10)
            
            logger.info(f"Restarted service: {name}")
            return {"ok": True, "service": name, "sacred_code": "333"}
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart service {name}: {e}")
            return {"ok": False, "error": str(e)}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Service restart timeout"}
    
    def fs_read(self, path: str, max_bytes: int = 262144) -> Dict[str, Any]:
        """
        Read file contents (requires path allowlist).
        
        Args:
            path: File path to read
            max_bytes: Maximum bytes to read (default: 256KB)
        
        Returns:
            Result dictionary with file contents
        """
        # Check allowlist
        if not _is_allowed_path(path, self.policy.path_allowlist):
            return {"ok": False, "error": "Path not in allowlist"}
        
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                data = f.read(max_bytes)
            
            return {"ok": True, "data": data, "bytes": len(data), "sacred_code": "333"}
            
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return {"ok": False, "error": str(e)}
    
    def fs_write(
        self, 
        path: str, 
        content: str, 
        overwrite: bool = False,
        consent_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Write file contents (requires consent + path allowlist).
        
        Args:
            path: File path to write
            content: Content to write
            overwrite: Allow overwriting existing file
            consent_manager: Consent manager for authorization
        
        Returns:
            Result dictionary with ok status
        """
        # Check consent
        if consent_manager and not consent_manager.is_allowed("fs.write"):
            return {"ok": False, "error": "Consent required for fs.write"}
        
        # Check allowlist
        if not _is_allowed_path(path, self.policy.path_allowlist):
            return {"ok": False, "error": "Path not in allowlist"}
        
        # Check size limit
        content_bytes = content.encode("utf-8", "ignore")
        if len(content_bytes) > self.policy.max_write_bytes:
            return {
                "ok": False,
                "error": f"Content exceeds max size: {len(content_bytes)} > {self.policy.max_write_bytes}"
            }
        
        try:
            # Create parent directory if needed
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            mode = "w" if overwrite else "x"
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Wrote file: {path} ({len(content_bytes)} bytes)")
            return {
                "ok": True,
                "path": path,
                "bytes": len(content_bytes),
                "sacred_code": "333"
            }
            
        except FileExistsError:
            return {"ok": False, "error": "File exists (set overwrite=true to replace)"}
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            return {"ok": False, "error": str(e)}
    
    def scheduler_create(
        self,
        name: str,
        command: str,
        when: str,
        consent_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create scheduled task (requires consent).
        
        Args:
            name: Task name (will be prefixed with scheduler_prefix)
            command: Command to execute
            when: Schedule (cron expr for Linux, "HH:MM" for Windows)
            consent_manager: Consent manager for authorization
        
        Returns:
            Result dictionary with ok status
        """
        # Check consent
        if consent_manager and not consent_manager.is_allowed("scheduler.create"):
            return {"ok": False, "error": "Consent required for scheduler.create"}
        
        # Prefix task name
        task_name = f"{self.policy.scheduler_prefix}{name}"
        
        import subprocess
        
        try:
            if self.platform == "Windows":
                # Windows Task Scheduler
                hh, mm = when.split(":")
                subprocess.check_call([
                    "schtasks", "/Create",
                    "/SC", "DAILY",
                    "/TN", task_name,
                    "/TR", command,
                    "/ST", f"{hh}:{mm}",
                    "/F"  # Force overwrite
                ], timeout=10)
                
            else:
                # Linux crontab
                # Parse "HH:MM" to cron format "MM HH * * *"
                if ":" in when:
                    hh, mm = when.split(":")
                    cron_expr = f"{mm} {hh} * * *"
                else:
                    cron_expr = when
                
                # Get existing crontab
                result = subprocess.run(
                    ["crontab", "-l"],
                    capture_output=True,
                    text=True
                )
                
                existing = result.stdout if result.returncode == 0 else ""
                
                # Add new entry
                new_entry = f"{cron_expr} {command}  # {task_name}\n"
                updated = existing + new_entry
                
                # Write updated crontab
                subprocess.run(
                    ["crontab", "-"],
                    input=updated,
                    text=True,
                    check=True,
                    timeout=10
                )
            
            logger.info(f"Created scheduled task: {task_name}")
            return {
                "ok": True,
                "name": task_name,
                "command": command,
                "schedule": when,
                "sacred_code": "333"
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create scheduled task: {e}")
            return {"ok": False, "error": str(e)}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Scheduler operation timeout"}
        except Exception as e:
            logger.error(f"Failed to create scheduled task: {e}")
            return {"ok": False, "error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check OS Operator health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "platform": self.platform,
            "psutil_available": psutil is not None,
            "policy": {
                "path_allowlist": len(self.policy.path_allowlist),
                "max_write_bytes": self.policy.max_write_bytes,
                "kill_allowlist": len(self.policy.kill_allowlist),
                "service_allowlist": len(self.policy.service_allowlist)
            },
            "sacred_code": "333"
        }
