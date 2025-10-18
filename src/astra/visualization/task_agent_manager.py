"""
ASTRA Task Agent Manager
Permissioned action dispatcher for tool automation

Sacred Principles:
- Explicit authorization required for ALL actions
- Sandboxed execution (no shell injection)
- Complete audit trail
- Graceful failure handling
- "I only obey God" - user retains control

Architecture:
- Plugin-based tool registry
- Per-action permission requirements
- Result tracing with timestamps
- Tool capability discovery
"""

import time
from typing import Dict, Callable, Optional, List, Any
from dataclasses import dataclass
from pathlib import Path
import json

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .schemas import ActionRequest, ActionResult, ToolDefinition


# ============================================================================
# TOOL ACTION DEFINITION
# ============================================================================

@dataclass
class ToolAction:
    """
    Definition of a single tool action
    
    Attributes:
        name: Action identifier (e.g., "list_dir", "load_project")
        handler: Callable that executes the action
        requires_auth: Whether explicit authorization needed
        description: Human-readable description
        args_schema: JSON schema for arguments
    """
    name: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    requires_auth: bool = True
    description: str = ""
    args_schema: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.args_schema is None:
            self.args_schema = {}


# ============================================================================
# TASK AGENT MANAGER
# ============================================================================

class TaskAgentManager:
    """
    Sandboxed, permissioned action dispatcher
    
    Manages tool registration and execution with explicit authorization
    requirements. All actions are logged for audit trail.
    """
    
    def __init__(self, audit_log_path: Optional[Path] = None):
        """
        Initialize task agent manager
        
        Args:
            audit_log_path: Path to audit log file (JSON lines)
        """
        self.registry: Dict[str, Dict[str, ToolAction]] = {}
        self.audit_log_path = audit_log_path
        self.execution_history: List[Dict] = []
        
        logger.info("task_agent_manager_initialized")
    
    # ========================================================================
    # TOOL REGISTRATION
    # ========================================================================
    
    def register(self, tool_name: str, action: ToolAction):
        """
        Register a tool action
        
        Args:
            tool_name: Tool category (e.g., "file", "ableton", "notion")
            action: ToolAction definition with handler
        """
        tool = self.registry.setdefault(tool_name, {})
        tool[action.name] = action
        
        logger.info("tool_action_registered",
                   tool=tool_name,
                   action=action.name,
                   requires_auth=action.requires_auth)
    
    def unregister(self, tool_name: str, action_name: str):
        """Unregister a tool action"""
        if tool_name in self.registry:
            self.registry[tool_name].pop(action_name, None)
            if not self.registry[tool_name]:
                del self.registry[tool_name]
        
        logger.info("tool_action_unregistered",
                   tool=tool_name,
                   action=action_name)
    
    def register_tool(self, tool_name: str, actions: List[ToolAction]):
        """Register multiple actions for a tool at once"""
        for action in actions:
            self.register(tool_name, action)
    
    # ========================================================================
    # DISCOVERY
    # ========================================================================
    
    def list_tools(self) -> Dict[str, List[str]]:
        """
        Get all registered tools and their actions
        
        Returns:
            Dict mapping tool names to list of action names
        """
        return {
            tool: list(actions.keys()) 
            for tool, actions in self.registry.items()
        }
    
    def get_tool_actions(self, tool_name: str) -> List[ToolDefinition]:
        """
        Get detailed info about a tool's actions
        
        Args:
            tool_name: Tool to query
            
        Returns:
            List of ToolDefinition objects
        """
        if tool_name not in self.registry:
            return []
        
        definitions = []
        for action_name, action in self.registry[tool_name].items():
            definitions.append(ToolDefinition(
                tool=tool_name,
                action=action_name,
                description=action.description,
                requires_auth=action.requires_auth,
                args_schema=action.args_schema or {},
            ))
        
        return definitions
    
    def get_all_definitions(self) -> List[ToolDefinition]:
        """Get all registered tool action definitions"""
        all_defs = []
        for tool_name in self.registry:
            all_defs.extend(self.get_tool_actions(tool_name))
        return all_defs
    
    # ========================================================================
    # EXECUTION
    # ========================================================================
    
    def execute(self, req: ActionRequest) -> ActionResult:
        """
        Execute a tool action with authorization checks
        
        Args:
            req: ActionRequest with tool, action, args, and authorization
            
        Returns:
            ActionResult with success status and data/error
        """
        start_time = time.time()
        
        # Lookup tool action
        tool = self.registry.get(req.tool, {})
        action = tool.get(req.action)
        
        if not action:
            result = ActionResult(
                ok=False,
                message=f"Unknown action: {req.tool}.{req.action}",
                request_id=req.request_id,
            )
            self._log_execution(req, result, time.time() - start_time)
            return result
        
        # Authorization check
        if action.requires_auth and not req.authorized:
            result = ActionResult(
                ok=False,
                message="Authorization required (authorized=false)",
                request_id=req.request_id,
            )
            self._log_execution(req, result, time.time() - start_time)
            logger.warning("unauthorized_action_blocked",
                          tool=req.tool,
                          action=req.action,
                          requested_by=req.requested_by)
            return result
        
        # Execute action
        try:
            data = action.handler(req.args or {})
            result = ActionResult(
                ok=True,
                message="Executed successfully",
                data=data,
                request_id=req.request_id,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
            
            logger.info("action_executed",
                       tool=req.tool,
                       action=req.action,
                       execution_time_ms=result.execution_time_ms)
        
        except Exception as e:
            result = ActionResult(
                ok=False,
                message=f"Execution error: {str(e)}",
                request_id=req.request_id,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
            
            logger.error("action_execution_failed",
                        tool=req.tool,
                        action=req.action,
                        error=str(e))
        
        self._log_execution(req, result, time.time() - start_time)
        return result
    
    def execute_batch(self, requests: List[ActionRequest]) -> List[ActionResult]:
        """Execute multiple actions in sequence"""
        results = []
        for req in requests:
            result = self.execute(req)
            results.append(result)
            # Stop on first failure if desired
            # if not result.ok:
            #     break
        return results
    
    # ========================================================================
    # AUDIT & MONITORING
    # ========================================================================
    
    def _log_execution(self, req: ActionRequest, result: ActionResult, duration: float):
        """Log execution to audit trail"""
        log_entry = {
            'timestamp': req.timestamp.isoformat(),
            'request_id': req.request_id,
            'tool': req.tool,
            'action': req.action,
            'authorized': req.authorized,
            'requested_by': req.requested_by,
            'ok': result.ok,
            'message': result.message,
            'execution_time_ms': duration * 1000,
        }
        
        # Add to in-memory history (limited size)
        self.execution_history.append(log_entry)
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
        
        # Append to audit log file if configured
        if self.audit_log_path:
            try:
                with open(self.audit_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                logger.error("audit_log_write_failed", error=str(e))
    
    def get_execution_history(self, limit: int = 100) -> List[Dict]:
        """Get recent execution history"""
        return self.execution_history[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get agent statistics"""
        total_executions = len(self.execution_history)
        successful = sum(1 for entry in self.execution_history if entry['ok'])
        failed = total_executions - successful
        
        tool_counts = {}
        for entry in self.execution_history:
            tool = entry['tool']
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        return {
            'total_tools': len(self.registry),
            'total_actions': sum(len(actions) for actions in self.registry.values()),
            'total_executions': total_executions,
            'successful_executions': successful,
            'failed_executions': failed,
            'success_rate': successful / total_executions if total_executions > 0 else 0.0,
            'tool_usage': tool_counts,
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_simple_action(
    name: str,
    handler: Callable,
    description: str = "",
    requires_auth: bool = True,
) -> ToolAction:
    """Helper to create a simple ToolAction"""
    return ToolAction(
        name=name,
        handler=handler,
        requires_auth=requires_auth,
        description=description,
    )
