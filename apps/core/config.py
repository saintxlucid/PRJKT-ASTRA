"""
ASTRA-OS Config Manager Module

Implements dynamic configuration management with hot-reload capabilities.
Provides:
- ConfigManager: Configuration management engine
- ConfigSource: Configuration sources (file, env, database)
- ConfigValidator: Configuration validation

The ConfigManager:
- Loads YAML configuration files
- Supports environment variable overrides
- Validates configuration
- Watches for file changes
- Hot-reloads configuration
- Tracks configuration history

Usage:
    config_mgr = ConfigManager()
    config_mgr.load_config('astra.yaml')
    
    value = config_mgr.get('orchestrator.max_queue_size')
    config_mgr.set('orchestrator.max_queue_size', 20000)
    
    await config_mgr.watch_file('astra.yaml')
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
import traceback

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    logger.warning("PyYAML not available")
    YAML_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    logger.warning("Watchdog not available")
    WATCHDOG_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """Configuration sources."""
    FILE = "file"
    ENV = "env"
    DATABASE = "database"
    RUNTIME = "runtime"


@dataclass
class ConfigChange:
    """Configuration change record."""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    changed_by: str = "system"
    source: ConfigSource = ConfigSource.RUNTIME


@dataclass
class ConfigValidator:
    """Configuration validator."""
    key: str
    validator_func: Callable
    required: bool = False


class ConfigManager:
    """
    Dynamic configuration management engine for ASTRA-OS.
    
    Responsibilities:
    - Load configuration from files (YAML)
    - Support environment variable overrides
    - Validate configuration
    - Watch for file changes
    - Hot-reload configuration
    - Track configuration history
    - Merge configurations
    """

    def __init__(self, env_prefix: str = "ASTRA_"):
        """
        Initialize the Config Manager.
        
        Args:
            env_prefix: Prefix for environment variable overrides
        """
        self.config: Dict[str, Any] = {}
        self.env_prefix = env_prefix
        self.validators: Dict[str, ConfigValidator] = {}
        self.change_history: List[ConfigChange] = []
        self.file_path: Optional[str] = None
        self.file_observer: Optional[Observer] = None
        self.reload_callbacks: List[Callable] = []
        self.reload_debounce_ms = 500
        self._pending_reload = False
        self._reload_lock = asyncio.Lock()
        
        logger.info(f"ConfigManager initialized with prefix {env_prefix}")

    def load_config(self, file_path: str) -> bool:
        """
        Load configuration from YAML file.
        
        Args:
            file_path: Path to YAML configuration file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            if not YAML_AVAILABLE:
                logger.error("PyYAML not available, cannot load config file")
                return False

            if not os.path.exists(file_path):
                logger.error(f"Configuration file not found: {file_path}")
                return False

            with open(file_path, 'r') as f:
                file_config = yaml.safe_load(f) or {}

            self.file_path = file_path
            self.config = self._deep_merge(self.config, file_config)

            logger.info(f"✓ Configuration loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.error(traceback.format_exc())
            return False

    def load_from_env(self) -> bool:
        """
        Load configuration from environment variables.
        
        Environment variables should be formatted as:
        ASTRA_ORCHESTRATOR__MAX_QUEUE_SIZE=20000
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            env_config = {}

            for key, value in os.environ.items():
                if key.startswith(self.env_prefix):
                    # Remove prefix and convert to config key
                    config_key = key[len(self.env_prefix):].lower().replace('__', '.')
                    
                    # Try to parse as different types
                    if value.lower() in ('true', 'false'):
                        env_config[config_key] = value.lower() == 'true'
                    elif value.isdigit():
                        env_config[config_key] = int(value)
                    else:
                        try:
                            env_config[config_key] = float(value)
                        except ValueError:
                            env_config[config_key] = value

            if env_config:
                self.config = self._deep_merge(self.config, env_config)
                logger.info(f"✓ Loaded {len(env_config)} environment variables")
                return True

            return True

        except Exception as e:
            logger.error(f"Failed to load environment configuration: {e}")
            return False

    async def watch_file(self) -> None:
        """
        Watch configuration file for changes and hot-reload.
        
        This runs as a background task.
        """
        if not self.file_path:
            logger.warning("No configuration file to watch")
            return

        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog not available, file watching disabled")
            return

        try:
            logger.info(f"Watching configuration file: {self.file_path}")

            class ConfigFileHandler(FileSystemEventHandler):
                def __init__(self, config_mgr):
                    self.config_mgr = config_mgr

                def on_modified(self, event):
                    if event.src_path.endswith(os.path.basename(self.config_mgr.file_path)):
                        logger.debug("Configuration file modified")
                        asyncio.create_task(self.config_mgr._schedule_reload())

            observer = Observer()
            handler = ConfigFileHandler(self)
            
            watch_dir = os.path.dirname(os.path.abspath(self.file_path))
            observer.schedule(handler, watch_dir, recursive=False)
            observer.start()

            self.file_observer = observer
            logger.info("✓ Configuration file watching enabled")

            # Keep watching
            while True:
                await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"Error watching configuration file: {e}")

    async def _schedule_reload(self) -> None:
        """Schedule a configuration reload with debouncing."""
        self._pending_reload = True

        await asyncio.sleep(self.reload_debounce_ms / 1000.0)

        if self._pending_reload:
            self._pending_reload = False
            await self.reload()

    async def reload(self) -> bool:
        """
        Hot-reload configuration from file and environment.
        
        Returns:
            bool: True if reload successful
        """
        async with self._reload_lock:
            try:
                old_config = self.config.copy()

                # Reload from file and env
                self.load_config(self.file_path or '')
                self.load_from_env()

                # Call reload callbacks
                for callback in self.reload_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(old_config, self.config)
                        else:
                            callback(old_config, self.config)
                    except Exception as e:
                        logger.error(f"Error in reload callback: {e}")

                logger.info("✓ Configuration reloaded")
                return True

            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")
                return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (dot notation).
        
        Args:
            key: Configuration key (e.g., 'orchestrator.max_queue_size')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            keys = key.split('.')
            value = self.config

            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default

            return value if value is not None else default

        except Exception as e:
            logger.error(f"Error getting config key {key}: {e}")
            return default

    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> bool:
        """
        Set configuration value by key (dot notation).
        
        Args:
            key: Configuration key
            value: New value
            source: Configuration source
            
        Returns:
            bool: True if set successfully
        """
        try:
            old_value = self.get(key)

            keys = key.split('.')
            config = self.config

            # Navigate/create nested structure
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            # Set value
            config[keys[-1]] = value

            # Record change
            self.change_history.append(ConfigChange(
                key=key,
                old_value=old_value,
                new_value=value,
                source=source
            ))

            logger.debug(f"✓ Config updated: {key} = {value}")
            return True

        except Exception as e:
            logger.error(f"Error setting config key {key}: {e}")
            return False

    def register_validator(self, key: str, validator_func: Callable, required: bool = False) -> bool:
        """
        Register a configuration validator.
        
        Args:
            key: Configuration key
            validator_func: Validator function (returns bool)
            required: Whether key is required
            
        Returns:
            bool: True if registered
        """
        try:
            self.validators[key] = ConfigValidator(
                key=key,
                validator_func=validator_func,
                required=required
            )
            logger.debug(f"✓ Validator registered for {key}")
            return True

        except Exception as e:
            logger.error(f"Error registering validator: {e}")
            return False

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []

        try:
            for key, validator in self.validators.items():
                value = self.get(key)

                if value is None:
                    if validator.required:
                        errors.append(f"Required key missing: {key}")
                else:
                    if not validator.validator_func(value):
                        errors.append(f"Validation failed for {key}: {value}")

            is_valid = len(errors) == 0
            return is_valid, errors

        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return False, [str(e)]

    def register_reload_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when configuration reloads.
        
        Args:
            callback: Callback function (old_config, new_config)
        """
        self.reload_callbacks.append(callback)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()

    def get_config_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get configuration change history.
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            list: Change history
        """
        return [
            {
                'key': change.key,
                'old_value': change.old_value,
                'new_value': change.new_value,
                'timestamp': change.timestamp.isoformat(),
                'source': change.source.value
            }
            for change in self.change_history[-limit:]
        ]

    def export_config(self, file_path: str) -> bool:
        """
        Export configuration to YAML file.
        
        Args:
            file_path: Path to export to
            
        Returns:
            bool: True if exported successfully
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML not available, cannot export config")
            return False

        try:
            with open(file_path, 'w') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)

            logger.info(f"✓ Configuration exported to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            dict: Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result
