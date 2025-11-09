import os
import json
from typing import Dict, Any, Optional

class AICLConfig:
    """Configuration manager for AICL"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.defaults = {
            # Network settings
            "host": "127.0.0.1",
            "port": 5555,
            "max_connections": 8,
            "message_timeout": 30.0,
            "use_tls": False,
            "certfile": None,
            "keyfile": None,
            
            # Security settings
            "max_tokens": 1024,
            "max_latency_ms": 5000,
            "max_payload_size": 100000,
            "max_requests_per_minute": 60,
            "max_requests_per_hour": 1000,
            
            # Logging settings
            "log_dir": "artifacts/conversations",
            "compress_logs": True,
            "log_level": "INFO",
            
            # Performance settings
            "enable_compression": False,
            "compression_level": 3,
            
            # Advanced features
            "enable_streaming": True,
            "stream_chunk_size": 1024,
            "enable_routing": False,
        }
        
        self.config = self.defaults.copy()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or environment"""
        # Load from file if specified
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        
        # Load from environment variables
        for key in self.defaults:
            env_key = f"AICL_{key.upper()}"
            if env_key in os.environ:
                # Convert string values to appropriate types
                value = os.environ[env_key]
                if value.lower() in ('true', 'false'):
                    self.config[key] = value.lower() == 'true'
                elif value.isdigit():
                    self.config[key] = int(value)
                else:
                    try:
                        self.config[key] = float(value)
                    except ValueError:
                        self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def save_config(self, config_file: Optional[str] = None):
        """Save current configuration to file"""
        save_file = config_file or self.config_file
        if save_file:
            try:
                with open(save_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save config file {save_file}: {e}")

# Global configuration instance
config = AICLConfig()