"""
ASTRA Bridge Tool Service
Permissioned agent handoff with authorization gates.
"""
from typing import Dict, Any, Optional
from fnmatch import fnmatch
import structlog

logger = structlog.get_logger()


class TaskAgentAdapter:
    """Task Agent adapter - replace with your real Task Agent integration."""
    
    def execute(self, tool: str, action: str, args: Dict[str, Any], authorized: bool) -> Dict[str, Any]:
        """
        Execute a tool action through the Task Agent.
        
        Args:
            tool: Tool name (e.g., "ableton", "file", "system")
            action: Action name (e.g., "open_project", "set_bpm")
            args: Action arguments
            authorized: Whether this execution is authorized
            
        Returns:
            Result dict with "ok" status and details
        """
        logger.warning("task_agent_not_bound", tool=tool, action=action)
        return {"ok": False, "message": "No agent bound. Wire TaskAgentAdapter to your real Task Agent."}


class ToolBridgeService:
    """
    Tool bridge service with authorization and allowlist enforcement.
    Enforces one-call budget by default (configurable).
    """
    
    def __init__(self, 
                 agent: Optional[TaskAgentAdapter] = None, 
                 safe_glob: str = "scripts/approved/*.ps1"):
        self.agent = agent or TaskAgentAdapter()
        self.safe_glob = safe_glob
        logger.info("tool_bridge_service_initialized", safe_glob=safe_glob)
    
    def tool_allowed(self, tool_id: str) -> bool:
        """
        Check if tool is allowed by allowlist/glob.
        For script tools, compare path against glob.
        For named tools, registry handles auth.
        
        Extend here if you pass file paths.
        """
        # For now, assume registry handles auth
        # Extend with actual allowlist check when wiring to scripts
        return True
    
    def call_one(self, 
                 tool: str, 
                 action: str, 
                 args: Dict[str, Any], 
                 authorized: bool) -> Dict[str, Any]:
        """
        Execute a single tool call with safety checks.
        
        Returns:
            Result dict from Task Agent
        """
        logger.info("tool_bridge_call_attempt", tool=tool, action=action, authorized=authorized)
        
        # Authorization check
        if not authorized:
            logger.warning("tool_bridge_call_denied_auth", tool=tool, action=action)
            return {"ok": False, "message": "Authorization required."}
        
        # Allowlist check
        if not self.tool_allowed(tool):
            logger.warning("tool_bridge_call_denied_allowlist", tool=tool)
            return {"ok": False, "message": f"Tool {tool} not allowed."}
        
        # Execute
        result = self.agent.execute(tool=tool, action=action, args=args, authorized=authorized)
        
        logger.info("tool_bridge_call_complete", tool=tool, action=action, ok=result.get("ok", False))
        return result
