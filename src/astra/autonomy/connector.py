"""
ASTRA Autonomy Connector
Integrates autonomy core with task system
"""

from typing import Any, Dict, Optional

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from ..core.service_registry import ServiceRegistry
from ..core.settings import Settings
from .autonomy_core import AutonomyCore


class AutonomyConnector:
    """Connector for autonomy core"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize and connect autonomy core"""
        try:
            # Create autonomy core
            core = AutonomyCore(
                check_interval=settings.get("autonomy.check_interval", 1.0),
                min_priority=settings.get("autonomy.min_priority", 1),
                max_priority=settings.get("autonomy.max_priority", 10)
            )
            
            # Add default triggers
            triggers = settings.get("autonomy.default_triggers", [])
            for trigger in triggers:
                core.add_trigger(trigger)
                
            # Start core
            await core.start()
            
            logger.info(
                "autonomy_core_connected",
                triggers=len(triggers)
            )
            return core
            
        except Exception as e:
            logger.error("autonomy_core_connect_failed", error=str(e))
            return None

    @staticmethod 
    def disconnect(instance: Any) -> None:
        """Shutdown autonomy core"""
        if instance:
            await instance.stop()
            logger.info("autonomy_core_disconnected")