"""
Memory quota management for user isolation.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import json
import structlog
from prometheus_client import Counter, Gauge

logger = structlog.get_logger(__name__)

# Metrics
QUOTA_EXCEEDED = Counter(
    "astra_memory_quota_exceeded_total",
    "Number of quota exceeded events",
    ["user_id"]
)

MEMORY_USAGE = Gauge(
    "astra_memory_usage_bytes",
    "Current memory usage per user",
    ["user_id"]
)

from .config import config as auth_config

class QuotaManager:
    """Manages memory quotas per user."""
    
    def __init__(self):
        """Initialize quota manager."""
        self.max_keys = auth_config.max_keys_per_user
        self.max_value_size = auth_config.max_value_size_bytes
        self.max_total_size = auth_config.max_total_size_bytes
        self._user_sizes: Dict[str, int] = {}
        
    def check_key_quota(self, user_id: str, current_keys: int) -> bool:
        """Check if adding another key would exceed quota.
        
        Args:
            user_id: User identifier
            current_keys: Current number of keys for user
            
        Returns:
            True if quota allows another key, False otherwise
        """
        if current_keys >= self.max_keys:
            QUOTA_EXCEEDED.labels(user_id=user_id).inc()
            logger.warning("key_quota_exceeded",
                         user_id=user_id,
                         current=current_keys,
                         limit=self.max_keys)
            return False
        return True
        
    def check_value_size(self, user_id: str, value: object) -> bool:
        """Check if value size is within quota.
        
        Args:
            user_id: User identifier
            value: Value to check size of
            
        Returns:
            True if value size is within quota, False otherwise
        """
        # Get approximate size of serialized value
        size = len(json.dumps(value).encode('utf-8'))
        
        if size > self.max_value_size:
            QUOTA_EXCEEDED.labels(user_id=user_id).inc()
            logger.warning("value_size_exceeded",
                         user_id=user_id,
                         size=size,
                         limit=self.max_value_size)
            return False
        return True
        
    def check_total_quota(self, user_id: str, new_value: object) -> bool:
        """Check if adding value would exceed total quota.
        
        Args:
            user_id: User identifier
            new_value: Value to be added
            
        Returns:
            True if adding value stays within quota, False otherwise
        """
        new_size = len(json.dumps(new_value).encode('utf-8'))
        current_size = self._user_sizes.get(user_id, 0)
        total_size = current_size + new_size
        
        if total_size > self.max_total_size:
            QUOTA_EXCEEDED.labels(user_id=user_id).inc()
            logger.warning("total_quota_exceeded",
                         user_id=user_id,
                         current=current_size,
                         new=new_size,
                         limit=self.max_total_size)
            return False
            
        return True
        
    def update_usage(self, user_id: str, old_value: Optional[object], new_value: Optional[object]) -> None:
        """Update tracked memory usage for user.
        
        Args:
            user_id: User identifier
            old_value: Previous value being replaced/deleted (if any)
            new_value: New value being added (if any)
        """
        old_size = len(json.dumps(old_value).encode('utf-8')) if old_value else 0
        new_size = len(json.dumps(new_value).encode('utf-8')) if new_value else 0
        
        current = self._user_sizes.get(user_id, 0)
        updated = current - old_size + new_size
        
        self._user_sizes[user_id] = updated
        MEMORY_USAGE.labels(user_id=user_id).set(updated)
        
    def clear_usage(self, user_id: str) -> None:
        """Clear tracked memory usage for user.
        
        Args:
            user_id: User identifier
        """
        if user_id in self._user_sizes:
            del self._user_sizes[user_id]
        MEMORY_USAGE.labels(user_id=user_id).set(0)

# Global quota manager instance        
quota_manager = QuotaManager()