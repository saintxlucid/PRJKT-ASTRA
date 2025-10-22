"""
Configuration management for auth system.
"""

import os
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class AuthConfig:
    """Auth system configuration."""
    
    # Memory quotas
    max_keys_per_user: int = 1000
    max_value_size_bytes: int = 1024 * 1024  # 1MB
    max_total_size_bytes: int = 10 * 1024 * 1024  # 10MB
    
    # Database
    db_path: str = "data/memory.db"
    
    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Create config from environment variables."""
        return cls(
            # Memory quotas
            max_keys_per_user=int(os.getenv("ASTRA_MAX_KEYS_PER_USER", "1000")),
            max_value_size_bytes=int(os.getenv("ASTRA_MAX_VALUE_SIZE_BYTES", str(1024 * 1024))),
            max_total_size_bytes=int(os.getenv("ASTRA_MAX_TOTAL_SIZE_BYTES", str(10 * 1024 * 1024))),
            
            # Database
            db_path=os.getenv("ASTRA_MEMORY_DB_PATH", "data/memory.db")
        )

# Global config instance
config = AuthConfig.from_env()