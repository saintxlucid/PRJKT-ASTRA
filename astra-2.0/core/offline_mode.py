"""
ASTRA Emergency Offline Mode
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger("astra.offline_mode")

@dataclass
class OfflineConfig:
    """Offline mode configuration"""
    allowed_endpoints: Set[str]
    max_memory_mb: int
    gui_enabled: bool
    log_level: str

class OfflineMode:
    """ASTRA emergency offline operation system"""
    
    def __init__(self) -> None:
        self.config_file = Path("core/offline_mode.json")
        self.is_active = False
        self.default_config = OfflineConfig(
            allowed_endpoints={"localhost"},
            max_memory_mb=1024,
            gui_enabled=False,
            log_level="WARNING"
        )
        self.config = self.default_config
        self._load_config()
        
    def activate(self) -> bool:
        """Enter offline mode"""
        try:
            if self.is_active:
                return True
                
            # Set restrictive logging
            logging.getLogger("astra").setLevel(
                self.config.log_level
            )
            
            # Limit memory usage
            import resource
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.config.max_memory_mb * 1024 * 1024,) * 2
            )
            
            # Block network access except allowed endpoints
            # This would require firewall integration
            # For now, we just log the intent
            logger.warning(
                f"Network restricted to: {self.config.allowed_endpoints}"
            )
            
            self.is_active = True
            logger.warning("Offline mode activated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate offline mode: {str(e)}")
            return False
            
    def deactivate(self) -> bool:
        """Exit offline mode"""
        try:
            if not self.is_active:
                return True
                
            # Restore normal logging
            logging.getLogger("astra").setLevel(logging.INFO)
            
            # Remove memory limits
            import resource
            resource.setrlimit(
                resource.RLIMIT_AS,
                (resource.RLIM_INFINITY,) * 2
            )
            
            # Restore network access
            logger.info("Network access restored")
            
            self.is_active = False
            logger.info("Offline mode deactivated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate offline mode: {str(e)}")
            return False
            
    def is_endpoint_allowed(self, endpoint: str) -> bool:
        """Check if network endpoint is allowed"""
        if not self.is_active:
            return True
            
        return endpoint in self.config.allowed_endpoints
        
    def update_config(self, config: OfflineConfig) -> bool:
        """Update offline mode configuration"""
        try:
            self.config = config
            self._save_config()
            
            # If active, apply new config
            if self.is_active:
                self.deactivate()
                self.activate()
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to update offline config: {str(e)}")
            return False
            
    def get_config(self) -> OfflineConfig:
        """Get current offline mode configuration"""
        return self.config
        
    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                data = json.loads(self.config_file.read_text())
                self.config = OfflineConfig(
                    allowed_endpoints=set(data["allowed_endpoints"]),
                    max_memory_mb=data["max_memory_mb"],
                    gui_enabled=data["gui_enabled"],
                    log_level=data["log_level"]
                )
        except Exception as e:
            logger.error(f"Failed to load offline config: {str(e)}")
            self.config = self.default_config
            
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            self.config_file.write_text(
                json.dumps({
                    "allowed_endpoints": list(self.config.allowed_endpoints),
                    "max_memory_mb": self.config.max_memory_mb,
                    "gui_enabled": self.config.gui_enabled,
                    "log_level": self.config.log_level
                })
            )
        except Exception as e:
            logger.error(f"Failed to save offline config: {str(e)}")

_instance = None

def get_offline_mode() -> OfflineMode:
    """Get offline mode singleton"""
    global _instance
    if _instance is None:
        _instance = OfflineMode()
    return _instance