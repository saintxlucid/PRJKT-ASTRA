"""
Consent management API routes.

This module provides FastAPI routes for managing tool execution consent,
including requesting consent, checking status, and recording decisions.
"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from astra.security.policy_engine import get_policy_engine
from astra.telemetry.audit import AuditLogger
from astra.telemetry.tool_bus_metrics import ToolBusMetrics
from astra.security.tokenizer import create_execution_token

router = APIRouter(prefix="/v1/consent", tags=["consent"])
audit = AuditLogger(__name__)


class ConsentRequest(BaseModel):
    """Request for tool execution consent."""
    tool_name: str
    args: dict
    request_id: str


class ConsentResponse(BaseModel):
    """Response to a consent request."""
    ok: bool
    token: Optional[str] = None
    error: Optional[str] = None
    expires_in: Optional[int] = None


class ConsentStatus(BaseModel):
    """Status of a consent request."""
    request_id: str
    status: str  # "pending", "approved", "denied", "expired"
    decision_reason: Optional[str] = None


@router.post("/request", response_model=ConsentResponse)
async def request_consent(request: ConsentRequest, http_request: Request):
    """
    Request consent for tool execution.
    Creates a consent request and returns its ID for status checking.
    """
    start_time = time.time()
    policy = get_policy_engine()
    
    # Check if tool requires consent
    policy_result = policy.check_tool_execution(
        tool_name=request.tool_name,
        args=request.args
    )
    
    ToolBusMetrics.record_policy_check(
        tool_name=request.tool_name,
        allowed=policy_result.allowed
    )
    
    if not policy_result.requires_consent:
        # If no consent needed, generate token directly
        token = create_execution_token(
            tool=request.tool_name,
            args=request.args,
            request_id=request.request_id
        )
        return ConsentResponse(
            ok=True,
            token=token,
            expires_in=300  # 5 minutes
        )

    # Create consent request
    try:
        policy.create_consent_request(
            request_id=request.request_id,
            tool_name=request.tool_name,
            args=request.args,
            impact_assessment=policy_result.impact_assessment
        )
        
        audit.log_event(
            "consent_request_created",
            tool=request.tool_name,
            request_id=request.request_id
        )
        
        return ConsentResponse(ok=True)
        
    except Exception as e:
        audit.log_event(
            "consent_request_error",
            tool=request.tool_name,
            request_id=request.request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create consent request: {str(e)}"
        )


@router.get("/status/{request_id}", response_model=ConsentStatus)
async def get_consent_status(request_id: str):
    """Get the current status of a consent request."""
    policy = get_policy_engine()
    
    try:
        status = policy.get_consent_status(request_id)
        return ConsentStatus(
            request_id=request_id,
            status=status.status,
            decision_reason=status.reason
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Consent request not found: {request_id}"
        )


@router.post("/approve/{request_id}", response_model=ConsentResponse)
async def approve_consent(request_id: str, reason: Optional[str] = None):
    """
    Approve a consent request and generate execution token.
    Requires appropriate authorization (handled by middleware).
    """
    policy = get_policy_engine()
    
    try:
        request_data = policy.get_consent_request(request_id)
        if not request_data:
            raise HTTPException(
                status_code=404,
                detail=f"Consent request not found: {request_id}"
            )

        # Record approval
        policy.record_consent_decision(
            request_id=request_id,
            approved=True,
            reason=reason
        )

        # Generate execution token
        token = create_execution_token(
            tool=request_data.tool_name,
            args=request_data.args,
            request_id=request_id
        )

        audit.log_event(
            "consent_approved",
            request_id=request_id,
            tool=request_data.tool_name,
            reason=reason
        )

        return ConsentResponse(
            ok=True,
            token=token,
            expires_in=300  # 5 minutes
        )

    except Exception as e:
        audit.log_event(
            "consent_approval_error",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve consent: {str(e)}"
        )


@router.post("/deny/{request_id}", response_model=ConsentResponse)
async def deny_consent(request_id: str, reason: Optional[str] = None):
    """
    Deny a consent request.
    Requires appropriate authorization (handled by middleware).
    """
    policy = get_policy_engine()
    
    try:
        request_data = policy.get_consent_request(request_id)
        if not request_data:
            raise HTTPException(
                status_code=404,
                detail=f"Consent request not found: {request_id}"
            )

        # Record denial
        policy.record_consent_decision(
            request_id=request_id,
            approved=False,
            reason=reason
        )

        audit.log_event(
            "consent_denied",
            request_id=request_id,
            tool=request_data.tool_name,
            reason=reason
        )

        return ConsentResponse(
            ok=True,
            error="Consent denied: " + (reason or "No reason provided")
        )

    except Exception as e:
        audit.log_event(
            "consent_denial_error",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record consent denial: {str(e)}"
        )