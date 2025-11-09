"""
ASTRA Privacy Protection Protocol (A.P.P.P) Initialization
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .privacy_enforcer import get_privacy_enforcer
from .audit_logger import get_audit_logger
from .model_wrapper import PrivacyAwareModel

logger = logging.getLogger("astra.privacy")

def initialize_privacy_system(config_override: Optional[Dict[str, Any]] = None) -> bool:
    """
    Initialize ASTRA's privacy protection system
    Returns True if initialization successful
    """
    try:
        # Get privacy enforcer
        enforcer = get_privacy_enforcer()
        
        # Apply any config overrides
        if config_override:
            enforcer.config.update(config_override)
        
        # Activate privacy enforcement
        enforcer.enforce_startup()
        
        # Initialize audit logging
        logger = get_audit_logger()
        logger.log_event(
            action="privacy_initialized",
            actor="privacy_system",
            payload={
                "mode": enforcer.config.get("PRIVACY_MODE"),
                "strict_mode": enforcer.in_strict_mode()
            },
            category="system"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize privacy system: {e}")
        return False

def wrap_model(model: Any, model_type: str = "unknown") -> PrivacyAwareModel:
    """
    Wrap an AI model with privacy protection
    """
    return PrivacyAwareModel(model, model_type)