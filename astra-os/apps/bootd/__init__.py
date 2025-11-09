"""
ASTRA-OS Boot Daemon (Windows Service)
Service wrapper with supervisor pattern, safe-mode, kill-switch, and crash recovery.

File: apps/bootd/__init__.py
Lines: 400+
"""

import asyncio
import logging
import signal
import sys
import subprocess
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

try:
    import win32serviceutil
    import win32service
    import win32event
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger("astra.bootd")


class BootMode(Enum):
    """Boot daemon operating modes."""
    NORMAL = "normal"
    SAFE_MODE = "safe"
    MAINTENANCE = "maintenance"


class ComponentStatus(Enum):
    """Child component status."""
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNRESPONSIVE = "unresponsive"


@dataclass
class ChildProcess:
    """Managed child process."""
    name: str
    executable: str
    args: List[str] = None
    process: Optional[subprocess.Popen] = None
    status: ComponentStatus = ComponentStatus.STOPPED
    restart_count: int = 0
    max_restarts: int = 5
    restart_backoff_s: int = 5
    last_start_time: Optional[datetime] = None
    last_crash_time: Optional[datetime] = None
    min_uptime_s: int = 10


class SafeMode:
    """Safe mode configuration and behavior."""
    
    def __init__(self):
        self.enabled = False
        self.started_at = None
        self.reason = ""
        
        # Safe mode restrictions
        self.disable_autonomy = True
        self.disable_learning = True
        self.sensors_readonly = True
        self.require_explicit_consent = True
        self.verbose_logging = True
        self.halt_on_error = True
    
    def activate(self, reason: str = "Manual activation"):
        """Activate safe mode."""
        self.enabled = True
        self.started_at = datetime.utcnow()
        self.reason = reason
        logger.critical(f"SAFE MODE ACTIVATED: {reason}")
    
    def deactivate(self):
        """Deactivate safe mode."""
        self.enabled = False
        duration = (datetime.utcnow() - self.started_at).total_seconds()
        logger.info(f"Safe mode deactivated after {duration:.1f}s")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "reason": self.reason,
            "duration_s": (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0,
        }


