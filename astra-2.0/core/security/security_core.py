"""
ASTRA Core Security System
Anti-destruction, immunity, and protection protocols
"""
import os
import sys
import time
import json
import hashlib
import logging
import asyncio
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import win32api
import win32con
import win32process
from threading import Lock

logger = logging.getLogger("astra.security")

@dataclass
class SecurityState:
    """Security system state information"""
    immunity_active: bool = False
    self_protect_active: bool = False
    scanner_active: bool = False
    privacy_active: bool = False
    device_protect_active: bool = False
    last_scan_time: float = 0
    threats_detected: int = 0
    integrity_verified: bool = False

class SystemIntegrityMonitor:
    """File and system integrity monitoring"""
    
    CRITICAL_EXTENSIONS = {'.py', '.gguf', '.json', '.pt', '.pth'}
    
    def __init__(self):
        self.file_hashes: Dict[str, str] = {}
        self.protected_paths: Set[str] = set()
        self._hash_lock = Lock()
        
    def protect_path(self, path: str) -> None:
        """Add path to protected list"""
        abs_path = str(Path(path).resolve())
        self.protected_paths.add(abs_path)
        self._hash_files(abs_path)
        
    def verify_integrity(self) -> bool:
        """Verify integrity of all protected files"""
        try:
            with self._hash_lock:
                for path, stored_hash in self.file_hashes.items():
                    if not os.path.exists(path):
                        logger.error(f"Protected file missing: {path}")
                        return False
                        
                    current_hash = self._hash_file(path)
                    if current_hash != stored_hash:
                        logger.error(f"File hash mismatch: {path}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Integrity check failed: {str(e)}")
            return False
            
    def _hash_files(self, path: str) -> None:
        """Hash all files in path"""
        path_obj = Path(path)
        if path_obj.is_file():
            if path_obj.suffix in self.CRITICAL_EXTENSIONS:
                self.file_hashes[str(path_obj)] = self._hash_file(str(path_obj))
        elif path_obj.is_dir():
            for item in path_obj.rglob("*"):
                if item.is_file() and item.suffix in self.CRITICAL_EXTENSIONS:
                    self.file_hashes[str(item)] = self._hash_file(str(item))
                    
    def _hash_file(self, path: str) -> str:
        """Generate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

class SystemProtector:
    """System protection and anti-destruction"""
    
    FORBIDDEN_COMMANDS = {
        'rm', 'del', 'format', 'shutdown', 'rmdir', 'kill',
        'taskkill', 'format', 'fdisk', 'rd', 'remove'
    }
    
    def __init__(self):
        self.original_exit = sys.exit
        self.original_remove = os.remove
        self.original_rmtree = None
        if hasattr(__builtins__, 'exit'):
            self.original_builtin_exit = __builtins__.exit
        
        # Try to import and store shutil.rmtree
        try:
            import shutil
            self.original_rmtree = shutil.rmtree
        except ImportError:
            pass
            
    def activate(self) -> None:
        """Activate system protection"""
        # Override system exit
        sys.exit = self._safe_exit
        if hasattr(__builtins__, 'exit'):
            __builtins__.exit = self._safe_exit
            
        # Override file deletion
        os.remove = self._safe_remove
        
        # Override rmtree if available
        if self.original_rmtree:
            import shutil
            shutil.rmtree = self._safe_rmtree
            
        # Set process priority to high
        try:
            pid = win32api.GetCurrentProcessId()
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
            win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
        except Exception as e:
            logger.error(f"Failed to set process priority: {str(e)}")
            
    def _safe_exit(self, code: int = 0) -> None:
        """Safe system exit handler"""
        logger.warning("System exit attempted - redirecting to safe shutdown")
        # Notify guardian
        from astra.core.sovereign.guardian import get_guardian
        asyncio.run(get_guardian().notify_exit_attempt())
        
    def _safe_remove(self, path: str, **kwargs) -> None:
        """Safe file removal handler"""
        logger.warning(f"File deletion attempted: {path}")
        # Check if path is protected
        if self._is_protected_path(path):
            raise PermissionError(f"Cannot delete protected file: {path}")
            
    def _safe_rmtree(self, path: str, **kwargs) -> None:
        """Safe directory removal handler"""
        logger.warning(f"Directory deletion attempted: {path}")
        if self._is_protected_path(path):
            raise PermissionError(f"Cannot delete protected directory: {path}")
            
    def _is_protected_path(self, path: str) -> bool:
        """Check if path is protected"""
        try:
            abs_path = str(Path(path).resolve())
            core_path = str(Path(__file__).parent.parent)
            return abs_path.startswith(core_path)
        except Exception:
            return True  # Protect by default

class PrivacyGuard:
    """Privacy protection system"""
    
    def __init__(self):
        self.mic_active = False
        self.logging_enabled = False
        self.allowed_endpoints: Set[str] = {'localhost', '127.0.0.1'}
        
    def allow_endpoint(self, endpoint: str) -> None:
        """Add allowed network endpoint"""
        self.allowed_endpoints.add(endpoint)
        
    def verify_endpoint(self, endpoint: str) -> bool:
        """Verify if endpoint is allowed"""
        return endpoint in self.allowed_endpoints
        
    def activate_mic(self) -> None:
        """Safely activate microphone"""
        self.mic_active = True
        
    def deactivate_mic(self) -> None:
        """Safely deactivate microphone"""
        self.mic_active = False
        
    def set_logging(self, enabled: bool) -> None:
        """Set logging state"""
        self.logging_enabled = enabled

class DeviceGuardian:
    """Device-level protection"""
    
    def __init__(self):
        self.max_cpu_percent = 80
        self.max_disk_write = 1000000  # 1MB/s
        self.temp_warning = 80  # Celsius
        self.watch_interval = 1.0  # seconds
        self._monitoring = False
        
    async def start_monitoring(self) -> None:
        """Start device monitoring"""
        self._monitoring = True
        while self._monitoring:
            await self._check_system_state()
            await asyncio.sleep(self.watch_interval)
            
    async def stop_monitoring(self) -> None:
        """Stop device monitoring"""
        self._monitoring = False
        
    async def _check_system_state(self) -> None:
        """Check system state"""
        try:
            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.max_cpu_percent:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                
            # Check disk
            disk_io = psutil.disk_io_counters()
            if disk_io and disk_io.write_bytes > self.max_disk_write:
                logger.warning("High disk write activity detected")
                
            # Check temperature if available
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > self.temp_warning:
                            logger.warning(
                                f"High temperature {entry.current}°C on {name}"
                            )
                            
        except Exception as e:
            logger.error(f"System state check failed: {str(e)}")

class SecurityCore:
    """ASTRA Security Core"""
    
    def __init__(self):
        self.state = SecurityState()
        self.integrity = SystemIntegrityMonitor()
        self.protector = SystemProtector()
        self.privacy = PrivacyGuard()
        self.device = DeviceGuardian()
        
    async def activate_immunity(self) -> bool:
        """Activate full immunity mode"""
        try:
            # Verify integrity
            if not self.integrity.verify_integrity():
                logger.error("System integrity check failed")
                return False
                
            # Activate protections
            self.protector.activate()
            
            # Start device monitoring
            await self.device.start_monitoring()
            
            # Update state
            self.state.immunity_active = True
            logger.info("Immunity mode activated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate immunity: {str(e)}")
            return False
            
    async def deactivate_immunity(self) -> None:
        """Deactivate immunity mode"""
        await self.device.stop_monitoring()
        self.state.immunity_active = False
        
    def protect_core_path(self, path: str) -> None:
        """Add core path to protection"""
        self.integrity.protect_path(path)

_instance = None

def get_security_core() -> SecurityCore:
    """Get security core singleton"""
    global _instance
    if _instance is None:
        _instance = SecurityCore()
    return _instance