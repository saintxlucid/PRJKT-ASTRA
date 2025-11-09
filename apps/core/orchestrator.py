"""
ASTRA-OS Core Orchestrator Module

Implements the central orchestration engine that coordinates all ASTRA-OS components.
Provides:
- RuntimeOrchestrator: Main orchestration controller
- RuntimeState: Runtime execution states
- RuntimeMetrics: Performance metrics tracking

The RuntimeOrchestrator is the entry point for starting and managing the entire
ASTRA-OS runtime, orchestrating all subsystems (Event Bus, Sensors, Memory,
Policies, Tools, Autonomy, Security).

Usage:
    orchestrator = RuntimeOrchestrator()
    await orchestrator.initialize()
    await orchestrator.start()
    
    # System running...
    
    await orchestrator.stop()
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, List, Any
import traceback

logger = logging.getLogger(__name__)


class RuntimeState(Enum):
    """Runtime execution states."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class RuntimeMetrics:
    """Runtime performance metrics."""
    start_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    events_processed: int = 0
    tasks_scheduled: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    avg_event_latency_ms: float = 0.0
    max_event_latency_ms: float = 0.0
    components_healthy: int = 0
    components_degraded: int = 0
    components_unhealthy: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def update_uptime(self) -> None:
        """Update uptime based on start time."""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            self.uptime_seconds = elapsed.total_seconds()
        self.last_updated = datetime.now()


@dataclass
class ComponentStatus:
    """Status of a component."""
    component_id: str
    component_name: str
    state: str  # initialized, running, paused, error, stopped
    health: str  # healthy, degraded, unhealthy, offline
    error_message: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0