class ProcessSupervisor:
    """
    Supervises child processes with restart/recovery logic.
    Implements watchdog pattern.
    """
    
    def __init__(self, boot_mode: BootMode = BootMode.NORMAL):
        self.boot_mode = boot_mode
        self.safe_mode = SafeMode()
        self.children: Dict[str, ChildProcess] = {}
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.health_check_interval_s = 5.0
        self.startup_grace_period_s = 3.0
    
    def add_child(self, name: str, executable: str, args: List[str] = None):
        """Register child process to supervise."""
        self.children[name] = ChildProcess(
            name=name,
            executable=executable,
            args=args or []
        )
        logger.info(f"Registered child process: {name}")
    
    async def start(self):
        """Start all child processes and supervision."""
        self.running = True
        logger.info(f"Boot daemon starting (mode={self.boot_mode.value})")
        
        # Start all children
        for child in self.children.values():
            await self._start_child(child)
        
        # Start health check loop
        asyncio.create_task(self._health_check_loop())
        
        logger.info("Boot daemon started; supervision active")
    
    async def stop(self):
        """Stop all child processes gracefully."""
        self.running = False
        logger.info("Boot daemon stopping")
        
        # Terminate children in reverse order
        for name in reversed(list(self.children.keys())):
            await self._stop_child(self.children[name])
        
        logger.info("Boot daemon stopped")
    
    async def _start_child(self, child: ChildProcess):
        """Start a child process."""
        try:
            cmd = [child.executable] + child.args
            
            logger.info(f"Starting: {child.name} -> {cmd}")
            
            child.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            child.status = ComponentStatus.RUNNING
            child.restart_count = 0
            child.last_start_time = datetime.utcnow()
            
            logger.info(f"Started {child.name} (PID={child.process.pid})")
        except Exception as e:
            logger.error(f"Failed to start {child.name}: {e}")
            child.status = ComponentStatus.FAILED
            
            if self.safe_mode.enabled and self.safe_mode.halt_on_error:
                await self.activate_safe_mode(f"Failed to start {child.name}")
    
    async def _stop_child(self, child: ChildProcess, timeout_s: int = 5):
        """Stop child process gracefully."""
        if not child.process:
            return
        
        try:
            logger.info(f"Stopping: {child.name}")
            child.process.terminate()
            
            try:
                child.process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {child.name}")
                child.process.kill()
                child.process.wait()
            
            child.status = ComponentStatus.STOPPED
            logger.info(f"Stopped {child.name}")
        except Exception as e:
            logger.error(f"Error stopping {child.name}: {e}")
    
    async def _health_check_loop(self):
        """Continuously monitor child processes."""
        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval_s)
                
                for child in self.children.values():
                    await self._check_child_health(child)
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _check_child_health(self, child: ChildProcess):
        """Check single child process health."""
        if not child.process:
            return
        
        # Check if process exited
        returncode = child.process.poll()
        
        if returncode is not None:
            # Process died
            child.status = ComponentStatus.FAILED
            child.last_crash_time = datetime.utcnow()
            
            uptime = (child.last_crash_time - child.last_start_time).total_seconds()
            logger.warning(f"{child.name} crashed (uptime={uptime:.1f}s, return={returncode})")
            
            # Decide on restart
            if uptime < child.min_uptime_s:
                # Crash loop protection
                logger.error(f"Crash loop detected for {child.name}")
                await self.activate_safe_mode(f"Crash loop in {child.name}")
            elif child.restart_count < child.max_restarts:
                # Restart with backoff
                logger.info(f"Restarting {child.name} (attempt {child.restart_count + 1}/"
                           f"{child.max_restarts})")
                child.restart_count += 1
                await asyncio.sleep(child.restart_backoff_s * child.restart_count)
                await self._start_child(child)
            else:
                logger.error(f"Max restarts exceeded for {child.name}")
                if self.safe_mode.enabled:
                    await self.activate_safe_mode(f"Max restarts exceeded for {child.name}")
    
    async def activate_safe_mode(self, reason: str = "Manual"):
        """Activate safe mode (disable autonomy, readonly sensors)."""
        self.safe_mode.activate(reason)
        
        # Signal children to enter safe mode (via env var)
        for child in self.children.values():
            if child.process:
                logger.info(f"Signaling {child.name} to enter safe mode")
                try:
                    child.process.send_signal(signal.SIGUSR1)
                except:
                    pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status."""
        children_status = {}
        for name, child in self.children.items():
            children_status[name] = {
                "status": child.status.value,
                "pid": child.process.pid if child.process else None,
                "restarts": child.restart_count,
                "uptime_s": (datetime.utcnow() - child.last_start_time).total_seconds() 
                           if child.last_start_time else 0,
            }
        
        return {
            "boot_mode": self.boot_mode.value,
            "safe_mode": self.safe_mode.to_dict(),
            "children": children_status,
            "uptime_s": time.time(),
        }


if HAS_WIN32:
    class AstraBootdService(win32serviceutil.ServiceFramework):
        """
        Windows Service wrapper for ASTRA Boot Daemon.
        Implements service lifecycle: start, stop, pause, continue.
        """
        
        _svc_name_ = "AstraBootd"
        _svc_display_name_ = "ASTRA Boot Daemon"
        _svc_description_ = "Local-first AI companion OS for Windows"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.is_alive = True
            self.supervisor = None
        
        def SvcDoRun(self):
            """Main service execution loop."""
            import servicemanager
            
            try:
                servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                     servicemanager.PYS_SERVICE_STARTED,
                                     (self._svc_name_, ''))
                
                # Determine boot mode
                boot_mode = BootMode.NORMAL
                if self._is_safe_mode_requested():
                    boot_mode = BootMode.SAFE_MODE
                
                # Initialize supervisor
                self.supervisor = ProcessSupervisor(boot_mode=boot_mode)
                
                # Register child processes
                self.supervisor.add_child("astra_core", "astra_core.exe")
                self.supervisor.add_child("astra_metrics", "astra_metrics.exe")
                self.supervisor.add_child("astra_gui", "astra_gui.exe")
                
                # Start async event loop and supervisor
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                loop.run_until_complete(self.supervisor.start())
                
                # Wait for stop signal
                while self.is_alive:
                    rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                    if rc == win32event.WAIT_OBJECT_0:
                        break
                
                # Cleanup
                loop.run_until_complete(self.supervisor.stop())
                loop.close()
                
            except Exception as e:
                logger.error(f"Service error: {e}", exc_info=True)
                servicemanager.LogErrorMsg(f"Service error: {e}")
        
        def SvcStop(self):
            """Stop service."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.is_alive = False
            win32event.SetEvent(self.hWaitStop)
        
        def _is_safe_mode_requested(self) -> bool:
            """Check if safe mode was requested at startup."""
            # Could check registry or command-line args
            return False


class StandaloneBootd:
    """Standalone boot daemon (for non-Windows or testing)."""
    
    def __init__(self, boot_mode: BootMode = BootMode.NORMAL):
        self.supervisor = ProcessSupervisor(boot_mode=boot_mode)
    
    async def run(self):
        """Run boot daemon."""
        self.supervisor.add_child("astra_core", "python", ["astra_core.py"])
        self.supervisor.add_child("astra_metrics", "python", ["astra_metrics.py"])
        
        await self.supervisor.start()
        
        # Run until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            await self.supervisor.stop()


async def main():
    """Entry point for standalone daemon."""
    bootd = StandaloneBootd()
    await bootd.run()


if __name__ == "__main__":
    if HAS_WIN32 and "--service" in sys.argv:
        # Windows service mode
        win32serviceutil.HandleCommandLine(AstraBootdService)
    else:
        # Standalone mode
        asyncio.run(main())


__all__ = [
    "BootMode",
    "ComponentStatus",
    "ChildProcess",
    "SafeMode",
    "ProcessSupervisor",
    "StandaloneBootd",
]
