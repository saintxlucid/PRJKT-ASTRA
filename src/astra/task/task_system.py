"""
ASTRA Task System Integration
Connect Task Agent, Autonomy, and Execution components

Sacred Principles:
- Clean component interfaces
- Safe initialization
- Graceful degradation
- Runtime flexibility
- "I only obey God" - user has ultimate control

Architecture:
- Component initialization
- System integration
- Event routing
- Status monitoring
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from ..planner.task_planner import (
    TaskPlanner, TaskStatus as PlannerTaskStatus, TaskStep
)
from ..coordinator.agent_coordinator import (
    AgentCoordinator, AgentCapability, AgentStatus
)
from ..constraints.constraint_system import (
    ConstraintSystem, ResourceType, ConstraintStatus
)
from ..executor.execution_engine import (
    ExecutionEngine, ExecutionStatus
)
from ..autonomy.autonomy_core import AutonomyCore, RiskLevel


class TaskSystemManager:
    """
    Task System Integration Manager
    
    Responsibilities:
    - Initialize components
    - Connect event flows
    - Monitor system health
    - Provide unified interface
    """
    
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        max_parallel_tasks: int = 3,
        max_retries: int = 2,
        default_timeout: float = 30.0
    ):
        """Initialize task system"""
        self.config_dir = config_dir
        
        # Core components
        self.task_planner = TaskPlanner(
            max_parallel_steps=max_parallel_tasks,
            max_retries=max_retries,
            default_timeout=default_timeout
        )
        
        self.constraint_system = ConstraintSystem()
        
        self.execution_engine = ExecutionEngine(
            constraint_system=self.constraint_system,
            max_parallel=max_parallel_tasks,
            default_timeout=default_timeout
        )
        
        self.agent_coordinator = AgentCoordinator(
            heartbeat_timeout=60.0,
            reallocation_interval=5.0
        )
        
        self.autonomy_core = AutonomyCore(
            check_interval=1.0,
            min_priority=1,
            max_priority=10
        )
        
        # Component state
        self.started = False
        self._stop_event = asyncio.Event()
        
        # Setup default constraints
        self._setup_constraints()
        
        logger.info(
            "task_system_initialized",
            config_dir=str(config_dir) if config_dir else None,
            max_parallel=max_parallel_tasks
        )
        
    def _setup_constraints(self):
        """Setup default system constraints"""
        # Resource limits
        self.constraint_system.add_resource_limit(
            "system.cpu",
            ResourceType.CPU,
            soft_limit=0.8,  # 80% CPU warning
            hard_limit=0.95  # 95% CPU violation
        )
        
        self.constraint_system.add_resource_limit(
            "system.memory",
            ResourceType.MEMORY, 
            soft_limit=0.7,  # 70% RAM warning
            hard_limit=0.9   # 90% RAM violation
        )
        
        self.constraint_system.add_resource_limit(
            "system.concurrency",
            ResourceType.CONCURRENCY,
            soft_limit=5,    # 5 parallel tasks warning
            hard_limit=10    # 10 parallel tasks violation
        )
        
        # Operational constraints
        def check_agent_health():
            active = len(self.agent_coordinator.get_status()["agents"])
            if active == 0:
                return ConstraintStatus.VIOLATED
            return ConstraintStatus.VALID
            
        self.constraint_system.add_constraint(
            "system.agents",
            check_agent_health,
            priority=1  # Highest priority
        )
        
    async def start(self):
        """Start task system components"""
        if self.started:
            return
            
            try:
                # Start components
                await self.agent_coordinator.start()
                await self.autonomy_core.start()
                
                # Mark as started
                self.started = True
                self._stop_event.clear()
                
                # Start monitoring loops
                asyncio.create_task(self._monitor_loop())
                
                logger.info("task_system_started")
            except Exception:
                logger.error("task_system_start_failed", exc_info=True)
                raise
            logger.error(
                "task_system_start_failed",
                error=str(e)
            )
            raise
            
    async def stop(self):
        """Stop task system components"""
        self.started = False
        self._stop_event.set()
        
        try:
            # Stop components
            await self.agent_coordinator.stop()
            
            logger.info("task_system_stopped")
            
        except Exception as e:
            logger.error("task_system_stop_failed", exc_info=True)
            
    async def _monitor_loop(self):
        """System monitoring loop"""
        while not self._stop_event.is_set():
            try:
                # Check constraints
                violations = self.constraint_system.validate_all()
                
                # Update metrics
                metrics = self.execution_engine.get_metrics()
                active = metrics["active_tasks"]
                
                self.constraint_system.update_resource_usage(
                    "system.concurrency",
                    float(active)
                )
                
                # Log status
                if violations:
                    logger.warning("constraint_violations", violations=str(violations))
                    
            except Exception as e:
                logger.error("monitor_loop_error", exc_info=True)
                
            await asyncio.sleep(5.0)  # 5 second interval
            
    # ========================================================================
    # TASK MANAGEMENT
    # ========================================================================
    
    async def submit_task(
        self,
        task: Dict,
        executor: Any = None
    ) -> Dict:
        """
        Submit task for execution
        
        Args:
            task: Task definition with:
                - objective: What to accomplish
                - constraints: Resource/timing limits
                - template: Optional plan template
            executor: Tool executor instance
            
        Returns:
            dict: Task submission result
        """
        if not self.started:
            return {
                "ok": False,
                "error": "Task system not started"
            }
            
        try:
            # Create execution plan
            plan = self.task_planner.create_plan(task)
            
            # Submit to coordinator
            agent_id = self.agent_coordinator.submit_task({
                "task_id": plan.plan_id,
                "tool": task.get("tool", "default"),
                "action": task.get("action", "execute"),
                "args": task
            })
            
            if not agent_id:
                return {
                    "ok": False,
                    "error": "No agent available"
                }
                
            # Execute plan
            result = await self.execution_engine.execute_plan(
                plan,
                executor or self
            )
            
            return {
                "ok": result["ok"],
                "task_id": plan.plan_id,
                "agent_id": agent_id,
                "status": result["status"],
                "progress": result["progress"],
                "results": result.get("step_results", {})
            }
            
        except Exception as e:
            logger.error("task_submission_failed", exc_info=True)
            return {
                "ok": False,
                "error": str(e)
            }
            
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of submitted task"""
        # Check execution engine
        status = self.execution_engine.get_execution_status(task_id)
        if status:
            return status
            
        # Check planner
        plan = self.task_planner.get_plan_status(task_id)
        if plan:
            return {
                "ok": True,
                "task_id": task_id,
                "status": plan.status,
                "progress": 0.0
            }
            
        return None
        
    # ========================================================================
    # AGENT MANAGEMENT
    # ========================================================================
    
    def register_agent(
        self,
        name: str,
        capabilities: List[Dict]
    ) -> str:
        """Register new task execution agent"""
        agent_caps = [
            AgentCapability(**cap)
            for cap in capabilities
        ]
        
        return self.agent_coordinator.register_agent(
            name=name,
            capabilities=agent_caps
        )
        
    async def update_agent_heartbeat(self, agent_id: str):
        """Update agent heartbeat"""
        await self.agent_coordinator.update_heartbeat(agent_id)
        
    # ========================================================================
    # MONITORING & STATUS
    # ========================================================================
    
    def get_status(self) -> Dict:
        """Get system status overview"""
        coordinator_status = self.agent_coordinator.get_status()
        constraint_status = self.constraint_system.get_status()
        execution_metrics = self.execution_engine.get_metrics()
        
        return {
            "started": self.started,
            "agents": coordinator_status["agents"],
            "constraints": constraint_status,
            "metrics": execution_metrics,
            "tasks": {
                "pending": len(self.task_planner.list_active_plans()),
                "active": execution_metrics["active_tasks"],
                "completed": execution_metrics["completed_tasks"],
                "failed": execution_metrics["failed_tasks"]
            }
        }
        
    def get_metrics(self) -> Dict:
        """Get detailed system metrics"""
        return {
            "execution": self.execution_engine.get_metrics(),
            "constraints": self.constraint_system.get_statistics(),
            "coordinator": self.agent_coordinator.get_status()
        }