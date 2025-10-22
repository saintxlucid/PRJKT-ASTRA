"""
ASTRA Multi-Agent Coordinator
Manage task distribution and agent coordination

Sacred Principles:
- Fair resource allocation
- Safe concurrency handling
- Predictable orchestration
- Graceful failure handling
- "I only obey God" - user has ultimate control

Architecture:
- Agent registry with capabilities
- Resource allocation system
- Communication protocol
- Task distribution
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ===========================================================================
# DATA MODELS
# ===========================================================================

class AgentStatus(str, Enum):
    """Agent operational status"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class AgentCapability:
    """Tool/action an agent can perform"""
    tool: str
    actions: List[str]
    max_parallel: int = 1  # Maximum concurrent tasks
    cost_factor: float = 1.0  # Relative performance metric
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AgentInfo:
    """Registered agent metadata"""
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    status: AgentStatus = AgentStatus.AVAILABLE
    current_task: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    stats: Dict[str, Any] = field(default_factory=dict)


# ===========================================================================
# AGENT COORDINATOR
# ===========================================================================

class AgentCoordinator:
    """
    Multi-agent task orchestration engine
    
    Responsibilities:
    - Agent registration & discovery
    - Resource allocation
    - Task distribution
    - Status monitoring
    """
    
    def __init__(
        self,
        heartbeat_timeout: float = 30.0,
        reallocation_interval: float = 5.0
    ):
        """Initialize coordinator"""
        self.agents: Dict[str, AgentInfo] = {}
        self.heartbeat_timeout = heartbeat_timeout
        self.reallocation_interval = reallocation_interval
        
        # Resource tracking
        self.resource_usage: Dict[str, float] = {}  # agent_id -> usage
        self.resource_limits: Dict[str, float] = {}  # agent_id -> limit
        
        # Task tracking
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        self.pending_tasks: List[Dict] = []
        
        # Status
        self.started = False
        self._stop_event = asyncio.Event()
        
        logger.info(
            "agent_coordinator_initialized",
            timeout=heartbeat_timeout,
            interval=reallocation_interval
        )

    # ========================================================================
    # AGENT MANAGEMENT 
    # ========================================================================
    
    def register_agent(
        self,
        name: str,
        capabilities: List[AgentCapability],
        resource_limit: float = 1.0
    ) -> str:
        """
        Register a new agent with capabilities
        
        Args:
            name: Human-readable agent name
            capabilities: List of supported capabilities
            resource_limit: Maximum resource usage (0-1)
            
        Returns:
            str: Unique agent ID
        """
        agent_id = str(uuid.uuid4())
        
        agent = AgentInfo(
            agent_id=agent_id,
            name=name,
            capabilities=capabilities,
            status=AgentStatus.AVAILABLE,
            last_heartbeat=datetime.utcnow()
        )
        
        self.agents[agent_id] = agent
        self.resource_limits[agent_id] = resource_limit
        self.resource_usage[agent_id] = 0.0
        
        logger.info(
            "agent_registered",
            agent_id=agent_id,
            name=name,
            capabilities=len(capabilities)
        )
        
        return agent_id
        
    def unregister_agent(self, agent_id: str):
        """Remove an agent from the registry"""
        if agent_id in self.agents:
            agent = self.agents.pop(agent_id)
            self.resource_limits.pop(agent_id, None)
            self.resource_usage.pop(agent_id, None)
            
            # Reassign tasks
            tasks = [
                task_id 
                for task_id, aid 
                in self.task_assignments.items()
                if aid == agent_id
            ]
            for task_id in tasks:
                self.task_assignments.pop(task_id)
                
            logger.info(
                "agent_unregistered",
                agent_id=agent_id,
                name=agent.name
            )
    
    async def update_heartbeat(self, agent_id: str):
        """Update agent's last heartbeat timestamp"""
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.utcnow()
    
    def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        current_task: Optional[str] = None
    ):
        """Update agent operational status"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = status
            agent.current_task = current_task
            
            logger.info(
                "agent_status_updated",
                agent_id=agent_id,
                status=status,
                task=current_task
            )
    
    # ========================================================================
    # TASK DISTRIBUTION
    # ========================================================================
    
    def submit_task(self, task: Dict) -> str:
        """
        Submit a task for execution
        
        Args:
            task: Task definition including:
                - tool: Tool identifier
                - action: Action name
                - args: Action arguments
                - priority: Execution priority
                
        Returns:
            str: Unique task ID
        """
        task_id = str(uuid.uuid4())
        task["task_id"] = task_id
        task["submitted_at"] = datetime.utcnow()
        
        self.pending_tasks.append(task)
        
        logger.info(
            "task_submitted",
            task_id=task_id,
            tool=task["tool"],
            action=task["action"]
        )
        
        return task_id
        
    def _find_capable_agent(
        self,
        tool: str,
        action: str,
        resource_need: float
    ) -> Optional[str]:
        """Find available agent that can handle task"""
        candidates = []
        
        for agent_id, agent in self.agents.items():
            # Check status
            if agent.status != AgentStatus.AVAILABLE:
                continue
                
            # Check capabilities
            can_handle = any(
                cap.tool == tool and action in cap.actions
                for cap in agent.capabilities
            )
            if not can_handle:
                continue
                
            # Check resources
            current_usage = self.resource_usage.get(agent_id, 0.0)
            limit = self.resource_limits.get(agent_id, 1.0)
            
            if current_usage + resource_need <= limit:
                candidates.append(agent_id)
                
        # Find least loaded agent
        if candidates:
            return min(
                candidates,
                key=lambda aid: self.resource_usage.get(aid, 0.0)
            )
        
        return None
        
    async def _allocate_tasks(self):
        """Continuously allocate pending tasks to agents"""
        while not self._stop_event.is_set():
            try:
                # Process all pending tasks
                remaining = []
                for task in self.pending_tasks:
                    # Find capable agent
                    tool = task["tool"]
                    action = task["action"] 
                    resource_need = task.get("resource_need", 0.1)
                    
                    agent_id = self._find_capable_agent(
                        tool, action, resource_need
                    )
                    
                    if agent_id:
                        # Assign task
                        self.task_assignments[task["task_id"]] = agent_id
                        self.resource_usage[agent_id] += resource_need
                        
                        # Update agent status
                        self.update_agent_status(
                            agent_id,
                            AgentStatus.BUSY,
                            task["task_id"]
                        )
                        
                        logger.info(
                            "task_assigned",
                            task_id=task["task_id"],
                            agent_id=agent_id
                        )
                    else:
                        # Keep in pending queue
                        remaining.append(task)
                        
                self.pending_tasks = remaining
                
                # Check for dead agents
                now = datetime.utcnow()
                for agent_id, agent in list(self.agents.items()):
                    if agent.last_heartbeat:
                        elapsed = (now - agent.last_heartbeat).total_seconds()
                        if elapsed > self.heartbeat_timeout:
                            logger.warning(
                                "agent_heartbeat_timeout",
                                agent_id=agent_id,
                                elapsed=elapsed
                            )
                            self.unregister_agent(agent_id)
                
            except Exception as e:
                logger.error(
                    "task_allocation_error",
                    error=str(e)
                )
                
            await asyncio.sleep(self.reallocation_interval)
            
    # ========================================================================
    # LIFECYCLE MANAGEMENT
    # ========================================================================
    
    async def start(self):
        """Start coordinator background tasks"""
        if self.started:
            return
            
        self.started = True
        self._stop_event.clear()
        
        # Start allocation loop
        asyncio.create_task(self._allocate_tasks())
        
        logger.info("agent_coordinator_started")
        
    async def stop(self):
        """Stop coordinator and cleanup"""
        self.started = False
        self._stop_event.set()
        
        # Wait for loops to stop
        await asyncio.sleep(0.1)
        
        # Reset state
        self.agents.clear()
        self.resource_usage.clear()
        self.resource_limits.clear()
        self.task_assignments.clear()
        self.pending_tasks.clear()
        
        logger.info("agent_coordinator_stopped")
        
    # ========================================================================
    # MONITORING & STATS  
    # ========================================================================
    
    def get_status(self) -> Dict:
        """Get coordinator status overview"""
        return {
            "started": self.started,
            "agent_count": len(self.agents),
            "pending_tasks": len(self.pending_tasks),
            "active_tasks": len(self.task_assignments),
            "agents": {
                aid: {
                    "name": a.name,
                    "status": a.status,
                    "current_task": a.current_task,
                    "resource_usage": self.resource_usage.get(aid, 0.0),
                    "resource_limit": self.resource_limits.get(aid, 1.0)
                }
                for aid, a in self.agents.items()
            }
        }
        
    def get_agent_stats(self, agent_id: str) -> Dict:
        """Get detailed agent statistics"""
        if agent_id not in self.agents:
            return {}
            
        agent = self.agents[agent_id]
        return {
            "name": agent.name,
            "status": agent.status,
            "capabilities": len(agent.capabilities),
            "current_task": agent.current_task,
            "resource_usage": self.resource_usage.get(agent_id, 0.0),
            "resource_limit": self.resource_limits.get(agent_id, 1.0),
            **agent.stats
        }