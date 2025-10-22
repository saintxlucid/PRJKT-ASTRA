"""
ASTRA Tool Registry
Manages available tools and their execution contexts

Architecture:
- Tool registration and discovery
- Runtime execution context 
- Permission management
- Cost tracking
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import inspect
import time
import uuid

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ToolScope(str, Enum):
    """Tool visibility and access scope"""
    SYSTEM = "system"  # Core system tools
    USER = "user"      # User-accessible tools
    ADMIN = "admin"    # Administrative tools


class ToolPermission(str, Enum):
    """Permission levels for tool execution"""
    READ = "read"      # Read-only operations
    WRITE = "write"    # File/state modifications
    EXECUTE = "exec"   # Process execution
    NETWORK = "net"    # Network access
    ADMIN = "admin"    # System changes


@dataclass
class ToolSignature:
    """Function signature and metadata"""
    name: str
    doc: str
    params: Dict[str, Dict]
    return_type: Optional[str]
    is_async: bool = False
    is_generator: bool = False


@dataclass
class ToolInfo:
    """Registered tool information"""
    name: str
    scope: ToolScope
    permissions: List[ToolPermission]
    fn: Callable
    signature: ToolSignature
    cost_estimate: float = 1.0
    timeout: float = 30.0
    enabled: bool = True
    metadata: Dict = field(default_factory=dict)


@dataclass 
class ToolContext:
    """Execution context for a tool invocation"""
    context_id: str
    tool: ToolInfo
    args: Dict[str, Any]
    start_time: datetime
    timeout: float
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0


class ToolRegistry:
    """
    Central registry for tool registration and execution
    
    Responsibilities:
    - Tool registration and discovery
    - Permission checking
    - Execution tracking
    - Cost management
    """
    
    def __init__(self):
        """Initialize tool registry"""
        self.tools: Dict[str, ToolInfo] = {}
        self.contexts: Dict[str, ToolContext] = {}
        self.history: List[ToolContext] = []
        self._shutdown = False
        self._cleanup_task = None

    def register(
        self,
        name: str,
        scope: Union[ToolScope, str],
        permissions: List[Union[ToolPermission, str]],
        cost_estimate: float = 1.0,
        timeout: float = 30.0,
        metadata: Optional[Dict] = None
    ) -> Callable:
        """
        Register tool via decorator
        
        Usage:
            @registry.register(
                name="my_tool",
                scope=ToolScope.USER,
                permissions=[ToolPermission.READ]
            )
            async def my_tool(arg1: str) -> str:
                ...
                
        Args:
            name: Tool name/id
            scope: Access scope 
            permissions: Required permissions
            cost_estimate: Computational cost estimate
            timeout: Default timeout in seconds
            metadata: Additional tool info
            
        Returns:
            Decorator function
        """
        def decorator(fn: Callable) -> Callable:
            # Get signature info
            sig = inspect.signature(fn)
            doc = inspect.getdoc(fn) or ""
            
            # Parse parameters
            params = {}
            for name, param in sig.parameters.items():
                param_info = {
                    "name": name,
                    "type": str(param.annotation)
                    if param.annotation != inspect.Parameter.empty
                    else "Any",
                    "default": None
                    if param.default == inspect.Parameter.empty
                    else param.default
                }
                params[name] = param_info
                
            # Create signature
            signature = ToolSignature(
                name=name,
                doc=doc,
                params=params,
                return_type=str(sig.return_annotation)
                if sig.return_annotation != inspect.Parameter.empty
                else None,
                is_async=asyncio.iscoroutinefunction(fn),
                is_generator=inspect.isgeneratorfunction(fn)
            )
            
            # Create tool info
            info = ToolInfo(
                name=name,
                scope=ToolScope(scope) if isinstance(scope, str) else scope,
                permissions=[ToolPermission(p) if isinstance(p, str) else p for p in permissions],
                fn=fn,
                signature=signature,
                cost_estimate=cost_estimate,
                timeout=timeout,
                metadata=metadata or {}
            )
            
            # Register tool
            self.tools[name] = info
            logger.info(
                "tool_registered",
                name=name,
                scope=info.scope,
                permissions=info.permissions
            )
            
            return fn
            
        return decorator

    async def execute(
        self,
        name: str,
        args: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute registered tool
        
        Args:
            name: Tool name/id
            args: Execution arguments
            timeout: Optional timeout override
            
        Returns:
            Tool execution result
        """
        # Validate tool exists
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")
            
        tool = self.tools[name]
        if not tool.enabled:
            raise RuntimeError(f"Tool disabled: {name}")
            
        # Create context
        context_id = str(uuid.uuid4())
        context = ToolContext(
            context_id=context_id,
            tool=tool,
            args=args,
            start_time=datetime.utcnow(),
            timeout=timeout or tool.timeout
        )
        
        try:
            # Track context
            self.contexts[context_id] = context
            
            # Execute with timeout
            if tool.signature.is_async:
                result = await asyncio.wait_for(
                    tool.fn(**args),
                    timeout=context.timeout
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: tool.fn(**args)
                )
                
            # Update context
            context.result = result
            context.duration = (
                datetime.utcnow() - context.start_time
            ).total_seconds()
            
            return result
            
        except asyncio.TimeoutError:
            context.error = f"Timeout after {context.timeout}s"
            raise
            
        except Exception as e:
            context.error = str(e)
            raise
            
        finally:
            # Move to history
            if context_id in self.contexts:
                del self.contexts[context_id]
                self.history.append(context)
                
            # Log execution
            if context.error:
                logger.warning(
                    "tool_execution_failed",
                    tool=name,
                    error=context.error,
                    duration=context.duration
                )
            else:
                logger.info(
                    "tool_execution_completed", 
                    tool=name,
                    duration=context.duration
                )

    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """Get registered tool info"""
        return self.tools.get(name)
        
    def list_tools(self) -> List[ToolInfo]:
        """Get all registered tools"""
        return list(self.tools.values())
        
    def disable_tool(self, name: str) -> None:
        """Disable tool execution"""
        if name in self.tools:
            self.tools[name].enabled = False
            
    def enable_tool(self, name: str) -> None:
        """Enable tool execution"""
        if name in self.tools:
            self.tools[name].enabled = True

    async def start(self) -> None:
        """Start registry background tasks"""
        self._shutdown = False
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    async def stop(self) -> None:
        """Stop registry background tasks"""
        self._shutdown = True
        if self._cleanup_task:
            await self._cleanup_task
            
    async def _cleanup_loop(self) -> None:
        """Clean up stale execution contexts"""
        while not self._shutdown:
            try:
                now = datetime.utcnow()
                
                # Find stale contexts
                stale = []
                for ctx_id, ctx in self.contexts.items():
                    duration = (now - ctx.start_time).total_seconds()
                    if duration > ctx.timeout * 2:
                        stale.append(ctx_id)
                        
                # Move to history
                for ctx_id in stale:
                    ctx = self.contexts[ctx_id]
                    ctx.error = f"Abandoned after {ctx.timeout * 2}s"
                    del self.contexts[ctx_id]
                    self.history.append(ctx)
                    
                    logger.warning(
                        "stale_context_removed",
                        tool=ctx.tool.name,
                        duration=ctx.duration
                    )
                    
            except Exception as e:
                logger.error("cleanup_error", error=str(e))
                
            finally:
                await asyncio.sleep(60.0)  # Check every minute