"""
ASTRA-OS Schedule Manager Module

Implements task scheduling with APScheduler integration.
Provides:
- ScheduleManager: Task scheduling engine
- ScheduleType: Scheduling types (once, interval, cron, at_time)
- ScheduledTask: Task definition

The ScheduleManager:
- Schedules one-time tasks
- Schedules recurring tasks (interval-based)
- Schedules cron-based tasks
- Enables/disables tasks
- Tracks execution history
- Handles execution errors

Usage:
    scheduler = ScheduleManager()
    await scheduler.initialize()
    
    # Schedule one-time task
    await scheduler.schedule_once('task1', handler, delay_seconds=10)
    
    # Schedule recurring task
    await scheduler.schedule_interval('task2', handler, interval_seconds=60)
    
    # Schedule cron task
    await scheduler.schedule_cron('task3', handler, cron_expression='0 9 * * MON')
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Coroutine
import traceback

logger = logging.getLogger(__name__)

# Import APScheduler
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    logger.warning("APScheduler not available, using basic scheduling")
    APSCHEDULER_AVAILABLE = False


class ScheduleType(Enum):
    """Task scheduling types."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    AT_TIME = "at_time"


@dataclass
class ScheduledTask:
    """Scheduled task definition."""
    task_id: str
    name: str
    schedule_type: ScheduleType
    handler: Callable
    trigger_config: Dict[str, Any]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'schedule_type': self.schedule_type.value,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'failure_count': self.failure_count,
            'last_error': self.last_error
        }


