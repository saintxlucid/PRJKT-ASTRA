"""
ASTRA Autonomy Core
Implements the core autonomy loop and task management
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AutonomyState(str, Enum):
    """Autonomy system operational states"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class RiskLevel(str, Enum):
    """Task risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskContext:
    """Context for task execution"""
    task_id: str
    objective: str
    priority: int = 1
    risk_level: RiskLevel = RiskLevel.LOW
    max_retries: int = 1
    timeout: float = 30.0
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AutonomyCore:
    """
    Core autonomy system implementing the sense-plan-act loop
    
    Components:
    - Sensor monitoring
    - Task planning
    - Safety controls
    - Execution monitoring
    """
    
    def __init__(
        self,
        check_interval: float = 1.0,
        min_priority: int = 1,
        max_priority: int = 10
    ):
        """Initialize autonomy core"""
        self.check_interval = check_interval
        self.min_priority = min_priority
        self.max_priority = max_priority
        
        # State
        self.state = AutonomyState.IDLE
        self._stop_event = asyncio.Event()
        
        # Task tracking
        self.active_tasks: Dict[str, TaskContext] = {}
        self.completed_tasks: Dict[str, TaskContext] = {}
        self.failed_tasks: Dict[str, TaskContext] = {}
        
        # Sensor readings
        self.sensors: Dict[str, float] = {}
        self.triggers: List[Dict] = []
        
        # Stats
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "last_check": 0.0,
            "trigger_fires": 0
        }
        
        logger.info(
            "autonomy_core_initialized",
            interval=check_interval,
            min_priority=min_priority,
            max_priority=max_priority
        )

    async def start(self) -> None:
        """Start autonomy loop"""
        if self.state != AutonomyState.IDLE:
            return
            
        self.state = AutonomyState.RUNNING
        self._stop_event.clear()
        
        # Start background loop
        asyncio.create_task(self._autonomy_loop())
        logger.info("autonomy_core_started")
        
    async def stop(self) -> None:
        """Stop autonomy loop"""
        if self.state not in (AutonomyState.RUNNING, AutonomyState.PAUSED):
            return
            
        self.state = AutonomyState.STOPPED
        self._stop_event.set()
        logger.info("autonomy_core_stopped")
        
    async def pause(self) -> None:
        """Pause autonomy loop"""
        if self.state != AutonomyState.RUNNING:
            return
            
        self.state = AutonomyState.PAUSED
        logger.info("autonomy_core_paused")
        
    async def resume(self) -> None:
        """Resume autonomy loop"""
        if self.state != AutonomyState.PAUSED:
            return
            
        self.state = AutonomyState.RUNNING
        logger.info("autonomy_core_resumed")

    def update_sensors(self, readings: Dict[str, float]) -> None:
        """Update sensor readings"""
        self.sensors.update(readings)
        self.stats["last_check"] = time.time()
        
    def add_trigger(self, trigger: Dict) -> None:
        """Add new trigger"""
        self.triggers.append(trigger)
        
    def remove_trigger(self, trigger_id: str) -> None:
        """Remove trigger by ID"""
        self.triggers = [t for t in self.triggers if t["id"] != trigger_id]

    async def submit_task(self, task: Dict) -> Optional[str]:
        """Submit new task for execution"""
        # Validate priority
        priority = task.get("priority", self.min_priority)
        if not self.min_priority <= priority <= self.max_priority:
            logger.warning(
                "invalid_task_priority",
                min=self.min_priority,
                max=self.max_priority,
                priority=priority
            )
            return None
            
        # Create task context with microsecond precision for unique IDs
        task_id = f"task_{int(time.time() * 1000000)}"
        context = TaskContext(
            task_id=task_id,
            objective=task["objective"],
            priority=priority,
            risk_level=RiskLevel(task.get("risk_level", RiskLevel.LOW)),
            max_retries=task.get("max_retries", 1),
            timeout=task.get("timeout", 30.0),
            constraints=task.get("constraints", {}),
            metadata=task.get("metadata", {})
        )
        
        # Track task
        self.active_tasks[task_id] = context
        logger.info(
            "task_submitted",
            task_id=task_id,
            priority=priority,
            risk_level=context.risk_level
        )
        
        return task_id
        
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of task"""
        # Check active tasks
        if task_id in self.active_tasks:
            return {
                "ok": True,
                "task_id": task_id,
                "status": "active",
                "context": self.active_tasks[task_id].__dict__
            }
            
        # Check completed tasks
        if task_id in self.completed_tasks:
            return {
                "ok": True,
                "task_id": task_id,
                "status": "completed", 
                "context": self.completed_tasks[task_id].__dict__
            }
            
        # Check failed tasks
        if task_id in self.failed_tasks:
            return {
                "ok": True,
                "task_id": task_id,
                "status": "failed",
                "context": self.failed_tasks[task_id].__dict__
            }
            
        return None

    async def _autonomy_loop(self) -> None:
        """Main autonomy loop"""
        while not self._stop_event.is_set():
            try:
                if self.state == AutonomyState.RUNNING:
                    # Check triggers
                    await self._check_triggers()
                    
                    # Process active tasks
                    await self._process_tasks()
                    
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("autonomy_loop_error", error=str(e))
                continue

    async def _check_triggers(self) -> None:
        """Check and fire triggers"""
        for trigger in self.triggers:
            try:
                # Check conditions
                conditions = trigger.get("conditions", {})
                if await self._evaluate_conditions(conditions):
                    # Check cooldown
                    last_fire = trigger.get("last_fire", 0)
                    cooldown = trigger.get("cooldown", 1.0)
                    now = time.time()
                    
                    if now - last_fire >= cooldown:
                        # Create task from trigger
                        task = trigger["task"]
                        await self.submit_task(task)
                        
                        # Update trigger
                        trigger["last_fire"] = now
                        self.stats["trigger_fires"] += 1
                        
                        logger.info(
                            "trigger_fired",
                            trigger_id=trigger["id"],
                            task=task["objective"]
                        )
            except Exception as e:
                logger.error(
                    "trigger_check_failed",
                    trigger_id=trigger["id"],
                    exc_info=True
                )
                continue

    async def _evaluate_conditions(self, conditions: Dict) -> bool:
        """Evaluate trigger conditions"""
        try:
            for sensor, threshold in conditions.items():
                if sensor not in self.sensors:
                    return False
                    
                value = self.sensors[sensor]
                if isinstance(threshold, (int, float)):
                    if value < threshold:
                        return False
                elif isinstance(threshold, dict):
                    if "min" in threshold and value < threshold["min"]:
                        return False
                    if "max" in threshold and value > threshold["max"]:
                        return False
                        
            return True
            
        except Exception as e:
            logger.error("condition_eval_failed", error=str(e))
            return False

    async def _process_tasks(self) -> None:
        """Process active tasks"""
        # Sort by priority
        sorted_tasks = sorted(
            list(self.active_tasks.items()),  # Create list copy to avoid modification during iteration
            key=lambda x: x[1].priority,
            reverse=True
        )
        
        # Process tasks concurrently
        tasks = []
        for task_id, context in sorted_tasks:
            task = asyncio.create_task(self._execute_task(task_id, context))
            tasks.append(task)
            
        if tasks:
            # Wait for all tasks
            await asyncio.gather(*tasks)
    
    async def _execute_task(self, task_id: str, context: TaskContext) -> None:
        """Execute single task"""
        try:
            if task_id not in self.active_tasks:
                return
                
            # Simulate task execution with longer time for testing
            execution_time = context.timeout / 2  # Use half the timeout period
            await asyncio.sleep(execution_time)
            
            # Mark as completed if still active
            if task_id in self.active_tasks:
                self.completed_tasks[task_id] = context
                del self.active_tasks[task_id]
                self.stats["tasks_completed"] += 1
                logger.info(f"task_completed: {task_id}")
                
        except Exception:
            logger.error("task_processing_failed", exc_info=True)
            
            # Move to failed tasks if still active
            if task_id in self.active_tasks:
                self.failed_tasks[task_id] = context
                del self.active_tasks[task_id]
                self.stats["tasks_failed"] += 1