"""
Local tool registry with safe, pre-approved tools.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition with metadata."""
    name: str
    description: str
    function: Callable
    risk_level: str  # "LOW", "NORMAL", "HIGH", "CRITICAL"
    parameters: dict[str, str]  # {param_name: description}


class LocalToolRegistry:
    """Registry of safe, pre-approved local tools."""

    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default safe tools."""

        # Tool 1: Read file (LOW risk)
        self.register(ToolDefinition(
            name="read_file",
            description="Read contents of a text file",
            function=self._tool_read_file,
            risk_level="LOW",
            parameters={"file_path": "Path to file to read"}
        ))

        # Tool 2: List directory (LOW risk)
        self.register(ToolDefinition(
            name="list_dir",
            description="List files in a directory",
            function=self._tool_list_dir,
            risk_level="LOW",
            parameters={"directory": "Directory path"}
        ))

        # Tool 3: Get CPU info (LOW risk)
        self.register(ToolDefinition(
            name="get_cpu_info",
            description="Get CPU usage and info",
            function=self._tool_get_cpu_info,
            risk_level="LOW",
            parameters={}
        ))

        # Tool 4: Get memory info (LOW risk)
        self.register(ToolDefinition(
            name="get_memory_info",
            description="Get memory usage and info",
            function=self._tool_get_memory_info,
            risk_level="LOW",
            parameters={}
        ))

        # Tool 5: Search knowledge base (LOW risk)
        self.register(ToolDefinition(
            name="search_knowledge",
            description="Search vector store knowledge base",
            function=self._tool_search_knowledge,
            risk_level="LOW",
            parameters={"query": "Search query"}
        ))

    def register(self, tool: ToolDefinition):
        """Register a new tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (risk={tool.risk_level})")

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool."""

        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]
        result = await tool.function(**kwargs)

        return result

    # Default tool implementations

    async def _tool_read_file(self, file_path: str) -> str:
        """Read file contents."""
        try:
            with open(file_path) as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    async def _tool_list_dir(self, directory: str) -> list[str]:
        """List directory contents."""
        try:
            return [str(p) for p in Path(directory).iterdir()]
        except Exception as e:
            return [f"Error listing directory: {e}"]

    async def _tool_get_cpu_info(self) -> dict[str, Any]:
        """Get CPU info."""
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
        }

    async def _tool_get_memory_info(self) -> dict[str, Any]:
        """Get memory info."""
        mem = psutil.virtual_memory()
        return {
            "total_mb": mem.total / (1024 * 1024),
            "available_mb": mem.available / (1024 * 1024),
            "percent": mem.percent,
        }

    async def _tool_search_knowledge(self, query: str) -> list[str]:
        """Search knowledge base (placeholder)."""
        return [f"Search result for: {query}"]

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "risk_level": tool.risk_level,
                "parameters": tool.parameters,
            }
            for tool in self.tools.values()
        ]
