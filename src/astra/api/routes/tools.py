"""
Tool Bus API routes.

This module provides FastAPI routes for tool execution and management,
including policy enforcement, consent checking, and audit logging.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from astra.security.tokenizer import verify_execution_token
from astra.security.policy_engine import get_policy_engine
from astra.telemetry.audit import AuditLogger
from astra.telemetry.tool_bus_metrics import ToolBusMetrics
from astra.core.tool_bus import get_registry

router = APIRouter(prefix="/v1/tools", tags=["tools"])
audit = AuditLogger(__name__)


class ToolPreviewRequest(BaseModel):
    """Preview tool execution request."""
    tool_name: str
    args: Dict[str, Any]
    token: Optional[str] = None


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    tool_name: str
    args: Dict[str, Any]
    token: str


class ToolResponse(BaseModel):
    """Tool execution response."""
    ok: bool
    result: Optional[Any] = None
    error: Optional[str] = None


async def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode execution token."""
    try:
        return verify_execution_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/preview", response_model=ToolResponse)
async def preview_tool(request: ToolPreviewRequest, http_request: Request):
    """
    Preview tool execution without actually running it.
    Performs policy validation and returns expected behavior.
    """
    start_time = time.time()
    tool_registry = get_registry()
    policy = get_policy_engine()
    
    # Check if tool exists
    if request.tool_name not in tool_registry.tools:
        ToolBusMetrics.record_api_request(
            endpoint="/v1/tools/preview",
            method=http_request.method,
            status_code=404,
            duration=time.time() - start_time
        )
        return ToolResponse(
            ok=False,
            error=f"Tool not found: {request.tool_name}"
        )

    # Run policy check
    policy_result = policy.check_tool_execution(
        tool_name=request.tool_name,
        args=request.args
    )

    if not policy_result.allowed:
        return ToolResponse(
            ok=False,
            error=f"Policy violation: {policy_result.reason}"
        )

    # If token provided, verify it's valid
    if request.token:
        try:
            token_data = await verify_token(request.token)
            if token_data["tool"] != request.tool_name:
                return ToolResponse(
                    ok=False,
                    error="Token does not match requested tool"
                )
        except Exception as e:
            return ToolResponse(
                ok=False,
                error=f"Invalid token: {str(e)}"
            )

    return ToolResponse(
        ok=True,
        result={
            "can_execute": True,
            "requires_consent": policy_result.requires_consent,
            "estimated_impact": policy_result.impact_assessment
        }
    )


@router.post("/execute", response_model=ToolResponse)
async def execute_tool(request: ToolExecuteRequest, http_request: Request):
    """
    Execute a tool with safety checks and audit logging.
    Requires a valid execution token.
    """
    start_time = time.time()
    execution_start = None
    
    # Verify token first
    try:
        token_data = await verify_token(request.token)
        ToolBusMetrics.record_token_validation(valid=True)
        
        if token_data["tool"] != request.tool_name:
            ToolBusMetrics.record_api_request(
                endpoint="/v1/tools/execute",
                method=http_request.method,
                status_code=401,
                duration=time.time() - start_time
            )
            raise HTTPException(
                status_code=401,
                detail="Token does not match requested tool"
            )
    except Exception as e:
        audit.log_event(
            "tool_execution_unauthorized",
            tool=request.tool_name,
            error=str(e)
        )
        raise

    # Get tool registry and verify tool exists
    tool_registry = get_registry()
    if request.tool_name not in tool_registry.tools:
        audit.log_event(
            "tool_not_found",
            tool=request.tool_name
        )
        raise HTTPException(
            status_code=404,
            detail=f"Tool not found: {request.tool_name}"
        )

    # Run tool with audit logging
    try:
        audit.log_event(
            "tool_execution_start",
            tool=request.tool_name,
            args=request.args,
            token_id=token_data["id"]
        )

        result = await tool_registry.execute(
            request.tool_name,
            request.args,
            token_data
        )

        audit.log_event(
            "tool_execution_success",
            tool=request.tool_name,
            token_id=token_data["id"]
        )

        return ToolResponse(ok=True, result=result)

    except Exception as e:
        audit.log_event(
            "tool_execution_error",
            tool=request.tool_name,
            error=str(e),
            token_id=token_data["id"]
        )
        return ToolResponse(ok=False, error=str(e))