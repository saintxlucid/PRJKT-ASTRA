"""
CleanupManager for ASTRA launcher.
Handles graceful shutdown and resource cleanup.
"""

import os
import signal
import asyncio
import tempfile
from pathlib import Path
from typing import List, Set, Optional
import subprocess
import structlog

logger = structlog.get_logger()

class CleanupManager:
    """Manages cleanup of processes and resources during shutdown"""
    
    def __init__(self):
        self.processes: Set[subprocess.Popen] = set()
        self.temp_files: Set[Path] = set()
        self.temp_dirs: Set[Path] = set()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup handlers for termination signals"""
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            if hasattr(signal, 'SIGBREAK'):  # Windows Ctrl+Break
                signal.signal(signal.SIGBREAK, self._signal_handler)
        except Exception as e:
            logger.warning("Failed to setup signal handlers", error=str(e))

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, initiating cleanup...")
        asyncio.create_task(self.cleanup())

    def register_process(self, process: subprocess.Popen) -> None:
        """Register a process for cleanup"""
        if process and process.poll() is None:  # Only register running processes
            self.processes.add(process)
            logger.debug("Registered process for cleanup", pid=process.pid)

    def register_temp_file(self, file_path: Path) -> None:
        """Register a temporary file for cleanup"""
        if file_path.exists():
            self.temp_files.add(file_path)
            logger.debug("Registered temp file for cleanup", path=str(file_path))

    def register_temp_dir(self, dir_path: Path) -> None:
        """Register a temporary directory for cleanup"""
        if dir_path.exists():
            self.temp_dirs.add(dir_path)
            logger.debug("Registered temp directory for cleanup", path=str(dir_path))

    def create_temp_file(self, suffix: Optional[str] = None) -> Path:
        """Create and register a temporary file"""
        temp_file = Path(tempfile.mktemp(suffix=suffix))
        self.register_temp_file(temp_file)
        return temp_file

    def create_temp_dir(self) -> Path:
        """Create and register a temporary directory"""
        temp_dir = Path(tempfile.mkdtemp())
        self.register_temp_dir(temp_dir)
        return temp_dir

    async def cleanup(self) -> None:
        """Perform cleanup of all registered resources"""
        logger.info("Starting cleanup...")

        # Clean up processes
        for process in self.processes:
            try:
                if process.poll() is None:  # Process still running
                    logger.info("Terminating process", pid=process.pid)
                    process.terminate()
                    try:
                        await asyncio.sleep(2)  # Give process time to terminate
                        if process.poll() is None:  # If still running
                            process.kill()  # Force kill
                    except Exception as e:
                        logger.error("Error force killing process", pid=process.pid, error=str(e))
            except Exception as e:
                logger.error("Error cleaning up process", pid=process.pid, error=str(e))

        # Clean up temporary files
        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    logger.debug("Removing temp file", path=str(file_path))
                    file_path.unlink()
            except Exception as e:
                logger.error("Error removing temp file", path=str(file_path), error=str(e))

        # Clean up temporary directories
        for dir_path in self.temp_dirs:
            try:
                if dir_path.exists():
                    logger.debug("Removing temp directory", path=str(dir_path))
                    for root, dirs, files in os.walk(dir_path, topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    dir_path.rmdir()
            except Exception as e:
                logger.error("Error removing temp directory", path=str(dir_path), error=str(e))

        logger.info("Cleanup complete")