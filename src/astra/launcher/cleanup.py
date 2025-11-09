"""
ASTRA Launcher cleanup utilities
Handles graceful shutdown and resource cleanup
"""
import os
import signal
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Set, Optional, Dict, Any
import structlog

logger = structlog.get_logger()

"""
CleanupManager for ASTRA process and file management.
Handles graceful termination and cleanup of processes and temporary files.
"""
import os
import time
import logging
import asyncio
import signal
import shutil
import psutil
from pathlib import Path
import subprocess
from typing import Set, Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

logger = structlog.get_logger()

@dataclass
class CleanupManager:
    """Manages graceful shutdown and cleanup for ASTRA"""
    
    def __init__(self):
        self.temp_files: Set[Path] = set()
        self.processes: Dict[str, subprocess.Popen] = {}
        self.cleanup_tasks: List[Callable[[], None]] = []
        self.is_shutting_down = False
        self.errors: List[Dict[str, Any]] = []
        self._register_signal_handlers()
        
    def add_cleanup_task(self, task: Callable[[], None]) -> None:
        """Add a custom cleanup task to be run during shutdown"""
        self.cleanup_tasks.append(task)
        logger.debug("registered_cleanup_task", task=task.__name__)
        
    def _run_cleanup_tasks(self) -> None:
        """Run registered cleanup tasks"""
        for task in self.cleanup_tasks:
            try:
                task()
            except Exception as e:
                error = {
                    "task": task.__name__,
                    "error": str(e),
                    "type": type(e).__name__
                }
                self.errors.append(error)
                logger.error("cleanup_task_error", **error)
        
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        if os.name == 'nt':  # Windows
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        else:  # Unix
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
            signal.signal(signal.SIGHUP, self._handle_shutdown)
            
    def register_temp_file(self, file_path: Path) -> None:
        """Register a temporary file for cleanup"""
        self.temp_files.add(file_path)
        logger.debug("registered_temp_file", path=str(file_path))
        
    def register_process(self, name: str, process: subprocess.Popen) -> None:
        """Register a subprocess for cleanup"""
        self.processes[name] = process
        logger.debug("registered_process", name=name, pid=process.pid)
        
    def create_temp_file(self, suffix: Optional[str] = None) -> Path:
        """Create and register a temporary file"""
        temp = Path(tempfile.mktemp(suffix=suffix or ""))
        self.register_temp_file(temp)
        return temp
        
    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals"""
        if self.is_shutting_down:
            logger.warning("repeated_shutdown_signal_ignored")
            return
            
        self.is_shutting_down = True
        logger.info("initiating_shutdown", signal_number=signum)
        
        try:
            # Run cleanup tasks first
            self._run_cleanup_tasks()
            
            # Stop all processes
            self._stop_processes()
            
            # Cleanup temp files 
            self._cleanup_files()
            
            if self.errors:
                logger.warning("shutdown_complete_with_errors", error_count=len(self.errors))
            else:
                logger.info("shutdown_complete")
        except Exception as e:
            logger.error("shutdown_error", error=str(e), type=type(e).__name__)
            self.errors.append({
                "task": "shutdown",
                "error": str(e),
                "type": type(e).__name__
            })
        
    def _stop_processes(self) -> None:
        """Stop all registered processes"""
        for name, process in self.processes.items():
            try:
                logger.info("stopping_process", name=name, pid=process.pid)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("process_force_kill", name=name, pid=process.pid)
                    process.kill()
                    process.wait(timeout=2)
            except Exception as e:
                logger.error("process_stop_error", name=name, pid=process.pid, error=str(e))
                
    def _cleanup_files(self) -> None:
        """Clean up all registered temporary files"""
        for tmp in self.temp_files:
            try:
                if tmp.exists():
                    tmp.unlink()
                    logger.debug("cleaned_temp_file", path=str(tmp))
            except Exception as e:
                logger.error("temp_file_cleanup_error", path=str(tmp), error=str(e))
                
    async def cleanup(self) -> None:
        """Run cleanup asynchronously"""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            logger.info("starting_async_cleanup")
            
            try:
                # Run cleanup tasks first
                self._run_cleanup_tasks()
                
                # Stop processes
                self._stop_processes()
                
                # Cleanup files
                self._cleanup_files()
                
                if self.errors:
                    logger.warning("async_cleanup_complete_with_errors", error_count=len(self.errors))
                else:
                    logger.info("async_cleanup_complete")
            except Exception as e:
                logger.error("async_cleanup_error", error=str(e), type=type(e).__name__)
                self.errors.append({
                    "task": "async_cleanup",
                    "error": str(e),
                    "type": type(e).__name__
                })