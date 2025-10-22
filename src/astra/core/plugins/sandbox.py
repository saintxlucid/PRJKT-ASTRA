"""
Plugin sandbox runner for ASTRA.
Manages plugin lifecycle, permissions, and execution environment.
"""
from __future__ import annotations

import asyncio
import atexit
import gc
import importlib.util
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type
from uuid import UUID, uuid4
import structlog
import jsonschema

from .audit import AuditLogger, PluginAction
from .consent import ConsentManager
from .exceptions import (
    PluginLoadError,
    PluginPermissionError,
    PluginRuntimeError,
    PluginValidationError
)

logger = structlog.get_logger()

@dataclass
class PluginMetadata:
    """Plugin metadata from manifest"""
    id: str
    version: str
    name: Optional[str] = None
    description: Optional[str] = None

@dataclass
class ActionMetadata:
    """Plugin action metadata"""
    name: str
    description: str
    permissions: Set[str]
    parameters: Optional[Dict] = None
    return_type: Optional[Dict] = None

class PluginContext:
    """Runtime context for plugin execution"""
    
    def __init__(
        self,
        plugin_id: str,
        storage_path: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ):
        self.id = plugin_id
        self.instance_id = str(uuid4())
        self.storage_path = storage_path
        self.env = env or {}
        self._permissions: Set[str] = set()
        
    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission"""
        return permission in self._permissions
        
    def grant_permission(self, permission: str) -> None:
        """Grant a permission to this context"""
        self._permissions.add(permission)
        
    def revoke_permission(self, permission: str) -> None:
        """Revoke a permission from this context"""
        self._permissions.discard(permission)

class PluginSandbox:
    """
    Plugin sandbox environment.
    Manages plugin loading, permission checks, and execution isolation.
    """
    
    # ABI version support
    MIN_ABI_VERSION = "1.0"
    MAX_ABI_VERSION = "1.0"
    
    def __init__(
        self,
        plugin_path: Path,
        storage_base: Optional[Path] = None,
        audit_logger: Optional[AuditLogger] = None,
        consent_manager: Optional[ConsentManager] = None
    ):
        self.plugin_path = plugin_path
        self.storage_base = storage_base or Path("data/plugins")
        self.audit_logger = audit_logger or AuditLogger()
        self.consent_manager = consent_manager or ConsentManager()
        
        # State tracking
        self._start_time = None
        self._memory_high = 0
        self._last_gc = time.monotonic()
        
        # Load plugin manifest and validate schema
        self.manifest = self._load_manifest()
        self._validate_manifest()
        self._validate_abi_version()
        
        # Initialize metadata
        self.metadata = PluginMetadata(
            id=self.manifest["id"],
            version=self.manifest["version"],
            name=self.manifest.get("name"),
            description=self.manifest.get("description")
        )
        
        # Parse capabilities
        self.actions = self._parse_actions()
        
        # Initialize empty state
        self.context = None
        self.module = None
        self.instance = None
        
    def _load_manifest(self) -> Dict[str, Any]:
        """Load and parse plugin manifest"""
        manifest_path = self.plugin_path / "manifest.json"
        if not manifest_path.exists():
            raise PluginLoadError(f"Missing manifest.json in {self.plugin_path}")
            
        try:
            with manifest_path.open() as f:
                return json.load(f)
        except Exception as e:
            raise PluginLoadError(f"Failed to load manifest: {e}")
            
    def _validate_manifest(self) -> None:
        """Validate manifest against ABI schema"""
        schema_path = Path(__file__).parent / "schema/abi_v1.json"
        try:
            with schema_path.open() as f:
                schema = json.load(f)
            jsonschema.validate(self.manifest, schema)
        except Exception as e:
            raise PluginValidationError(f"Invalid manifest: {e}")
            
    def _validate_abi_version(self) -> None:
        """Validate plugin's ABI version compatibility"""
        capabilities = self.manifest["capabilities"]
        min_abi = capabilities.get("minAbiVersion", "1.0")
        max_abi = capabilities.get("maxAbiVersion", "1.0")
        
        if self._version_lt(self.MAX_ABI_VERSION, min_abi):
            raise PluginValidationError(
                f"Plugin requires minimum ABI version {min_abi}, "
                f"but runtime only supports up to {self.MAX_ABI_VERSION}"
            )
            
        if self._version_lt(max_abi, self.MIN_ABI_VERSION):
            raise PluginValidationError(
                f"Plugin supports maximum ABI version {max_abi}, "
                f"but runtime requires at least {self.MIN_ABI_VERSION}"
            )
                
    def _version_lt(self, ver1: str, ver2: str) -> bool:
        """Compare dot-separated version strings"""
        v1_parts = [int(x) for x in ver1.split(".")]
        v2_parts = [int(x) for x in ver2.split(".")]
        return v1_parts < v2_parts
            
    def _check_resource_limits(self) -> None:
        """Check if plugin is within resource limits"""
        # Check execution time
        if self._start_time:
            runtime = time.monotonic() - self._start_time
            timeout = self.manifest["capabilities"].get("timeout", 30)
            if runtime > timeout:
                raise PluginRuntimeError(
                    f"Plugin exceeded time limit of {timeout}s"
                )
        
        # Check memory usage and run GC if needed
        try:
            mem_limit = self.manifest["capabilities"].get("memoryLimit", 512) * 1024 * 1024
            used_memory = 0
            
            # Trigger collection to get accurate memory
            if time.monotonic() - self._last_gc > 1.0:
                gc.collect()
                self._last_gc = time.monotonic()
            
            # Get memory from garbage collector stats
            for obj in gc.get_objects():
                try:
                    used_memory += sys.getsizeof(obj)
                except:
                    continue
            
            if used_memory > mem_limit:
                raise PluginRuntimeError(
                    f"Plugin exceeded memory limit of {mem_limit//(1024*1024)}MB"
                )
            
            self._memory_high = max(self._memory_high, used_memory)
            
        except Exception as e:
            logger.warning(f"Failed to check memory usage: {e}")
            
    def _parse_actions(self) -> Dict[str, ActionMetadata]:
        """Parse action definitions from manifest"""
        actions = {}
        for action in self.manifest["capabilities"]["actions"]:
            actions[action["name"]] = ActionMetadata(
                name=action["name"],
                description=action["description"],
                permissions=set(action["permissions"]),
                parameters=action.get("parameters"),
                return_type=action.get("returnType")
            )
        return actions
        
    async def load(self) -> None:
        """Load plugin module and create instance"""
        try:
            # Reset state
            self._start_time = time.monotonic()
            self._memory_high = 0
            self._last_gc = self._start_time
            
            # Import plugin module
            sys.path.insert(0, str(self.plugin_path))
            spec = importlib.util.spec_from_file_location(
                f"plugin_{self.metadata.id}",
                self.plugin_path / "plugin.py"
            )
            if not spec or not spec.loader:
                raise PluginLoadError("Failed to create module spec")
                
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
            
            # Validate plugin class
            plugin_class = getattr(self.module, "Plugin", None)
            if not plugin_class:
                raise PluginLoadError("Plugin class not found")
                
            # Create plugin context
            storage_path = self.storage_base / self.metadata.id if self.storage_base else None
            self.context = PluginContext(
                plugin_id=self.metadata.id,
                storage_path=storage_path,
                env=os.environ.copy()
            )
            
            # Register cleanup
            atexit.register(self._emergency_cleanup)
            
            # Create plugin instance with resource checks
            try:
                self._check_resource_limits()
                self.instance = plugin_class()
                self._check_resource_limits()
            except Exception as e:
                self._emergency_cleanup()
                raise PluginLoadError(f"Failed to create plugin instance: {e}")
            
            # Initialize plugin
            if hasattr(self.instance, "initialize"):
                try:
                    await asyncio.wait_for(
                        self.instance.initialize(self.context),
                        timeout=self.manifest["capabilities"].get("timeout", 30)
                    )
                    self._check_resource_limits()
                except asyncio.TimeoutError:
                    self._emergency_cleanup()
                    raise PluginLoadError("Plugin initialization timed out")
                except Exception as e:
                    self._emergency_cleanup()
                    raise PluginLoadError(f"Plugin initialization failed: {e}")
                
            logger.info(
                "Plugin loaded",
                id=self.metadata.id,
                version=self.metadata.version,
                peak_memory_mb=self._memory_high / 1024
            )
            
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin: {e}")
            
    def _emergency_cleanup(self) -> None:
        """Emergency cleanup when plugin must be terminated"""
        try:
            if self.instance and hasattr(self.instance, "cleanup"):
                # Run cleanup synchronously in emergency
                asyncio.get_event_loop().run_until_complete(
                    self.instance.cleanup()
                )
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
            
        self.instance = None
        self.context = None
        self.module = None
        
        # Unregister cleanup
        atexit.unregister(self._emergency_cleanup)
        
        # Force garbage collection
        gc.collect()
            
    async def unload(self) -> None:
        """Unload plugin and cleanup"""
        if self.instance and hasattr(self.instance, "cleanup"):
            try:
                await asyncio.wait_for(
                    self.instance.cleanup(),
                    timeout=self.manifest["capabilities"].get("timeout", 30)
                )
            except asyncio.TimeoutError:
                logger.error("Plugin cleanup timed out")
            except Exception as e:
                logger.error(f"Plugin cleanup error: {e}")
                
        # Clear plugin state
        self.instance = None
        self.context = None
        self.module = None
        
        # Unregister cleanup
        atexit.unregister(self._emergency_cleanup)
        
        # Remove from sys.path
        if str(self.plugin_path) in sys.path:
            sys.path.remove(str(self.plugin_path))
            
        # Force garbage collection
        gc.collect()
            
        logger.info(
            "Plugin unloaded",
            id=self.metadata.id,
            peak_memory_mb=self._memory_high / 1024
        )
        
    async def call_action(
        self,
        action_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Call a plugin action with permission checks and audit logging
        
        Args:
            action_name: Name of action to call
            parameters: Action parameters
            
        Returns:
            Action result
        """
        if not self.context or not self.instance:
            raise PluginRuntimeError("Plugin not loaded")
            
        # Verify action exists
        if action_name not in self.actions:
            raise PluginRuntimeError(f"Unknown action: {action_name}")
            
        action = self.actions[action_name]
        
        # Check permissions
        current_permissions = getattr(self.context, "_permissions", set())
        missing_permissions = action.permissions - current_permissions
        
        if missing_permissions:
            # Request consent if possible
            if self.consent_manager:
                try:
                    granted = await self.consent_manager.request_consent(
                        plugin_id=self.metadata.id,
                        plugin_name=self.metadata.name,
                        action_name=action_name,
                        action_description=action.description,
                        permissions=missing_permissions
                    )
                    if granted:
                        for permission in missing_permissions:
                            self.context.grant_permission(permission)
                    else:
                        raise PluginPermissionError(
                            f"Consent denied for permissions: {missing_permissions}"
                        )
                except Exception as e:
                    raise PluginPermissionError(f"Consent error: {e}")
            else:
                raise PluginPermissionError(
                    f"Missing permissions: {missing_permissions}"
                )
                
        # Validate parameters if schema exists
        if action.parameters:
            try:
                jsonschema.validate(parameters or {}, action.parameters)
            except jsonschema.ValidationError as e:
                raise PluginValidationError(f"Invalid parameters: {e}")
                
        # Create audit record
        audit_record = PluginAction(
            plugin_id=self.metadata.id,
            action=action_name,
            parameters=parameters,
            permissions=list(action.permissions)
        )
                
        try:
            # Reset execution timer
            self._start_time = time.monotonic()
            
            # Call action with timeout
            method = getattr(self.instance, action_name)
            result = await asyncio.wait_for(
                method(parameters or {}),
                timeout=self.manifest["capabilities"].get("timeout", 30)
            )
            
            # Check resource usage
            self._check_resource_limits()
            
            # Validate return value if schema exists
            if action.return_type:
                try:
                    jsonschema.validate(result, action.return_type)
                except jsonschema.ValidationError as e:
                    raise PluginValidationError(f"Invalid return value: {e}")
                    
            # Log successful audit with metrics
            metrics_data = {
                "duration_ms": int((time.monotonic() - self._start_time) * 1000),
                "peak_memory_mb": self._memory_high / 1024
            }
            audit_record.success = True
            audit_record.result = result
            # Add metrics to result structure
            if isinstance(audit_record.result, dict):
                audit_record.result["_metrics"] = metrics_data
            else:
                audit_record.result = {"result": result, "_metrics": metrics_data}
            
            await self.audit_logger.log_action(audit_record)
            
            return result
            
        except Exception as e:
            # Log failed audit
            audit_record.success = False
            audit_record.error = str(e)
            await self.audit_logger.log_action(audit_record)
            
            raise PluginRuntimeError(f"Action failed: {e}")
            
    def get_action_metadata(self, action_name: str) -> Optional[ActionMetadata]:
        """Get metadata for a specific action"""
        return self.actions.get(action_name)