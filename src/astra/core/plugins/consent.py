"""
Permission consent management for plugins.
Handles user authorization of plugin permission requests.
"""
from __future__ import annotations

import asyncio
from typing import Optional, Set
import structlog
from pathlib import Path
import json

from .ui.interface import UIProvider, PermissionRequest, ConsentResponse

logger = structlog.get_logger()

class ConsentManager:
    """
    Manages user consent for plugin permissions.
    Provides UI prompts and persistence of consent decisions.
    """
    
    def __init__(
        self,
        storage_path: Path = Path("data/consent"),
        auto_grant: bool = False,
        ui_provider: Optional[UIProvider] = None
    ):
        self.storage_path = storage_path
        self.auto_grant = auto_grant
        self.ui_provider = ui_provider
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_saved_consents()
        
    def _load_saved_consents(self) -> None:
        """Load previously saved consent decisions"""
        self._consents = {}
        consent_file = self.storage_path / "consents.json"
        
        if consent_file.exists():
            try:
                with consent_file.open() as f:
                    self._consents = json.load(f)
            except Exception as e:
                logger.error("Failed to load saved consents", error=str(e))
                
    def _save_consents(self) -> None:
        """Save current consent decisions"""
        consent_file = self.storage_path / "consents.json"
        try:
            with consent_file.open("w") as f:
                json.dump(self._consents, f, indent=2)
        except Exception as e:
            logger.error("Failed to save consents", error=str(e))
            
    def _get_consent_key(
        self,
        plugin_id: str,
        action_name: str,
        permissions: Set[str]
    ) -> str:
        """Generate unique key for consent decision"""
        perms = sorted(permissions)
        return f"{plugin_id}:{action_name}:{','.join(perms)}"
        
    def get_saved_consent(
        self,
        plugin_id: str,
        action_name: str,
        permissions: Set[str]
    ) -> bool:
        """Check if consent was previously granted"""
        key = self._get_consent_key(plugin_id, action_name, permissions)
        return self._consents.get(key, False)
        
    def save_consent(
        self,
        plugin_id: str,
        action_name: str,
        permissions: Set[str],
        granted: bool
    ) -> None:
        """Save a consent decision"""
        key = self._get_consent_key(plugin_id, action_name, permissions)
        self._consents[key] = granted
        self._save_consents()
        
    async def request_consent(
        self,
        plugin_id: str,
        action_name: str,
        permissions: Set[str],
        plugin_name: Optional[str] = None,
        action_description: Optional[str] = None
    ) -> bool:
        """
        Request user consent for plugin permissions
        
        Args:
            plugin_id: Plugin requesting permissions
            action_name: Name of action requiring permissions
            permissions: Set of permission strings
            plugin_name: Optional friendly name of plugin
            action_description: Optional description of action
            
        Returns:
            bool: True if consent granted, False otherwise
        """
        # Check for auto-grant mode
        if self.auto_grant:
            return True
            
        # Check saved consent
        if self.get_saved_consent(plugin_id, action_name, permissions):
            return True
            
        # Use UI provider if available
        if self.ui_provider:
            request = PermissionRequest(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                action_name=action_name,
                action_description=action_description,
                permissions=permissions
            )
            
            response = await self.ui_provider.request_permissions(request)
            
            # Save permanent consent if requested
            if response.remember:
                self.save_consent(
                    plugin_id,
                    action_name,
                    permissions,
                    response.granted
                )
                
            return response.granted
            
        else:
            # Fallback to command line
            perms_list = "\n".join(f"- {p}" for p in sorted(permissions))
            prompt = f"""
Plugin '{plugin_id}' requests permissions for action '{action_name}':

{perms_list}

Allow these permissions? [y/n/a] (y=yes, n=no, a=always allow): """

            # Get user response
            print(prompt, end="", flush=True)
            response = await asyncio.get_event_loop().run_in_executor(
                None, input
            )
            
            granted = response.lower() in ["y", "a"]
            
            # Save permanent consent if requested
            if response.lower() == "a":
                self.save_consent(plugin_id, action_name, permissions, granted)
                
            return granted