class RuntimeOrchestrator:
    """
    Main orchestration controller for ASTRA-OS runtime.
    
    Responsibilities:
    - Initialize all components in correct order
    - Start and manage the event loop
    - Coordinate between all subsystems
    - Handle lifecycle management
    - Emit runtime events to Event Bus
    - Manage graceful shutdown
    - Track metrics and health
    """

    def __init__(self, event_bus=None, config=None):
        """
        Initialize the Runtime Orchestrator.
        
        Args:
            event_bus: EventBus instance for publishing runtime events
            config: Configuration dictionary
        """
        self.event_bus = event_bus
        self.config = config or {}
        self.state = RuntimeState.INITIALIZING
        self.metrics = RuntimeMetrics()
        self.components: Dict[str, ComponentStatus] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.initialized = False
        self.running = False
        self._initialization_order = [
            'boot_daemon',
            'event_bus',
            'sensors',
            'memory',
            'policies',
            'tools',
            'autonomy',
            'sentinel'
        ]
        logger.info("RuntimeOrchestrator initialized")

    async def initialize(self) -> bool:
        """
        Initialize all ASTRA-OS components in the correct order.
        
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        if self.initialized:
            logger.warning("RuntimeOrchestrator already initialized")
            return False

        logger.info("Starting ASTRA-OS initialization sequence...")
        self.state = RuntimeState.INITIALIZING

        try:
            # Initialize each phase system
            for component_name in self._initialization_order:
                logger.debug(f"Initializing {component_name}...")
                
                try:
                    await self._initialize_component(component_name)
                    self.components[component_name] = ComponentStatus(
                        component_id=component_name,
                        component_name=component_name.replace('_', ' ').title(),
                        state='initialized',
                        health='healthy'
                    )
                    logger.info(f"✓ {component_name} initialized")
                except Exception as e:
                    logger.error(f"✗ Failed to initialize {component_name}: {e}")
                    self.components[component_name] = ComponentStatus(
                        component_id=component_name,
                        component_name=component_name.replace('_', ' ').title(),
                        state='error',
                        health='unhealthy',
                        error_message=str(e)
                    )
                    # Continue with other components (graceful degradation)
                    continue

            self.initialized = True
            self.metrics.components_healthy = len(
                [c for c in self.components.values() if c.health == 'healthy']
            )
            
            # Publish initialization event
            if self.event_bus:
                await self._publish_event('runtime/initialized', {
                    'timestamp': datetime.now().isoformat(),
                    'components_initialized': len(self.components),
                    'components_healthy': self.metrics.components_healthy
                })

            logger.info(f"ASTRA-OS initialized with {self.metrics.components_healthy} healthy components")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            logger.error(traceback.format_exc())
            self.state = RuntimeState.STOPPED
            return False

    async def start(self) -> bool:
        """
        Start the ASTRA-OS runtime.
        
        Returns:
            bool: True if start succeeded, False otherwise
        """
        if not self.initialized:
            logger.error("RuntimeOrchestrator not initialized. Call initialize() first.")
            return False

        if self.running:
            logger.warning("RuntimeOrchestrator already running")
            return False

        try:
            logger.info("Starting ASTRA-OS runtime...")
            self.state = RuntimeState.RUNNING
            self.metrics.start_time = datetime.now()
            self.running = True

            # Publish start event
            if self.event_bus:
                await self._publish_event('runtime/started', {
                    'timestamp': datetime.now().isoformat(),
                    'metrics': self._metrics_to_dict()
                })

            logger.info("✓ ASTRA-OS runtime started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start ASTRA-OS runtime: {e}")
            self.state = RuntimeState.STOPPED
            self.running = False
            return False

    async def pause(self) -> bool:
        """
        Pause the ASTRA-OS runtime (keep running for diagnostics).
        
        Returns:
            bool: True if pause succeeded
        """
        if not self.running:
            logger.warning("RuntimeOrchestrator not running")
            return False

        try:
            self.state = RuntimeState.PAUSED
            logger.info("Runtime paused")

            if self.event_bus:
                await self._publish_event('runtime/paused', {
                    'timestamp': datetime.now().isoformat()
                })

            return True
        except Exception as e:
            logger.error(f"Failed to pause runtime: {e}")
            return False

    async def resume(self) -> bool:
        """
        Resume the ASTRA-OS runtime from pause.
        
        Returns:
            bool: True if resume succeeded
        """
        if self.state != RuntimeState.PAUSED:
            logger.warning("RuntimeOrchestrator not paused")
            return False

        try:
            self.state = RuntimeState.RUNNING
            logger.info("Runtime resumed")

            if self.event_bus:
                await self._publish_event('runtime/resumed', {
                    'timestamp': datetime.now().isoformat()
                })

            return True
        except Exception as e:
            logger.error(f"Failed to resume runtime: {e}")
            return False

    async def stop(self) -> bool:
        """
        Gracefully stop the ASTRA-OS runtime.
        
        Returns:
            bool: True if stop succeeded
        """
        if not self.running and self.state == RuntimeState.STOPPED:
            logger.warning("RuntimeOrchestrator already stopped")
            return False

        try:
            logger.info("Initiating graceful shutdown...")
            self.state = RuntimeState.STOPPING

            if self.event_bus:
                await self._publish_event('runtime/stopping', {
                    'timestamp': datetime.now().isoformat()
                })

            # Cancel pending tasks
            for task_name, task in self.tasks.items():
                if not task.done():
                    logger.debug(f"Cancelling task: {task_name}")
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=5.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass

            self.running = False
            self.state = RuntimeState.STOPPED
            self.metrics.update_uptime()

            if self.event_bus:
                await self._publish_event('runtime/stopped', {
                    'timestamp': datetime.now().isoformat(),
                    'uptime_seconds': self.metrics.uptime_seconds,
                    'total_events_processed': self.metrics.events_processed,
                    'total_tasks_completed': self.metrics.tasks_completed
                })

            logger.info("✓ ASTRA-OS runtime stopped gracefully")
            return True

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            self.state = RuntimeState.STOPPED
            return False

    async def recover(self) -> bool:
        """
        Attempt to recover from an error state.
        
        Returns:
            bool: True if recovery succeeded
        """
        if self.state != RuntimeState.RECOVERING and self.running:
            logger.warning("Not in recovery state")
            return False

        try:
            logger.info("Attempting runtime recovery...")
            self.state = RuntimeState.RECOVERING

            # Check component health
            unhealthy = [c for c in self.components.values() if c.health != 'healthy']
            
            for component in unhealthy:
                logger.info(f"Recovering component: {component.component_id}")
                try:
                    await self._recover_component(component.component_id)
                    component.health = 'healthy'
                    component.error_message = None
                except Exception as e:
                    logger.error(f"Failed to recover {component.component_id}: {e}")

            self.state = RuntimeState.RUNNING
            logger.info("✓ Recovery completed")
            return True

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.state = RuntimeState.STOPPED
            return False

    def get_metrics(self) -> RuntimeMetrics:
        """
        Get current runtime metrics.
        
        Returns:
            RuntimeMetrics: Current metrics
        """
        self.metrics.update_uptime()
        self.metrics.components_healthy = len(
            [c for c in self.components.values() if c.health == 'healthy']
        )
        self.metrics.components_degraded = len(
            [c for c in self.components.values() if c.health == 'degraded']
        )
        self.metrics.components_unhealthy = len(
            [c for c in self.components.values() if c.health == 'unhealthy']
        )
        return self.metrics

    def get_component_status(self) -> Dict[str, ComponentStatus]:
        """
        Get status of all components.
        
        Returns:
            dict: Component status mapping
        """
        return self.components.copy()

    def get_component_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of component status.
        
        Returns:
            dict: Summary information
        """
        total = len(self.components)
        healthy = len([c for c in self.components.values() if c.health == 'healthy'])
        degraded = len([c for c in self.components.values() if c.health == 'degraded'])
        unhealthy = len([c for c in self.components.values() if c.health == 'unhealthy'])

        return {
            'total_components': total,
            'healthy': healthy,
            'degraded': degraded,
            'unhealthy': unhealthy,
            'health_percentage': (healthy / total * 100) if total > 0 else 0,
            'state': self.state.value,
            'running': self.running
        }

    def record_event(self, event_name: str) -> None:
        """Record an event for metrics."""
        self.metrics.events_processed += 1

    def record_task_completed(self, task_name: str, duration_ms: float) -> None:
        """Record a completed task."""
        self.metrics.tasks_completed += 1
        # Update latency metrics
        if self.metrics.avg_event_latency_ms == 0:
            self.metrics.avg_event_latency_ms = duration_ms
        else:
            # Rolling average
            self.metrics.avg_event_latency_ms = (
                self.metrics.avg_event_latency_ms * 0.9 + duration_ms * 0.1
            )
        if duration_ms > self.metrics.max_event_latency_ms:
            self.metrics.max_event_latency_ms = duration_ms

    def record_task_failed(self, task_name: str) -> None:
        """Record a failed task."""
        self.metrics.tasks_failed += 1

    # Private helper methods

    async def _initialize_component(self, component_name: str) -> None:
        """Initialize a single component (stub for component-specific logic)."""
        # This is a stub that would be extended with actual component initialization
        # In a real implementation, this would initialize the specific component
        logger.debug(f"Initializing component: {component_name}")
        await asyncio.sleep(0.01)  # Simulate async init

    async def _recover_component(self, component_name: str) -> None:
        """Recover a single component (stub for component-specific logic)."""
        logger.debug(f"Recovering component: {component_name}")
        await asyncio.sleep(0.01)  # Simulate async recovery

    async def _publish_event(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish an event to the Event Bus."""
        if self.event_bus and hasattr(self.event_bus, 'publish'):
            try:
                await self.event_bus.publish(topic, data)
            except Exception as e:
                logger.error(f"Failed to publish event {topic}: {e}")

    def _metrics_to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'uptime_seconds': self.metrics.uptime_seconds,
            'events_processed': self.metrics.events_processed,
            'tasks_scheduled': self.metrics.tasks_scheduled,
            'tasks_completed': self.metrics.tasks_completed,
            'tasks_failed': self.metrics.tasks_failed,
            'cpu_usage_percent': self.metrics.cpu_usage_percent,
            'memory_usage_mb': self.metrics.memory_usage_mb,
            'avg_event_latency_ms': self.metrics.avg_event_latency_ms,
            'max_event_latency_ms': self.metrics.max_event_latency_ms,
            'components_healthy': self.metrics.components_healthy,
            'components_degraded': self.metrics.components_degraded,
            'components_unhealthy': self.metrics.components_unhealthy
        }
