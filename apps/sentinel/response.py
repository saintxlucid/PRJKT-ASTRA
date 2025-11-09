"""
ASTRA-OS Response Orchestrator: Coordinates threat response actions.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class ResponseStatus(Enum):
    """Response action status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResponseAction(Enum):
    """Response actions to threats."""
    ALERT = "alert"
    INVESTIGATE = "investigate"
    ISOLATE = "isolate"
    TERMINATE = "terminate"
    QUARANTINE = "quarantine"
    WHITELIST = "whitelist"
    LOG_ONLY = "log_only"


@dataclass
class ResponsePlan:
    """Response action plan."""
    plan_id: str
    timestamp: float
    incident_id: str
    threat_level: str
    actions: List[str]  # Action names
    priority: int = 0
    status: ResponseStatus = ResponseStatus.PENDING
    executed_actions: List[str] = field(default_factory=list)
    failed_actions: Dict[str, str] = field(default_factory=dict)
    estimated_duration_seconds: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def duration(self) -> Optional[float]:
        """Get actual duration if completed."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        if self.start_time:
            return time.time() - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'plan_id': self.plan_id,
            'timestamp': self.timestamp,
            'incident_id': self.incident_id,
            'threat_level': self.threat_level,
            'actions': self.actions,
            'priority': self.priority,
            'status': self.status.value,
            'executed_actions': self.executed_actions,
            'failed_actions': self.failed_actions,
            'duration': self.duration(),
        }


# ============================================================================
# Response Actions
# ============================================================================

class ResponseAction:
    """Base response action."""
    
    def __init__(self, action_id: str, name: str, description: str, 
                 priority: int = 0, async_safe: bool = False):
        self.action_id = action_id
        self.name = name
        self.description = description
        self.priority = priority
        self.async_safe = async_safe
        self.last_executed = None
        self.execution_count = 0
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute response action.
        
        Args:
            context: Action context (incident, process, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.last_executed = time.time()
            self.execution_count += 1
            logger.info(f"Executing response action: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error executing action {self.name}: {e}")
            return False


class AlertAction(ResponseAction):
    """Alert response action."""
    
    def __init__(self, event_bus=None, notification_system=None):
        super().__init__(
            action_id="alert",
            name="Alert",
            description="Emit security alert",
            priority=1,
            async_safe=True
        )
        self.event_bus = event_bus
        self.notification_system = notification_system
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute alert."""
        try:
            incident = context.get('incident')
            
            # Emit to event bus
            if self.event_bus:
                await self.event_bus.publish(
                    topic="sentinel/alert",
                    message={
                        'incident_id': incident.get('incident_id'),
                        'threat_level': incident.get('threat_level'),
                        'description': incident.get('description'),
                    }
                )
            
            # Send notification
            if self.notification_system:
                title = f"Security Alert: {incident.get('threat_level')}"
                message = incident.get('description', 'Unknown threat detected')
                await self.notification_system.send_alert(title, message)
            
            logger.info(f"Alert sent for incident {incident.get('incident_id')}")
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in AlertAction: {e}")
            return False


class InvestigateAction(ResponseAction):
    """Investigate response action."""
    
    def __init__(self, memory_layer=None):
        super().__init__(
            action_id="investigate",
            name="Investigate",
            description="Collect detailed incident information",
            priority=2,
            async_safe=True
        )
        self.memory_layer = memory_layer
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute investigation."""
        try:
            incident = context.get('incident')
            
            # Log incident to memory
            if self.memory_layer:
                await self.memory_layer.record_event(
                    event_type="security_incident",
                    data=incident,
                    importance=0.9
                )
            
            # Collect process information
            processes = context.get('affected_processes', [])
            logger.info(f"Investigating {len(processes)} affected processes")
            
            # Collect file information
            files = context.get('affected_files', [])
            logger.info(f"Investigating {len(files)} affected files")
            
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in InvestigateAction: {e}")
            return False


class IsolateAction(ResponseAction):
    """Isolate response action (network or process isolation)."""
    
    def __init__(self, tool_bus=None):
        super().__init__(
            action_id="isolate",
            name="Isolate",
            description="Isolate threat from system/network",
            priority=8,
            async_safe=False
        )
        self.tool_bus = tool_bus
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute isolation."""
        try:
            incident = context.get('incident')
            processes = context.get('affected_processes', [])
            
            # Isolate processes (network isolation, firewall rules, etc.)
            if self.tool_bus:
                for pid in processes[:5]:  # Limit to avoid cascading failures
                    result = await self.tool_bus.execute_tool(
                        tool_name="shell",
                        operation="isolate_process",
                        args={'pid': pid, 'timeout': 300}  # 5 minute timeout
                    )
                    
                    if result.get('success'):
                        logger.info(f"Isolated process {pid}")
                    else:
                        logger.warning(f"Failed to isolate process {pid}: {result.get('error')}")
            
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in IsolateAction: {e}")
            return False