class ScheduleManager:
    """
    Task scheduling engine for ASTRA-OS.
    
    Responsibilities:
    - Schedule one-time tasks
    - Schedule recurring tasks
    - Schedule cron tasks
    - Enable/disable tasks
    - Track execution history
    - Handle execution errors
    - Manage APScheduler backend
    """

    def __init__(self, max_workers: int = 10):
        """
        Initialize the Schedule Manager.
        
        Args:
            max_workers: Maximum concurrent workers (for APScheduler)
        """
        self.scheduler = None
        self.max_workers = max_workers
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.initialized = False
        self.running = False
        
        if APSCHEDULER_AVAILABLE:
            try:
                self.scheduler = AsyncIOScheduler(
                    max_instances=max_workers,
                    daemon=False
                )
                logger.info("APScheduler initialized")
            except Exception as e:
                logger.error(f"Failed to initialize APScheduler: {e}")
                self.scheduler = None
        else:
            logger.warning("APScheduler not available, fallback to basic scheduling")

    async def initialize(self) -> bool:
        """
        Initialize the schedule manager.
        
        Returns:
            bool: True if initialized successfully
        """
        if self.initialized:
            logger.warning("ScheduleManager already initialized")
            return False

        try:
            if self.scheduler:
                self.scheduler.start()
                self.running = True
                logger.info("✓ ScheduleManager initialized")
            else:
                logger.warning("ScheduleManager initialized without APScheduler backend")
            
            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize ScheduleManager: {e}")
            return False

    async def shutdown(self) -> bool:
        """
        Shut down the schedule manager.
        
        Returns:
            bool: True if shutdown successful
        """
        if not self.running:
            return False

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
                self.running = False
                logger.info("✓ ScheduleManager shut down")
            return True

        except Exception as e:
            logger.error(f"Error shutting down ScheduleManager: {e}")
            return False

    async def schedule_once(
        self,
        task_id: str,
        handler: Callable,
        delay_seconds: float = 0,
        name: Optional[str] = None
    ) -> Optional[ScheduledTask]:
        """
        Schedule a one-time task.
        
        Args:
            task_id: Unique task identifier
            handler: Handler coroutine or function
            delay_seconds: Delay before execution (seconds)
            name: Human-readable task name
            
        Returns:
            ScheduledTask: Task object, or None if failed
        """
        try:
            task_name = name or task_id
            trigger_config = {'delay_seconds': delay_seconds}

            task = ScheduledTask(
                task_id=task_id,
                name=task_name,
                schedule_type=ScheduleType.ONCE,
                handler=handler,
                trigger_config=trigger_config,
                next_run=datetime.now() + timedelta(seconds=delay_seconds)
            )

            self.scheduled_tasks[task_id] = task

            if self.scheduler:
                # Schedule with APScheduler
                run_time = datetime.now() + timedelta(seconds=delay_seconds)
                self.scheduler.add_job(
                    self._wrap_handler(task),
                    DateTrigger(run_date=run_time),
                    id=task_id,
                    name=task_name,
                    replace_existing=True
                )
            else:
                # Fallback: schedule with asyncio
                asyncio.create_task(self._schedule_once_async(task, delay_seconds))

            logger.debug(f"✓ Task scheduled (once): {task_name} in {delay_seconds}s")
            return task

        except Exception as e:
            logger.error(f"Failed to schedule task: {e}")
            return None

    async def schedule_interval(
        self,
        task_id: str,
        handler: Callable,
        interval_seconds: float,
        name: Optional[str] = None,
        start_immediately: bool = False
    ) -> Optional[ScheduledTask]:
        """
        Schedule a recurring task (interval-based).
        
        Args:
            task_id: Unique task identifier
            handler: Handler coroutine or function
            interval_seconds: Interval between executions (seconds)
            name: Human-readable task name
            start_immediately: Whether to run immediately first
            
        Returns:
            ScheduledTask: Task object, or None if failed
        """
        try:
            task_name = name or task_id
            trigger_config = {
                'interval_seconds': interval_seconds,
                'start_immediately': start_immediately
            }

            task = ScheduledTask(
                task_id=task_id,
                name=task_name,
                schedule_type=ScheduleType.INTERVAL,
                handler=handler,
                trigger_config=trigger_config,
                next_run=datetime.now() if start_immediately else (
                    datetime.now() + timedelta(seconds=interval_seconds)
                )
            )

            self.scheduled_tasks[task_id] = task

            if self.scheduler:
                # Schedule with APScheduler
                self.scheduler.add_job(
                    self._wrap_handler(task),
                    IntervalTrigger(seconds=interval_seconds),
                    id=task_id,
                    name=task_name,
                    replace_existing=True
                )
            else:
                # Fallback: schedule with asyncio
                asyncio.create_task(
                    self._schedule_interval_async(task, interval_seconds, start_immediately)
                )

            logger.debug(f"✓ Task scheduled (interval): {task_name} every {interval_seconds}s")
            return task

        except Exception as e:
            logger.error(f"Failed to schedule interval task: {e}")
            return None

    async def schedule_cron(
        self,
        task_id: str,
        handler: Callable,
        cron_expression: str,
        name: Optional[str] = None
    ) -> Optional[ScheduledTask]:
        """
        Schedule a cron-based task.
        
        Cron expression format: minute hour day month day_of_week
        Examples:
        - '0 9 * * MON' - 9:00 AM on Mondays
        - '0 0 * * *' - Midnight daily
        - '*/15 * * * *' - Every 15 minutes
        
        Args:
            task_id: Unique task identifier
            handler: Handler coroutine or function
            cron_expression: Cron expression
            name: Human-readable task name
            
        Returns:
            ScheduledTask: Task object, or None if failed
        """
        try:
            task_name = name or task_id
            trigger_config = {'cron_expression': cron_expression}

            task = ScheduledTask(
                task_id=task_id,
                name=task_name,
                schedule_type=ScheduleType.CRON,
                handler=handler,
                trigger_config=trigger_config
            )

            self.scheduled_tasks[task_id] = task

            if self.scheduler:
                # Schedule with APScheduler
                self.scheduler.add_job(
                    self._wrap_handler(task),
                    CronTrigger.from_crontab(cron_expression),
                    id=task_id,
                    name=task_name,
                    replace_existing=True
                )
            else:
                logger.warning("Cron scheduling requires APScheduler")

            logger.debug(f"✓ Task scheduled (cron): {task_name} - {cron_expression}")
            return task

        except Exception as e:
            logger.error(f"Failed to schedule cron task: {e}")
            return None

    async def schedule_at(
        self,
        task_id: str,
        handler: Callable,
        run_time: datetime,
        name: Optional[str] = None
    ) -> Optional[ScheduledTask]:
        """
        Schedule a task to run at a specific time.
        
        Args:
            task_id: Unique task identifier
            handler: Handler coroutine or function
            run_time: Time to run
            name: Human-readable task name
            
        Returns:
            ScheduledTask: Task object, or None if failed
        """
        try:
            task_name = name or task_id
            trigger_config = {'run_time': run_time.isoformat()}

            task = ScheduledTask(
                task_id=task_id,
                name=task_name,
                schedule_type=ScheduleType.AT_TIME,
                handler=handler,
                trigger_config=trigger_config,
                next_run=run_time
            )

            self.scheduled_tasks[task_id] = task

            if self.scheduler:
                # Schedule with APScheduler
                self.scheduler.add_job(
                    self._wrap_handler(task),
                    DateTrigger(run_date=run_time),
                    id=task_id,
                    name=task_name,
                    replace_existing=True
                )

            logger.debug(f"✓ Task scheduled (at): {task_name} at {run_time}")
            return task

        except Exception as e:
            logger.error(f"Failed to schedule at-time task: {e}")
            return None

    async def enable_task(self, task_id: str) -> bool:
        """
        Enable a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if enabled successfully
        """
        if task_id not in self.scheduled_tasks:
            return False

        try:
            self.scheduled_tasks[task_id].enabled = True

            if self.scheduler and task_id in self.scheduler._lookup:
                self.scheduler._lookup[task_id].resume()

            logger.debug(f"Task enabled: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error enabling task: {e}")
            return False

    async def disable_task(self, task_id: str) -> bool:
        """
        Disable a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if disabled successfully
        """
        if task_id not in self.scheduled_tasks:
            return False

        try:
            self.scheduled_tasks[task_id].enabled = False

            if self.scheduler and task_id in self.scheduler._lookup:
                self.scheduler._lookup[task_id].pause()

            logger.debug(f"Task disabled: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error disabling task: {e}")
            return False

    async def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if removed successfully
        """
        if task_id not in self.scheduled_tasks:
            return False

        try:
            del self.scheduled_tasks[task_id]

            if self.scheduler:
                try:
                    self.scheduler.remove_job(task_id)
                except Exception:
                    pass

            logger.debug(f"Task removed: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing task: {e}")
            return False

    def get_scheduled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all scheduled tasks.
        
        Returns:
            dict: Task mapping
        """
        return {
            task_id: task.to_dict()
            for task_id, task in self.scheduled_tasks.items()
        }

    def get_task_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get task execution history.
        
        Args:
            limit: Maximum number of history entries
            
        Returns:
            list: History entries
        """
        return self.execution_history[-limit:]

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.
        
        Returns:
            dict: Statistics dictionary
        """
        total_tasks = len(self.scheduled_tasks)
        enabled_tasks = sum(1 for t in self.scheduled_tasks.values() if t.enabled)
        total_runs = sum(t.run_count for t in self.scheduled_tasks.values())
        total_failures = sum(t.failure_count for t in self.scheduled_tasks.values())

        return {
            'total_tasks': total_tasks,
            'enabled_tasks': enabled_tasks,
            'disabled_tasks': total_tasks - enabled_tasks,
            'total_runs': total_runs,
            'total_failures': total_failures,
            'total_history_entries': len(self.execution_history),
            'scheduler_running': self.running
        }

    # Private helper methods

    def _wrap_handler(self, task: ScheduledTask) -> Callable:
        """Wrap task handler for APScheduler."""
        async def wrapped_handler():
            try:
                task.last_run = datetime.now()
                task.run_count += 1

                # Execute handler
                if asyncio.iscoroutinefunction(task.handler):
                    await task.handler()
                else:
                    task.handler()

                # Log history
                self.execution_history.append({
                    'task_id': task.task_id,
                    'name': task.name,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'completed',
                    'error': None
                })

                if len(self.execution_history) > 10000:
                    self.execution_history = self.execution_history[-10000:]

            except Exception as e:
                logger.error(f"Task execution error ({task.task_id}): {e}")
                task.failure_count += 1
                task.last_error = str(e)

                # Log history
                self.execution_history.append({
                    'task_id': task.task_id,
                    'name': task.name,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'failed',
                    'error': str(e)
                })

        return wrapped_handler

    async def _schedule_once_async(self, task: ScheduledTask, delay_seconds: float) -> None:
        """Fallback one-time scheduling without APScheduler."""
        try:
            await asyncio.sleep(delay_seconds)

            if asyncio.iscoroutinefunction(task.handler):
                await task.handler()
            else:
                task.handler()

            task.last_run = datetime.now()
            task.run_count += 1

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            task.failure_count += 1

    async def _schedule_interval_async(
        self,
        task: ScheduledTask,
        interval_seconds: float,
        start_immediately: bool
    ) -> None:
        """Fallback interval scheduling without APScheduler."""
        try:
            if start_immediately:
                if asyncio.iscoroutinefunction(task.handler):
                    await task.handler()
                else:
                    task.handler()

                task.last_run = datetime.now()
                task.run_count += 1

            while task.enabled:
                await asyncio.sleep(interval_seconds)

                if not task.enabled:
                    break

                try:
                    if asyncio.iscoroutinefunction(task.handler):
                        await task.handler()
                    else:
                        task.handler()

                    task.last_run = datetime.now()
                    task.run_count += 1

                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                    task.failure_count += 1

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Interval scheduling error: {e}")
