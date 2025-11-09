"""
ASTRA-OS Event Loop Module

Implements the core async event loop for ASTRA-OS runtime.
Provides:
- EventLoop: Main event processing loop
- EventLoopState: Loop execution states
- TaskContext: Scheduled task tracking

The EventLoop is the heart of ASTRA-OS, continuously:
- Reading events from the Event Bus
- Processing events in batches
- Executing scheduled tasks
- Monitoring loop health

Usage:
    loop = EventLoop(event_bus=bus, orchestrator=orchestrator)
    await loop.run()
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Coroutine
import traceback

logger = logging.getLogger(__name__)


class EventLoopState(Enum):
    """Event loop execution states."""
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class TaskContext:
    """Context for a scheduled task."""
    task_id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3

    def start(self) -> None:
        """Mark task as started."""
        self.started_at = datetime.now()
        self.status = "running"

    def complete(self, result: Any = None) -> None:
        """Mark task as completed."""
        self.completed_at = datetime.now()
        self.result = result
        self.status = "completed"
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.completed_at = datetime.now()
        self.error = error
        self.status = "failed"
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.completed_at = datetime.now()
        self.status = "cancelled"
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000


class EventLoop:
    """
    Core async event loop for ASTRA-OS runtime.
    
    Responsibilities:
    - Read events from Event Bus
    - Process events in batches
    - Execute scheduled tasks
    - Monitor loop health
    - Track event statistics
    """

    def __init__(
        self,
        event_bus=None,
        orchestrator=None,
        router=None,
        max_queue_size: int = 10000,
        batch_size: int = 100,
        loop_sleep_ms: int = 10
    ):
        """
        Initialize the Event Loop.
        
        Args:
            event_bus: EventBus instance for reading events
            orchestrator: RuntimeOrchestrator instance for metrics
            router: ActionRouter instance for routing events
            max_queue_size: Maximum event queue size
            batch_size: Number of events to process per batch
            loop_sleep_ms: Sleep duration between loop iterations (ms)
        """
        self.event_bus = event_bus
        self.orchestrator = orchestrator
        self.router = router
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.loop_sleep_ms = loop_sleep_ms / 1000.0  # Convert to seconds
        
        self.state = EventLoopState.READY
        self.running = False
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.scheduled_tasks: Dict[str, TaskContext] = {}
        self.task_history: List[TaskContext] = []
        self.pending_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.total_events_processed = 0
        self.total_tasks_executed = 0
        self.total_tasks_failed = 0
        self.last_event_timestamp = None
        self.last_task_timestamp = None
        self.loop_iterations = 0
        self.avg_event_latency_ms = 0.0
        self.max_event_latency_ms = 0.0
        
        logger.info("EventLoop initialized")

    async def run(self) -> None:
        """
        Run the main event loop.
        
        This is the core loop that:
        - Continuously reads events from the bus
        - Processes them in batches
        - Executes scheduled tasks
        - Monitors loop health
        """
        if self.running:
            logger.warning("EventLoop already running")
            return

        try:
            logger.info("Starting EventLoop...")
            self.state = EventLoopState.RUNNING
            self.running = True

            while self.running:
                self.loop_iterations += 1
                start_time = time.time()

                try:
                    # Process pending events
                    await self._process_event_batch()

                    # Execute scheduled tasks
                    await self._execute_pending_tasks()

                    # Monitor loop health
                    if self.loop_iterations % 100 == 0:
                        await self._check_loop_health()

                    # Sleep to prevent CPU spinning
                    await asyncio.sleep(self.loop_sleep_ms)

                except asyncio.CancelledError:
                    logger.info("EventLoop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in event loop iteration: {e}")
                    logger.error(traceback.format_exc())
                    await asyncio.sleep(1.0)  # Back off on error

        except Exception as e:
            logger.error(f"Fatal error in EventLoop: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.running = False
            self.state = EventLoopState.STOPPED
            logger.info("EventLoop stopped")

    async def stop(self) -> None:
        """Stop the event loop gracefully."""
        if not self.running:
            logger.warning("EventLoop not running")
            return

        try:
            logger.info("Stopping EventLoop...")
            self.state = EventLoopState.STOPPING
            self.running = False

            # Cancel pending tasks
            for task_id, task in self.pending_tasks.items():
                if not task.done():
                    logger.debug(f"Cancelling task: {task_id}")
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=5.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass

            self.state = EventLoopState.STOPPED
            logger.info("✓ EventLoop stopped")

        except Exception as e:
            logger.error(f"Error stopping EventLoop: {e}")

    async def submit_event(self, event_name: str, event_data: Dict[str, Any]) -> bool:
        """
        Submit an event to the loop queue.
        
        Args:
            event_name: Name of the event
            event_data: Event data dictionary
            
        Returns:
            bool: True if submitted successfully
        """
        try:
            if self.event_queue.full():
                logger.warning("Event queue full, dropping event")
                return False

            await self.event_queue.put({
                'name': event_name,
                'data': event_data,
                'timestamp': datetime.now()
            })
            return True
        except Exception as e:
            logger.error(f"Failed to submit event: {e}")
            return False

    def schedule_task(
        self,
        task_id: str,
        name: str,
        coro: Coroutine,
        retry: bool = True
    ) -> TaskContext:
        """
        Schedule a task for execution.
        
        Args:
            task_id: Unique task identifier
            name: Human-readable task name
            coro: Coroutine to execute
            retry: Whether to retry on failure
            
        Returns:
            TaskContext: Task context
        """
        ctx = TaskContext(task_id=task_id, name=name)
        self.scheduled_tasks[task_id] = ctx

        # Create asyncio task
        async def run_task():
            try:
                ctx.start()
                result = await coro
                ctx.complete(result)
                self.total_tasks_executed += 1
                self.last_task_timestamp = datetime.now()
                if self.orchestrator:
                    self.orchestrator.record_task_completed(task_id, ctx.duration_ms)
                logger.debug(f"Task completed: {name} ({ctx.duration_ms:.2f}ms)")
            except asyncio.CancelledError:
                ctx.cancel()
                logger.debug(f"Task cancelled: {name}")
            except Exception as e:
                logger.error(f"Task failed: {name} - {e}")
                ctx.fail(str(e))
                self.total_tasks_failed += 1
                if self.orchestrator:
                    self.orchestrator.record_task_failed(task_id)

                # Retry logic
                if retry and ctx.retry_count < ctx.max_retries:
                    ctx.retry_count += 1
                    logger.info(f"Retrying task {name} (attempt {ctx.retry_count})")
                    await asyncio.sleep(1.0)  # Back off before retry
                    # Re-schedule retry
                    self.schedule_task(f"{task_id}_retry_{ctx.retry_count}", name, coro, retry=True)

        task = asyncio.create_task(run_task())
        self.pending_tasks[task_id] = task
        return ctx

    def get_scheduled_tasks(self) -> Dict[str, TaskContext]:
        """Get all scheduled tasks."""
        return self.scheduled_tasks.copy()

    def get_task_history(self, limit: int = 100) -> List[TaskContext]:
        """Get task execution history (last N tasks)."""
        return self.task_history[-limit:]

    def get_loop_stats(self) -> Dict[str, Any]:
        """Get event loop statistics."""
        return {
            'state': self.state.value,
            'running': self.running,
            'loop_iterations': self.loop_iterations,
            'total_events_processed': self.total_events_processed,
            'total_tasks_executed': self.total_tasks_executed,
            'total_tasks_failed': self.total_tasks_failed,
            'event_queue_size': self.event_queue.qsize(),
            'pending_tasks': len(self.pending_tasks),
            'avg_event_latency_ms': self.avg_event_latency_ms,
            'max_event_latency_ms': self.max_event_latency_ms,
            'last_event_timestamp': self.last_event_timestamp.isoformat() if self.last_event_timestamp else None,
            'last_task_timestamp': self.last_task_timestamp.isoformat() if self.last_task_timestamp else None
        }

    # Private helper methods

    async def _process_event_batch(self) -> None:
        """Process a batch of events from the queue."""
        batch_count = 0

        try:
            while batch_count < self.batch_size and not self.event_queue.empty():
                try:
                    # Non-blocking get
                    event = self.event_queue.get_nowait()
                    await self._run_event(event)
                    batch_count += 1
                    self.total_events_processed += 1
                except asyncio.QueueEmpty:
                    break
        except Exception as e:
            logger.error(f"Error processing event batch: {e}")

    async def _run_event(self, event: Dict[str, Any]) -> None:
        """
        Process a single event.
        
        Args:
            event: Event dictionary with 'name', 'data', 'timestamp'
        """
        try:
            event_name = event.get('name', 'unknown')
            event_data = event.get('data', {})
            event_timestamp = event.get('timestamp', datetime.now())
            
            start_time = time.time()

            # Route event through ActionRouter if available
            if self.router:
                await self.router.route_event(event_name, event_data)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Update latency metrics
            if self.avg_event_latency_ms == 0:
                self.avg_event_latency_ms = latency_ms
            else:
                self.avg_event_latency_ms = self.avg_event_latency_ms * 0.95 + latency_ms * 0.05
            
            if latency_ms > self.max_event_latency_ms:
                self.max_event_latency_ms = latency_ms

            self.last_event_timestamp = datetime.now()

            if self.orchestrator:
                self.orchestrator.record_event(event_name)

            logger.debug(f"Event processed: {event_name} ({latency_ms:.2f}ms)")

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            logger.error(traceback.format_exc())

    async def _execute_pending_tasks(self) -> None:
        """Execute and clean up pending tasks."""
        completed_tasks = []

        for task_id, task in list(self.pending_tasks.items()):
            if task.done():
                try:
                    # Get result (to trigger any exceptions)
                    result = task.result()
                    # Move to history
                    if task_id in self.scheduled_tasks:
                        ctx = self.scheduled_tasks[task_id]
                        self.task_history.append(ctx)
                        if len(self.task_history) > 10000:
                            self.task_history = self.task_history[-10000:]
                except Exception as e:
                    logger.error(f"Task {task_id} raised exception: {e}")

                completed_tasks.append(task_id)

        # Clean up completed tasks
        for task_id in completed_tasks:
            del self.pending_tasks[task_id]
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]

    async def _check_loop_health(self) -> None:
        """Check event loop health metrics."""
        try:
            queue_size = self.event_queue.qsize()
            pending_count = len(self.pending_tasks)

            if queue_size > self.max_queue_size * 0.8:
                logger.warning(f"EventLoop queue filling up: {queue_size}/{self.max_queue_size}")

            if pending_count > 100:
                logger.warning(f"Many pending tasks: {pending_count}")

            logger.debug(
                f"EventLoop health - Queue: {queue_size}, Pending: {pending_count}, "
                f"Latency: {self.avg_event_latency_ms:.2f}ms"
            )
        except Exception as e:
            logger.error(f"Error checking loop health: {e}")