class TerminateAction(ResponseAction):
    """Terminate response action (kill malicious processes)."""
    
    def __init__(self, tool_bus=None):
        super().__init__(
            action_id="terminate",
            name="Terminate",
            description="Terminate malicious processes",
            priority=9,
            async_safe=False
        )
        self.tool_bus = tool_bus
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute termination."""
        try:
            processes = context.get('affected_processes', [])
            
            # Terminate processes
            if self.tool_bus:
                for pid in processes:
                    result = await self.tool_bus.execute_tool(
                        tool_name="shell",
                        operation="terminate_process",
                        args={'pid': pid, 'force': True}
                    )
                    
                    if result.get('success'):
                        logger.info(f"Terminated process {pid}")
                    else:
                        logger.warning(f"Failed to terminate process {pid}: {result.get('error')}")
            
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in TerminateAction: {e}")
            return False


class QuarantineAction(ResponseAction):
    """Quarantine response action (move suspicious files to quarantine)."""
    
    def __init__(self, tool_bus=None):
        super().__init__(
            action_id="quarantine",
            name="Quarantine",
            description="Move suspicious files to quarantine",
            priority=7,
            async_safe=True
        )
        self.tool_bus = tool_bus
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute quarantine."""
        try:
            files = context.get('affected_files', [])
            
            # Quarantine files
            if self.tool_bus:
                for file_path in files[:10]:  # Limit for safety
                    result = await self.tool_bus.execute_tool(
                        tool_name="filesystem",
                        operation="quarantine_file",
                        args={'path': file_path}
                    )
                    
                    if result.get('success'):
                        logger.info(f"Quarantined file: {file_path}")
                    else:
                        logger.warning(f"Failed to quarantine {file_path}: {result.get('error')}")
            
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in QuarantineAction: {e}")
            return False


