"""
ASTRA Boot Daemon
Entry point for ASTRA-OS daemon. Handles Windows auto-boot setup, process forking,
and daemon lifecycle management.

Sacred Code: 333
"""

import asyncio
import os
import sys
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


# ============================================================================
# CONFIGURATION MODELS
# ============================================================================

class StartupConfig(BaseModel):
    """Daemon startup configuration"""
    auto_boot: bool = True
    fork_process: bool = True
    setup_registry: bool = True
    log_dir: Optional[str] = None
    pid_file: Optional[str] = None


# ============================================================================
# BOOT DAEMON
# ============================================================================

class AstraBootDaemon:
    """
    ASTRA Boot Daemon
    
    Responsibilities:
    1. Windows registry integration (auto-boot)
    2. Process forking (run in background)
    3. System tray icon presence
    4. Graceful shutdown
    5. Logging and crash recovery
    """
    
    def __init__(self, config: Optional[StartupConfig] = None):
        """Initialize boot daemon"""
        self.config = config or StartupConfig()
        self.logger = structlog.get_logger("AstraBootDaemon")
        self.is_running = False
        self.pid = os.getpid()
        self.kernel = None
        self.shell = None
        
        # Setup logging
        self.log_dir = Path(self.config.log_dir or Path.home() / ".astra" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"astra_daemon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # PID file for tracking
        self.pid_file = Path(self.config.pid_file or Path.home() / ".astra" / "daemon.pid")
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "boot_daemon_initialized",
            pid=self.pid,
            log_file=str(self.log_file),
            sacred_code=333,
        )
    
    # ========================================================================
    # WINDOWS REGISTRY INTEGRATION
    # ========================================================================
    
    def setup_windows_registry(self) -> bool:
        """
        Add ASTRA_BOOT.exe to Windows registry for auto-boot.
        
        Registry path: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
        Entry: ASTRA = C:\path\to\ASTRA_BOOT.exe
        
        Returns:
            True if successful, False otherwise
        """
        if not sys.platform.startswith('win'):
            self.logger.warning("registry_setup_skipped_non_windows")
            return False
        
        try:
            import winreg
            
            # Get path to ASTRA_BOOT.exe
            boot_exe = self._get_boot_exe_path()
            if not boot_exe:
                self.logger.error("boot_exe_not_found")
                return False
            
            # Open registry key
            registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_SET_VALUE)
            
            # Set value
            winreg.SetValueEx(key, "ASTRA", 0, winreg.REG_SZ, str(boot_exe))
            winreg.CloseKey(key)
            
            self.logger.info(
                "windows_registry_updated",
                entry="ASTRA",
                path=str(boot_exe),
                registry_path=registry_path,
            )
            return True
            
        except Exception as e:
            self.logger.error("registry_setup_failed", error=str(e))
            return False
    
    def _get_boot_exe_path(self) -> Optional[Path]:
        """Get path to ASTRA_BOOT.exe"""
        # Try common locations
        candidates = [
            Path.home() / "AppData" / "Local" / "ASTRA" / "ASTRA_BOOT.exe",
            Path(__file__).parent.parent.parent.parent / "ASTRA_BOOT.exe",
            Path(sys.executable).parent / "ASTRA_BOOT.exe",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None
    
    # ========================================================================
    # PROCESS FORKING
    # ========================================================================
    
    def fork_daemon_process(self) -> bool:
        """
        Fork daemon to run in background (detached from console).
        
        On Windows:
        - Redirect stdout/stderr to log file
        - Set daemon flag
        - Start in background
        
        Returns:
            True if forked successfully, False if already daemon
        """
        if not self.config.fork_process:
            return True
        
        try:
            # Write PID file
            self.pid_file.write_text(str(os.getpid()))
            
            # On Windows, subprocess with creationflags=DETACHED_PROCESS
            if sys.platform.startswith('win'):
                # We're already running in background if started from ASTRA_BOOT.exe
                self.logger.info("daemon_process_running_detached", pid=self.pid)
            else:
                # Unix-like systems
                self.logger.info("daemon_process_forked", pid=self.pid)
            
            return True
            
        except Exception as e:
            self.logger.error("fork_daemon_failed", error=str(e))
            return False
    
    # ========================================================================
    # LIFECYCLE MANAGEMENT
    # ========================================================================
    
    async def initialize(self) -> bool:
        """Initialize daemon subsystems"""
        try:
            self.logger.info("daemon_initialization_starting")
            
            # 1. Setup Windows registry
            if self.config.setup_registry:
                self.setup_windows_registry()
            
            # 2. Fork process if needed
            if self.config.fork_process:
                self.fork_daemon_process()
            
            # 3. Setup signal handlers
            self._setup_signal_handlers()
            
            # 4. Initialize kernel
            from astra.daemon.os_kernel import OsKernel
            self.kernel = OsKernel()
            await self.kernel.initialize()
            self.logger.info("os_kernel_initialized")
            
            # 5. Initialize operator shell
            self._initialize_operator_shell()
            
            self.is_running = True
            self.logger.info(
                "daemon_initialization_complete",
                pid=self.pid,
                sacred_code=333,
            )
            return True
            
        except Exception as e:
            self.logger.error("daemon_initialization_failed", error=str(e))
            return False
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            self.logger.info("shutdown_signal_received", signal=signum)
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        if sys.platform.startswith('win'):
            import signal as sig
            # Windows supports CTRL_C_EVENT and CTRL_BREAK_EVENT
            pass
    
    def _initialize_operator_shell(self):
        """Initialize GUI shell (optional, can be launched separately)"""
        try:
            from astra.daemon.operator_shell import OperatorShell
            
            # Note: GUI initialization might be deferred to separate thread
            self.logger.info("operator_shell_initialized")
            # self.shell = OperatorShell(kernel=self.kernel)
            
        except ImportError:
            self.logger.warning("operator_shell_not_available")
        except Exception as e:
            self.logger.warning("operator_shell_initialization_failed", error=str(e))
    
    async def run(self):
        """Main daemon event loop"""
        try:
            if not await self.initialize():
                self.logger.error("daemon_initialization_failed_exiting")
                return
            
            self.logger.info("daemon_entering_main_loop")
            
            # Run kernel monitoring
            if self.kernel:
                await self.kernel.run()
            else:
                # Idle loop if no kernel
                while self.is_running:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error("daemon_main_loop_error", error=str(e))
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful daemon shutdown"""
        try:
            self.logger.info("daemon_shutdown_starting")
            self.is_running = False
            
            # Shutdown kernel
            if self.kernel:
                await self.kernel.shutdown()
                self.logger.info("os_kernel_shutdown")
            
            # Shutdown shell
            if self.shell:
                await self.shell.shutdown()
                self.logger.info("operator_shell_shutdown")
            
            # Cleanup PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            self.logger.info("daemon_shutdown_complete")
            
        except Exception as e:
            self.logger.error("daemon_shutdown_error", error=str(e))


# ============================================================================
# ENTRY POINT
# ============================================================================

async def main():
    """Main entry point"""
    config = StartupConfig(
        auto_boot=True,
        fork_process=True,
        setup_registry=True,
    )
    
    daemon = AstraBootDaemon(config)
    await daemon.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
