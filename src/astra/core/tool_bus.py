"""
ASTRA Tool Bus
Core infrastructure for tool registration, validation, and execution.
Created: October 16, 2025
"""
from __future__ import annotations
from typing import Dict, Any, Callable, Optional, Type
from pathlib import Path
import asyncio
import structlog
from pydantic import BaseModel, create_model
import functools
import inspect
import json
import sys

from .event_bus import get_event_bus

logger = structlog.get_logger()

class ToolError(Exception):
    """Base exception for tool errors"""
    pass

class ToolTimeoutError(ToolError):
    """Raised when a tool execution times out"""
    pass

class ToolValidationError(ToolError):
    """Raised when tool arguments fail validation"""
    pass

class ToolContext(BaseModel):
    """Execution context for a tool"""
    tool_id: str
    timeout: Optional[float] = None
    dry_run: bool = False
    metadata: Dict[str, Any] = {}

class ToolRegistry:
    """
    Central registry for all ASTRA tools.
    Handles registration, validation, and execution.
    """
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        logger.info("Tool registry initialized")

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        schema: Dict[str, Any],
        timeout: Optional[float] = None,
        isolated: bool = False
    ) -> None:
        """
        Register a new tool.
        Args:
            name: Unique tool identifier
            description: Tool description 
            handler: Function that implements the tool
            schema: JSON schema for tool arguments
            timeout: Optional execution timeout in seconds
            isolated: Whether to run in isolated process
        """
        if name in self._tools:
            raise ValueError(f"Tool {name} already registered")

        # Create Pydantic model for args
        fields = {}
        for field_name, field_schema in schema["properties"].items():
            field_type = self._get_type(field_schema)
            is_required = field_name in schema.get("required", [])
            default_value = ... if is_required else None
            fields[field_name] = (field_type, default_value)

        model = create_model(
            f"{name.title()}Args",
            __base__=BaseModel,
            **fields
        )

        tool = Tool(
            name=name,
            description=description,
            handler=handler,
            arg_model=model,
            timeout=timeout,
            isolated=isolated
        )
        
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def _get_type(self, schema: Dict[str, Any]) -> Type:
        """Convert JSON schema type to Python type"""
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_map.get(schema["type"], Any)

    async def execute(
        self,
        name: str,
        args: Dict[str, Any],
        context: Optional[ToolContext] = None
    ) -> Any:
        """
        Execute a registered tool.
        Args:
            name: Tool name to execute
            args: Arguments for the tool
            context: Optional execution context
        Returns:
            Tool execution result
        Raises:
            ToolError: If execution fails
        """
        if name not in self._tools:
            raise ToolError(f"Tool {name} not found")

        tool = self._tools[name]
        event_bus = get_event_bus()
        
        # Validate arguments
        try:
            validated_args = tool.arg_model(**args)
        except Exception as e:
            raise ToolValidationError(f"Invalid arguments: {str(e)}")

        # Create default context if none provided
        if context is None:
            context = ToolContext(tool_id=name)

        # Override timeout from context
        timeout = context.timeout if context.timeout is not None else tool.timeout

        # Emit before event
        event_bus.emit("astra.tool.before", {
            "tool": name,
            "args": args,
            "context": context.model_dump() if context else None
        })

        try:
            result = None
            if tool.isolated:
                # Run in separate process
                result = await self._run_isolated(tool, validated_args, timeout)
            else:
                # Run in current process
                if timeout:
                    result = await asyncio.wait_for(
                        tool.handler(**validated_args.model_dump()),
                        timeout=timeout
                    )
                else:
                    result = await tool.handler(**validated_args.model_dump())
                    
            # Emit success event
            event_bus.emit("astra.tool.executed", {
                "tool": name,
                "args": args,
                "context": context.model_dump() if context else None,
                "result": result,
                "success": True
            })
            
            return result

        except asyncio.TimeoutError as e:
            # Emit failure event
            event_bus.emit("astra.tool.executed", {
                "tool": name,
                "args": args,
                "context": context.model_dump() if context else None,
                "error": str(e),
                "success": False,
                "error_type": "timeout"
            })
            raise ToolTimeoutError(f"Tool {name} timed out after {timeout}s")
            
        except Exception as e:
            # Emit failure event
            event_bus.emit("astra.tool.executed", {
                "tool": name,
                "args": args,
                "context": context.model_dump() if context else None,
                "error": str(e),
                "success": False,
                "error_type": "execution"
            })
            raise ToolError(f"Tool execution failed: {str(e)}")

    async def _run_isolated(
        self,
        tool: Tool,
        args: BaseModel,
        timeout: Optional[float]
    ) -> Any:
        """Run a tool in an isolated process"""
        # Create subprocess
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            f"import asyncio; asyncio.run(tool.handler(**{args.dict()}))",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            if proc.returncode != 0:
                raise ToolError(f"Tool failed: {stderr.decode()}")
            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            proc.kill()
            raise ToolTimeoutError(f"Tool timed out after {timeout}s")

class Tool:
    """Registered tool definition"""
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        arg_model: Type[BaseModel],
        timeout: Optional[float] = None,
        isolated: bool = False
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.arg_model = arg_model
        self.timeout = timeout
        self.isolated = isolated

# Global registry instance
_registry: Optional[ToolRegistry] = None

def get_registry() -> ToolRegistry:
    """Get the global tool registry"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry

def initialize_registry() -> ToolRegistry:
    """Initialize and return the global tool registry"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        logger.info("Tool registry initialized")
    return _registry

def tool(
    name: str,
    description: str,
    schema: Dict[str, Any],
    timeout: Optional[float] = None,
    isolated: bool = False
):
    """
    Decorator to register a tool.
    Example:
        @tool(
            name="file_read",
            description="Read a file",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        )
        async def read_file(path: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        registry = get_registry()
        registry.register(
            name=name,
            description=description,
            handler=func,
            schema=schema,
            timeout=timeout,
            isolated=isolated
        )
        return func
    return decorator