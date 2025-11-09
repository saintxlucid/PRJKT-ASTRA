"""
ASTRA-OS Health Monitor Module

Implements component health tracking and recovery.
Provides:
- HealthMonitor: Component health monitoring engine
- ComponentHealth: Health status enum
- HealthMetric: Health metric tracking
- HealthCheck: Health check definition

The HealthMonitor:
- Registers health checks
- Executes periodic health checks
- Tracks component status
- Detects failures
- Triggers recovery
- Generates health reports

Usage:
    monitor = HealthMonitor()
    
    async def check_cpu():
        return psutil.cpu_percent() < 80
    
    monitor.register_component('boot_daemon', check_func=check_cpu)
    
    await monitor.check_all_components()
    status = monitor.get_component_status()
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import traceback

logger = logging.getLogger(__name__)


class ComponentHealth(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class HealthMetric:
    """Health metric measurement."""
    component_id: str
    metric_name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    status: ComponentHealth = ComponentHealth.HEALTHY
    threshold: Optional[float] = None


@dataclass
class HealthCheck:
    """Health check definition."""
    check_id: str
    component_id: str
    check_func: Callable
    interval_seconds: float = 30
    timeout_seconds: float = 10
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: ComponentHealth = ComponentHealth.HEALTHY
    failure_count: int = 0
    failure_threshold: int = 3


@dataclass
class ComponentStatus:
    """Component status tracking."""
    component_id: str
    component_name: str
    health: ComponentHealth = ComponentHealth.HEALTHY
    last_check: Optional[datetime] = None
    uptime_seconds: float = 0.0
    failure_count: int = 0
    recovery_attempts: int = 0
    metrics: List[HealthMetric] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class HealthMonitor:
    """
    Component health monitoring engine for ASTRA-OS.
    
    Responsibilities:
    - Register components for monitoring
    - Execute periodic health checks
    - Track component status
    - Detect failures
    - Trigger recovery
    - Generate health reports
    """

    def __init__(
        self,
        check_interval_seconds: int = 30,
        unhealthy_threshold: int = 3,
        recovery_attempts: int = 3
    ):
        """
        Initialize the Health Monitor.
        
        Args:
            check_interval_seconds: Default interval between checks
            unhealthy_threshold: Failures before marking unhealthy
            recovery_attempts: Recovery attempts per component
        """
        self.components: Dict[str, ComponentStatus] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.check_interval_seconds = check_interval_seconds
        self.unhealthy_threshold = unhealthy_threshold
        self.recovery_attempts = recovery_attempts
        
        self.recovery_handlers: Dict[str, Callable] = {}
        self.health_report_callbacks: List[Callable] = []
        
        self.monitoring = False
        self.total_checks_executed = 0
        self.total_failures_detected = 0
        self.total_recoveries_triggered = 0
        
        logger.info("HealthMonitor initialized")

    async def start_monitoring(self) -> None:
        """Start periodic health monitoring."""
        if self.monitoring:
            logger.warning("Health monitoring already running")
            return

        self.monitoring = True
        logger.info("Starting health monitoring")

        try:
            while self.monitoring:
                await self.check_all_components()
                await asyncio.sleep(self.check_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Health monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")
        finally:
            self.monitoring = False

    async def stop_monitoring(self) -> None:
        """Stop periodic health monitoring."""
        self.monitoring = False
        logger.info("Health monitoring stopped")

    def register_component(
        self,
        component_id: str,
        component_name: str,
        check_func: Callable,
        interval_seconds: Optional[float] = None
    ) -> bool:
        """
        Register a component for health monitoring.
        
        Args:
            component_id: Unique component identifier
            component_name: Human-readable component name
            check_func: Async health check function
            interval_seconds: Check interval (uses default if None)
            
        Returns:
            bool: True if registered successfully
        """
        try:
            if component_id in self.components:
                logger.warning(f"Component already registered: {component_id}")
                return False

            # Create component status
            self.components[component_id] = ComponentStatus(
                component_id=component_id,
                component_name=component_name
            )

            # Create health check
            check_id = f"check_{component_id}"
            self.health_checks[check_id] = HealthCheck(
                check_id=check_id,
                component_id=component_id,
                check_func=check_func,
                interval_seconds=interval_seconds or self.check_interval_seconds
            )

            logger.debug(f"✓ Component registered: {component_id}")
            return True

        except Exception as e:
            logger.error(f"Error registering component: {e}")
            return False

    def unregister_component(self, component_id: str) -> bool:
        """
        Unregister a component from monitoring.
        
        Args:
            component_id: Component identifier
            
        Returns:
            bool: True if unregistered successfully
        """
        try:
            if component_id in self.components:
                del self.components[component_id]
                logger.debug(f"Component unregistered: {component_id}")
            
            # Also remove associated checks
            checks_to_remove = [
                check_id for check_id, check in self.health_checks.items()
                if check.component_id == component_id
            ]
            for check_id in checks_to_remove:
                del self.health_checks[check_id]
            
            return True

        except Exception as e:
            logger.error(f"Error unregistering component: {e}")
            return False

    def register_recovery_handler(self, component_id: str, handler: Callable) -> None:
        """
        Register a recovery handler for a component.
        
        Args:
            component_id: Component identifier
            handler: Recovery handler function (async)
        """
        self.recovery_handlers[component_id] = handler
        logger.debug(f"Recovery handler registered for {component_id}")

    async def check_component(self, component_id: str) -> ComponentHealth:
        """
        Execute health check for a single component.
        
        Args:
            component_id: Component identifier
            
        Returns:
            ComponentHealth: Current health status
        """
        if component_id not in self.components:
            logger.warning(f"Component not found: {component_id}")
            return ComponentHealth.OFFLINE

        component = self.components[component_id]

        try:
            # Find check for this component
            check = None
            for hc in self.health_checks.values():
                if hc.component_id == component_id:
                    check = hc
                    break

            if not check:
                logger.warning(f"No health check for {component_id}")
                return ComponentHealth.OFFLINE

            if not check.enabled:
                return component.health

            # Execute health check with timeout
            try:
                logger.debug(f"Executing health check: {component_id}")
                
                # Execute check function
                if asyncio.iscoroutinefunction(check.check_func):
                    result = await asyncio.wait_for(
                        check.check_func(),
                        timeout=check.timeout_seconds
                    )
                else:
                    result = check.check_func()

                # Interpret result
                if result is True or result >= 0.8:
                    # Component is healthy
                    component.health = ComponentHealth.HEALTHY
                    component.failure_count = 0
                    check.failure_count = 0

                elif result is False or result == 0:
                    # Component is unhealthy
                    check.failure_count += 1
                    component.failure_count += 1

                    if check.failure_count >= self.unhealthy_threshold:
                        component.health = ComponentHealth.UNHEALTHY
                        logger.warning(f"Component unhealthy: {component_id}")
                        self.total_failures_detected += 1

                        # Trigger recovery
                        await self.trigger_recovery(component_id)

                else:
                    # Degraded state
                    component.health = ComponentHealth.DEGRADED

            except asyncio.TimeoutError:
                logger.warning(f"Health check timeout: {component_id}")
                check.failure_count += 1
                component.failure_count += 1

                if check.failure_count >= self.unhealthy_threshold:
                    component.health = ComponentHealth.UNHEALTHY

            except Exception as e:
                logger.error(f"Health check error for {component_id}: {e}")
                check.failure_count += 1
                component.failure_count += 1
                component.error_message = str(e)

                if check.failure_count >= self.unhealthy_threshold:
                    component.health = ComponentHealth.UNHEALTHY

            finally:
                component.last_check = datetime.now()
                self.total_checks_executed += 1

        except Exception as e:
            logger.error(f"Error checking component {component_id}: {e}")
            component.health = ComponentHealth.OFFLINE

        return component.health

    async def check_all_components(self) -> Dict[str, ComponentHealth]:
        """
        Execute health checks for all components.
        
        Returns:
            dict: Component ID -> health status mapping
        """
        results = {}

        try:
            # Execute checks concurrently
            tasks = [
                self.check_component(component_id)
                for component_id in self.components.keys()
            ]

            healths = await asyncio.gather(*tasks, return_exceptions=True)

            for component_id, health in zip(self.components.keys(), healths):
                if isinstance(health, Exception):
                    results[component_id] = ComponentHealth.OFFLINE
                else:
                    results[component_id] = health

        except Exception as e:
            logger.error(f"Error checking all components: {e}")

        return results

    async def trigger_recovery(self, component_id: str) -> bool:
        """
        Trigger recovery for an unhealthy component.
        
        Args:
            component_id: Component identifier
            
        Returns:
            bool: True if recovery attempted
        """
        if component_id not in self.components:
            return False

        component = self.components[component_id]

        if component.recovery_attempts >= self.recovery_attempts:
            logger.error(f"Recovery attempts exhausted for {component_id}")
            return False

        try:
            logger.info(f"Triggering recovery for {component_id}")
            component.recovery_attempts += 1
            self.total_recoveries_triggered += 1

            # Call recovery handler if registered
            if component_id in self.recovery_handlers:
                handler = self.recovery_handlers[component_id]
                
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()

                    logger.info(f"✓ Recovery completed for {component_id}")
                    return True

                except Exception as e:
                    logger.error(f"Recovery handler error for {component_id}: {e}")
                    return False
            else:
                logger.warning(f"No recovery handler for {component_id}")
                return False

        except Exception as e:
            logger.error(f"Error triggering recovery: {e}")
            return False

    def get_component_status(self, component_id: str) -> Optional[ComponentStatus]:
        """
        Get status of a single component.
        
        Args:
            component_id: Component identifier
            
        Returns:
            ComponentStatus: Component status, or None if not found
        """
        return self.components.get(component_id)

    def get_all_component_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all components.
        
        Returns:
            dict: Component ID -> status mapping
        """
        return {
            component_id: {
                'component_name': status.component_name,
                'health': status.health.value,
                'last_check': status.last_check.isoformat() if status.last_check else None,
                'uptime_seconds': status.uptime_seconds,
                'failure_count': status.failure_count,
                'recovery_attempts': status.recovery_attempts,
                'error_message': status.error_message
            }
            for component_id, status in self.components.items()
        }

    def get_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report.
        
        Returns:
            dict: Health report
        """
        total_components = len(self.components)
        healthy = sum(1 for c in self.components.values() if c.health == ComponentHealth.HEALTHY)
        degraded = sum(1 for c in self.components.values() if c.health == ComponentHealth.DEGRADED)
        unhealthy = sum(1 for c in self.components.values() if c.health == ComponentHealth.UNHEALTHY)
        offline = sum(1 for c in self.components.values() if c.health == ComponentHealth.OFFLINE)

        overall_health = ComponentHealth.HEALTHY
        if unhealthy > 0:
            overall_health = ComponentHealth.UNHEALTHY
        elif degraded > 0:
            overall_health = ComponentHealth.DEGRADED
        elif offline > 0:
            overall_health = ComponentHealth.OFFLINE

        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': overall_health.value,
            'total_components': total_components,
            'healthy': healthy,
            'degraded': degraded,
            'unhealthy': unhealthy,
            'offline': offline,
            'health_percentage': (healthy / total_components * 100) if total_components > 0 else 0,
            'total_checks_executed': self.total_checks_executed,
            'total_failures_detected': self.total_failures_detected,
            'total_recoveries_triggered': self.total_recoveries_triggered,
            'components': self.get_all_component_status()
        }

        # Call report callbacks
        try:
            for callback in self.health_report_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(report))
                else:
                    callback(report)
        except Exception as e:
            logger.error(f"Error calling health report callbacks: {e}")

        return report

    def enable_component(self, component_id: str) -> bool:
        """Mark a component as enabled/healthy."""
        if component_id not in self.components:
            return False

        self.components[component_id].health = ComponentHealth.HEALTHY
        self.components[component_id].failure_count = 0
        return True

    def disable_component(self, component_id: str) -> bool:
        """Mark a component as offline."""
        if component_id not in self.components:
            return False

        self.components[component_id].health = ComponentHealth.OFFLINE
        return True

    def register_health_report_callback(self, callback: Callable) -> None:
        """
        Register a callback for health reports.
        
        Args:
            callback: Callback function (report_dict)
        """
        self.health_report_callbacks.append(callback)

    def get_monitor_stats(self) -> Dict[str, Any]:
        """Get health monitor statistics."""
        return {
            'total_components': len(self.components),
            'total_checks': len(self.health_checks),
            'total_checks_executed': self.total_checks_executed,
            'total_failures_detected': self.total_failures_detected,
            'total_recoveries_triggered': self.total_recoveries_triggered,
            'monitoring': self.monitoring,
            'check_interval_seconds': self.check_interval_seconds
        }
