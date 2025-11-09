"""
Agent Kernel API Routes
========================

REST API endpoints for ASTRA's autonomous agent kernel.
Provides task execution, browser automation, and tool management.

Features:
- Autonomous task execution with ReAct planning
- Browser automation and control
- Tool registry and execution
- Task monitoring and cancellation
- Memory-aware agent coordination

Sacred Code: 333
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/v1/agent", tags=["Agent Kernel"])


# ============================================================================
# Global Task Store (simple in-memory for now)
# ============================================================================

class TaskStore:
    """In-memory task storage"""
    def __init__(self):
        self.tasks: dict[str, dict] = {}
    
    def create(self, task_id: str, task_data: dict):
        self.tasks[task_id] = task_data
    
    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)
    
    def update(self, task_id: str, updates: dict):
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)
    
    def list_all(self) -> list[dict]:
        return list(self.tasks.values())
    
    def delete(self, task_id: str):
        self.tasks.pop(task_id, None)


task_store = TaskStore()


# ============================================================================
# Request/Response Models
# ============================================================================

class TaskRequest(BaseModel):
    """Request to create autonomous task"""
    goal: str = Field(..., description="High-level goal for the agent")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    max_iterations: int = Field(10, ge=1, le=50, description="Max planning iterations")
    timeout_seconds: int = Field(180, ge=10, le=600, description="Task timeout")
    tools: list[str] = Field(default_factory=list, description="Allowed tools (empty = all)")


class TaskResponse(BaseModel):
    """Response for task creation"""
    task_id: str
    status: str
    created_at: float
    goal: str


class TaskStatus(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    goal: str
    created_at: float
    updated_at: float
    iterations: int
    tool_calls: int
    result: Any = None
    error: str | None = None
    history: list[dict] = Field(default_factory=list)


class BrowserNavigate(BaseModel):
    """Navigate browser to URL"""
    url: str = Field(..., description="URL to navigate to")
    wait_for_load: bool = Field(True, description="Wait for page load")


class BrowserClick(BaseModel):
    """Click element in browser"""
    selector: str = Field(..., description="CSS selector for element")
    wait_for_element: bool = Field(True, description="Wait for element to appear")


class BrowserType(BaseModel):
    """Type text in browser"""
    selector: str = Field(..., description="CSS selector for input element")
    text: str = Field(..., description="Text to type")
    clear_first: bool = Field(True, description="Clear existing text first")


class BrowserExtract(BaseModel):
    """Extract data from browser"""
    selector: str = Field(..., description="CSS selector for element(s)")
    attribute: str | None = Field(None, description="Extract attribute (null = text content)")
    all: bool = Field(False, description="Extract all matches")


class ToolExecution(BaseModel):
    """Execute a tool"""
    tool_name: str = Field(..., description="Name of tool to execute")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    token: str | None = Field(None, description="Authorization token (if required)")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_agent_kernel(request: Request):
    """Get Agent Kernel from app state"""
    if not hasattr(request.app.state, "agent_kernel"):
        raise HTTPException(
            status_code=503,
            detail="Agent Kernel not available. Autonomous agent capabilities require agent_kernel module."
        )
    return request.app.state.agent_kernel


def get_tool_registry(request: Request):
    """Get Tool Registry from app state"""
    if not hasattr(request.app.state, "tool_registry"):
        raise HTTPException(
            status_code=503,
            detail="Tool Registry not available."
        )
    return request.app.state.tool_registry


# ============================================================================
# Task Management
# ============================================================================

@router.post("/task", response_model=TaskResponse)
async def create_task(
    task: TaskRequest,
    background_tasks: BackgroundTasks,
    agent_kernel = Depends(get_agent_kernel)
):
    """
    **Create Autonomous Task**
    
    Submit a high-level goal and let the agent autonomously plan and execute.
    Uses ReAct (Reasoning + Acting) planning loop.
    
    Task executes asynchronously in background. Use GET /agent/task/{id} to monitor.
    """
    try:
        task_id = str(uuid.uuid4())
        created_at = time.time()
        
        # Create task record
        task_data = {
            "task_id": task_id,
            "status": "queued",
            "goal": task.goal,
            "created_at": created_at,
            "updated_at": created_at,
            "iterations": 0,
            "tool_calls": 0,
            "result": None,
            "error": None,
            "history": [],
            "context": task.context,
            "max_iterations": task.max_iterations,
            "timeout_seconds": task.timeout_seconds,
        }
        
        task_store.create(task_id, task_data)
        
        # Schedule task execution in background
        background_tasks.add_task(
            execute_agent_task,
            task_id,
            task.goal,
            task.context,
            task.max_iterations,
            task.timeout_seconds,
            agent_kernel
        )
        
        logger.info("task_created", task_id=task_id, goal=task.goal)
        
        return TaskResponse(
            task_id=task_id,
            status="queued",
            created_at=created_at,
            goal=task.goal
        )
        
    except Exception as e:
        logger.error("create_task_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}") from None


async def execute_agent_task(
    task_id: str,
    goal: str,
    context: dict,
    max_iterations: int,
    timeout_seconds: int,
    agent_kernel
):
    """Background task executor for agent tasks"""
    try:
        # Update status to running
        task_store.update(task_id, {
            "status": "running",
            "updated_at": time.time()
        })
        
        # Execute agent loop
        result = await asyncio.wait_for(
            agent_kernel.run(
                user_goal=goal,
                context=context,
                max_iterations=max_iterations
            ),
            timeout=timeout_seconds
        )
        
        # Update with success
        task_store.update(task_id, {
            "status": "completed",
            "updated_at": time.time(),
            "result": result,
            "iterations": agent_kernel.iteration,
            "tool_calls": agent_kernel.tool_calls,
            "history": agent_kernel.history
        })
        
        logger.info("task_completed", task_id=task_id, iterations=agent_kernel.iteration)
        
    except asyncio.TimeoutError:
        task_store.update(task_id, {
            "status": "timeout",
            "updated_at": time.time(),
            "error": f"Task exceeded timeout of {timeout_seconds}s"
        })
        logger.warning("task_timeout", task_id=task_id, timeout=timeout_seconds)
        
    except Exception as e:
        task_store.update(task_id, {
            "status": "failed",
            "updated_at": time.time(),
            "error": str(e)
        })
        logger.error("task_failed", task_id=task_id, error=str(e))


@router.get("/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    **Get Task Status**
    
    Retrieve current status and execution details for a task.
    """
    task_data = task_store.get(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return TaskStatus(**task_data)


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """
    **Cancel Task**
    
    Cancel a running or queued task.
    Note: Cancellation may not be immediate for running tasks.
    """
    task_data = task_store.get(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    if task_data["status"] in ("completed", "failed", "timeout"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status: {task_data['status']}"
        )
    
    # Mark as cancelled
    task_store.update(task_id, {
        "status": "cancelled",
        "updated_at": time.time()
    })
    
    logger.info("task_cancelled", task_id=task_id)
    
    return {
        "success": True,
        "task_id": task_id,
        "status": "cancelled"
    }


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    limit: int = 50
):
    """
    **List All Tasks**
    
    Retrieve list of all tasks, optionally filtered by status.
    """
    tasks = task_store.list_all()
    
    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    
    # Limit results
    tasks = tasks[:limit]
    
    return {
        "success": True,
        "count": len(tasks),
        "tasks": tasks
    }


# ============================================================================
# Browser Automation
# ============================================================================

@router.post("/browser/navigate")
async def browser_navigate(
    nav: BrowserNavigate,
    tool_registry = Depends(get_tool_registry)
):
    """
    **Navigate Browser**
    
    Navigate browser to specified URL.
    """
    try:
        # Get browser tool
        browser_tool = tool_registry.get("browser.navigate")
        
        if not browser_tool:
            raise HTTPException(status_code=501, detail="Browser automation not available")
        
        # Execute navigation
        result = browser_tool({
            "url": nav.url,
            "wait_for_load": nav.wait_for_load
        }, token=None)  # TODO: Add token support
        
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail=result.get("error", "Navigation failed"))
        
        return {
            "success": True,
            "url": nav.url,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("browser_navigate_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Navigation failed: {str(e)}") from None


@router.post("/browser/click")
async def browser_click(
    click: BrowserClick,
    tool_registry = Depends(get_tool_registry)
):
    """
    **Click Browser Element**
    
    Click element matching CSS selector.
    """
    try:
        browser_tool = tool_registry.get("browser.click")
        
        if not browser_tool:
            raise HTTPException(status_code=501, detail="Browser automation not available")
        
        result = browser_tool({
            "selector": click.selector,
            "wait_for_element": click.wait_for_element
        }, token=None)
        
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail=result.get("error", "Click failed"))
        
        return {
            "success": True,
            "selector": click.selector,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("browser_click_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Click failed: {str(e)}") from None


@router.post("/browser/type")
async def browser_type(
    type_req: BrowserType,
    tool_registry = Depends(get_tool_registry)
):
    """
    **Type in Browser**
    
    Type text into element matching CSS selector.
    """
    try:
        browser_tool = tool_registry.get("browser.type")
        
        if not browser_tool:
            raise HTTPException(status_code=501, detail="Browser automation not available")
        
        result = browser_tool({
            "selector": type_req.selector,
            "text": type_req.text,
            "clear_first": type_req.clear_first
        }, token=None)
        
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail=result.get("error", "Type failed"))
        
        return {
            "success": True,
            "selector": type_req.selector,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("browser_type_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Type failed: {str(e)}") from None


@router.post("/browser/extract")
async def browser_extract(
    extract: BrowserExtract,
    tool_registry = Depends(get_tool_registry)
):
    """
    **Extract Data from Browser**
    
    Extract text or attributes from elements matching CSS selector.
    """
    try:
        browser_tool = tool_registry.get("browser.extract")
        
        if not browser_tool:
            raise HTTPException(status_code=501, detail="Browser automation not available")
        
        result = browser_tool({
            "selector": extract.selector,
            "attribute": extract.attribute,
            "all": extract.all
        }, token=None)
        
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail=result.get("error", "Extract failed"))
        
        return {
            "success": True,
            "selector": extract.selector,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("browser_extract_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Extract failed: {str(e)}") from None


# ============================================================================
# Tool Management
# ============================================================================

@router.get("/tools")
async def list_tools(
    tool_registry = Depends(get_tool_registry)
):
    """
    **List Available Tools**
    
    Returns all registered tools with their descriptions and requirements.
    """
    try:
        tools = tool_registry.list_tools()
        
        tool_list = [
            {
                "name": tool.name,
                "description": tool.description,
                "scope": tool.scope,
                "policy": tool.policy,
                "requires_token": tool.requires_token
            }
            for tool in tools
        ]
        
        return {
            "success": True,
            "count": len(tool_list),
            "tools": tool_list
        }
        
    except Exception as e:
        logger.error("list_tools_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}") from None


@router.post("/tool/execute")
async def execute_tool(
    execution: ToolExecution,
    tool_registry = Depends(get_tool_registry)
):
    """
    **Execute Tool**
    
    Directly execute a registered tool with provided arguments.
    
    **Warning**: Some tools require authorization tokens.
    """
    try:
        tool = tool_registry.get(execution.tool_name)
        
        if not tool:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{execution.tool_name}' not found"
            )
        
        # Execute tool
        result = tool(execution.args, token=execution.token)
        
        if not result.get("ok"):
            return {
                "success": False,
                "tool": execution.tool_name,
                "error": result.get("error", "Tool execution failed"),
                "result": result
            }
        
        return {
            "success": True,
            "tool": execution.tool_name,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("execute_tool_error", tool=execution.tool_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}") from None


# ============================================================================
# Agent Status
# ============================================================================

@router.get("/status")
async def agent_status(
    agent_kernel = Depends(get_agent_kernel)
):
    """
    **Agent Kernel Status**
    
    Returns current status of the agent kernel.
    """
    try:
        return {
            "success": True,
            "available": True,
            "state": agent_kernel.state.value if hasattr(agent_kernel, "state") else "idle",
            "current_iteration": agent_kernel.iteration if hasattr(agent_kernel, "iteration") else 0,
            "tool_calls": agent_kernel.tool_calls if hasattr(agent_kernel, "tool_calls") else 0,
            "max_iterations": agent_kernel.max_iterations if hasattr(agent_kernel, "max_iterations") else 0,
            "active_tasks": len([t for t in task_store.list_all() if t["status"] in ("queued", "running")])
        }
        
    except Exception as e:
        logger.error("agent_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}") from None