class WhitelistAction(ResponseAction):
    """Whitelist response action (add to whitelist for known-good items)."""
    
    def __init__(self, threat_detector=None):
        super().__init__(
            action_id="whitelist",
            name="Whitelist",
            description="Add item to whitelist",
            priority=3,
            async_safe=True
        )
        self.threat_detector = threat_detector
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute whitelist."""
        try:
            whitelist_items = context.get('whitelist_items', [])
            
            # Add to whitelist
            if self.threat_detector:
                for item in whitelist_items:
                    self.threat_detector.add_to_whitelist(item)
                    logger.info(f"Whitelisted: {item}")
            
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in WhitelistAction: {e}")
            return False


class LogOnlyAction(ResponseAction):
    """Log-only response action (just log, no action)."""
    
    def __init__(self):
        super().__init__(
            action_id="log_only",
            name="Log Only",
            description="Log incident without taking action",
            priority=0,
            async_safe=True
        )
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """Execute log-only action."""
        try:
            incident = context.get('incident')
            logger.warning(f"Threat incident logged: {incident.get('incident_id')} - "
                          f"{incident.get('description')}")
            return await super().execute(context)
        except Exception as e:
            logger.error(f"Error in LogOnlyAction: {e}")
            return False


# ============================================================================
# Response Orchestrator
# ============================================================================

class ResponseOrchestrator:
    """Orchestrates threat response actions."""
    
    def __init__(self, event_bus=None, memory_layer=None, tool_bus=None,
                 threat_detector=None, notification_system=None):
        """Initialize response orchestrator."""
        self.event_bus = event_bus
        self.memory_layer = memory_layer
        self.tool_bus = tool_bus
        self.threat_detector = threat_detector
        self.notification_system = notification_system
        
        # Registered actions
        self.actions: Dict[str, ResponseAction] = {}
        self.response_history: List[ResponsePlan] = []
        self.active_responses: Dict[str, ResponsePlan] = {}
        
        self._register_default_actions()
    
    def _register_default_actions(self):
        """Register default response actions."""
        self.actions['alert'] = AlertAction(
            event_bus=self.event_bus,
            notification_system=self.notification_system
        )
        self.actions['investigate'] = InvestigateAction(
            memory_layer=self.memory_layer
        )
        self.actions['isolate'] = IsolateAction(tool_bus=self.tool_bus)
        self.actions['terminate'] = TerminateAction(tool_bus=self.tool_bus)
        self.actions['quarantine'] = QuarantineAction(tool_bus=self.tool_bus)
        self.actions['whitelist'] = WhitelistAction(
            threat_detector=self.threat_detector
        )
        self.actions['log_only'] = LogOnlyAction()
    
    def register_action(self, action: ResponseAction):
        """Register custom response action."""
        self.actions[action.action_id] = action
        logger.info(f"Registered response action: {action.name}")
    
    async def execute_response(self, incident: Dict[str, Any], 
                              recommended_action: str,
                              context: Dict[str, Any] = None) -> ResponsePlan:
        """Execute response to incident.
        
        Args:
            incident: Threat incident data
            recommended_action: Primary response action
            context: Additional context for response
            
        Returns:
            ResponsePlan with execution status
        """
        if context is None:
            context = {}
        
        # Create response plan
        plan = ResponsePlan(
            plan_id=f"RESP_{int(time.time() * 1000)}",
            timestamp=time.time(),
            incident_id=incident.get('incident_id', 'unknown'),
            threat_level=incident.get('threat_level', 'unknown'),
            actions=[recommended_action],
            priority=self._priority_from_threat_level(incident.get('threat_level')),
        )
        
        # Add context
        context['incident'] = incident
        context['affected_processes'] = list(incident.get('affected_processes', []))
        context['affected_files'] = list(incident.get('affected_files', []))
        context['affected_registry'] = list(incident.get('affected_registry', []))
        
        # Execute primary action
        plan.start_time = time.time()
        self.active_responses[plan.plan_id] = plan
        
        try:
            if recommended_action in self.actions:
                action = self.actions[recommended_action]
                success = await action.execute(context)
                
                if success:
                    plan.executed_actions.append(recommended_action)
                    plan.status = ResponseStatus.COMPLETED
                    logger.info(f"Response plan {plan.plan_id} completed successfully")
                else:
                    plan.failed_actions[recommended_action] = "Execution failed"
                    plan.status = ResponseStatus.FAILED
                    logger.error(f"Response plan {plan.plan_id} failed")
                
                # For high-threat incidents, also execute alert
                if incident.get('threat_level') in ['HIGH', 'CRITICAL']:
                    await self.actions['alert'].execute(context)
                    plan.executed_actions.append('alert')
            else:
                logger.warning(f"Unknown response action: {recommended_action}")
                plan.status = ResponseStatus.FAILED
                plan.failed_actions[recommended_action] = "Unknown action"
        
        except Exception as e:
            logger.error(f"Error executing response plan {plan.plan_id}: {e}")
            plan.status = ResponseStatus.FAILED
            plan.failed_actions[recommended_action] = str(e)
        
        finally:
            plan.end_time = time.time()
            self.response_history.append(plan)
            del self.active_responses[plan.plan_id]
            
            # Publish response completion
            if self.event_bus:
                await self.event_bus.publish(
                    topic="sentinel/response_complete",
                    message=plan.to_dict()
                )
        
        return plan
    
    def _priority_from_threat_level(self, threat_level: str) -> int:
        """Convert threat level to priority."""
        level_map = {
            'CRITICAL': 10,
            'HIGH': 8,
            'MEDIUM': 5,
            'LOW': 2,
            'INFO': 0,
        }
        return level_map.get(threat_level, 0)
    
    def get_response_history(self, limit: int = 100) -> List[ResponsePlan]:
        """Get response history."""
        return self.response_history[-limit:]
    
    def get_active_responses(self) -> List[ResponsePlan]:
        """Get currently active response plans."""
        return list(self.active_responses.values())
    
    def get_action_stats(self) -> Dict[str, Any]:
        """Get statistics on all actions."""
        stats = {}
        for action_id, action in self.actions.items():
            stats[action_id] = {
                'name': action.name,
                'execution_count': action.execution_count,
                'last_executed': action.last_executed,
                'async_safe': action.async_safe,
            }
        return stats
    
    def cancel_response(self, plan_id: str) -> bool:
        """Cancel active response plan."""
        if plan_id in self.active_responses:
            plan = self.active_responses[plan_id]
            plan.status = ResponseStatus.CANCELLED
            logger.info(f"Cancelled response plan: {plan_id}")
            return True
        return False


if __name__ == "__main__":
    # Simple test
    orchestrator = ResponseOrchestrator()
    print(f"Registered {len(orchestrator.actions)} response actions")
    print(orchestrator.get_action_stats())
