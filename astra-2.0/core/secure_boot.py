"""
ASTRA Secure Boot System
"""
import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from .divine_lock import get_divine_lock
from .orchestrator import get_orchestrator
from .backup import get_backup_manager
from .offline_mode import get_offline_mode
from .audit import get_audit_logger
from .plugins import get_plugin_manager

logger = logging.getLogger("astra.secure_boot")

class BootState(str, Enum):
    """ASTRA boot states"""
    DORMANT = "DORMANT"
    AWAKENING = "AWAKENING"
    SOVEREIGN = "SOVEREIGN"
    PROTECTED = "PROTECTED"
    EMERGENCY = "EMERGENCY"

@dataclass
class SecurityProfile:
    """Security configuration"""
    offline_mode: bool = False
    gui_enabled: bool = True
    max_memory_mb: int = 4096
    allowed_plugins: bool = True
    debug_mode: bool = False
    creator_verified: bool = False

class SecureBoot:
    """ASTRA secure boot system"""
    
    def __init__(self) -> None:
        self.state = BootState.DORMANT
        self.security_profile = SecurityProfile()
        self.orchestrator = get_orchestrator()
        self.divine_lock = get_divine_lock()
        self.backup_manager = get_backup_manager()
        self.offline_mode = get_offline_mode()
        self.audit_logger = get_audit_logger()
        self.plugin_manager = get_plugin_manager()
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize secure boot system"""
        try:
            # Set security profile
            self.security_profile = SecurityProfile(**config)
            
            # Activate offline mode if configured
            if self.security_profile.offline_mode:
                self.offline_mode.activate()
                
            # Initialize Divine Lock
            if not self.divine_lock.state.creator_key:
                if "creator_password" not in config:
                    raise ValueError("Creator password required for initialization")
                self.divine_lock.initialize(config["creator_password"])
                
            # Start orchestrator
            await self.orchestrator.start()
            
            # Initialize backup system
            await self.backup_manager.start()
            
            # Log boot
            await self.audit_logger.log_event(
                "system_boot",
                "ASTRA secure boot initialized",
                "INFO"
            )
            
            # Load authorized plugins
            if self.security_profile.allowed_plugins:
                self._load_authorized_plugins()
                
            return True
            
        except Exception as e:
            logger.error(f"Secure boot initialization failed: {str(e)}")
            await self.enter_emergency_state("Boot initialization failed")
            return False
            
    async def verify_creator(self, password: str) -> bool:
        """Verify creator credentials"""
        try:
            if self.divine_lock.verify_creator(password):
                self.security_profile.creator_verified = True
                await self.audit_logger.log_event(
                    "creator_verified",
                    "Creator authentication successful",
                    "INFO"
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Creator verification failed: {str(e)}")
            return False
            
    async def change_state(self, new_state: BootState) -> bool:
        """Change boot state"""
        try:
            old_state = self.state
            self.state = new_state
            
            await self.audit_logger.log_event(
                "state_change",
                f"Boot state changed: {old_state} -> {new_state}",
                "INFO"
            )
            
            # Handle state-specific actions
            if new_state == BootState.SOVEREIGN:
                if not self.security_profile.creator_verified:
                    raise ValueError("Creator verification required for SOVEREIGN")
                    
            elif new_state == BootState.PROTECTED:
                # Activate enhanced security
                if not self.offline_mode.is_active:
                    self.offline_mode.activate()
                    
            elif new_state == BootState.EMERGENCY:
                await self.enter_emergency_state("State change to EMERGENCY")
                
            return True
            
        except Exception as e:
            logger.error(f"State change failed: {str(e)}")
            return False
            
    async def enter_emergency_state(self, reason: str) -> None:
        """Enter emergency state"""
        try:
            # Activate Divine Lock
            await self.divine_lock.activate_lock(reason)
            
            # Force offline mode
            self.offline_mode.activate()
            
            # Stop non-critical services
            if self.security_profile.allowed_plugins:
                self._unload_all_plugins()
                
            # Create emergency backup
            await self.backup_manager.create_backup("core", force=True)
            
            # Log emergency
            await self.audit_logger.log_event(
                "emergency",
                f"Emergency state entered: {reason}",
                "CRITICAL"
            )
            
            self.state = BootState.EMERGENCY
            
        except Exception as e:
            logger.error(f"Emergency state transition failed: {str(e)}")
            
    def _load_authorized_plugins(self) -> None:
        """Load authorized plugins"""
        try:
            for plugin in self.plugin_manager.list_plugins():
                if plugin.name.startswith("astra_"):
                    self.plugin_manager.load_plugin(plugin.name)
                    
        except Exception as e:
            logger.error(f"Plugin loading failed: {str(e)}")
            
    def _unload_all_plugins(self) -> None:
        """Unload all plugins"""
        try:
            for plugin in self.plugin_manager.list_plugins():
                self.plugin_manager.unload_plugin(plugin.name)
                
        except Exception as e:
            logger.error(f"Plugin unloading failed: {str(e)}")

_instance = None

def get_secure_boot() -> SecureBoot:
    """Get secure boot singleton"""
    global _instance
    if _instance is None:
        _instance = SecureBoot()
    return _instance