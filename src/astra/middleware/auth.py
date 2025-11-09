"""
ASTRA Authentication Middleware
================================

JWT/Token verification via Sigil Gate integration.
Protects sensitive API endpoints with bearer token authentication.

Usage:
    from src.astra.middleware.auth import verify_token
    
    @router.post("/v1/agent/task")
    async def create_task(req: dict, user=Depends(verify_token)):
        # user contains validated user_id/subject
        ...

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""
import os
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security scheme for bearer token authentication
security = HTTPBearer()

# Sigil Gate service URL
SIGIL_GATE_URL = os.getenv("SIGIL_GATE_URL", "http://localhost:7701")


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify bearer token via Sigil Gate service.
    
    Args:
        credentials: HTTP bearer token from Authorization header
        
    Returns:
        str: User ID / subject from validated token
        
    Raises:
        HTTPException: 401 if token is invalid or verification fails
        
    Example:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    token = credentials.credentials
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SIGIL_GATE_URL}/verify",
                json={"token": token},
                timeout=5.0
            )
            
            # Check if verification succeeded
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token verification failed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Parse verification response
            data = response.json()
            
            if not data.get("valid", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Return user identifier (subject)
            user_id = data.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject claim",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user_id
            
    except httpx.RequestError as e:
        # Sigil Gate unavailable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {str(e)}",
        ) from e


async def verify_token_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(
        security, auto_error=False
    )
) -> Optional[str]:
    """
    Optional token verification (allows anonymous access).
    
    Use for endpoints that work both authenticated and unauthenticated,
    but may provide enhanced features for authenticated users.
    
    Args:
        credentials: Optional HTTP bearer token
        
    Returns:
        Optional[str]: User ID if token provided and valid, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await verify_token(credentials)
    except HTTPException:
        return None


# API Key verification (alternative to JWT)
async def verify_api_key(
    api_key: str = Security(HTTPBearer())
) -> str:
    """
    Verify API key via Sigil Gate.
    
    Alternative to JWT tokens for service-to-service authentication
    or long-lived API keys.
    
    Args:
        api_key: API key from Authorization header
        
    Returns:
        str: Service/user identifier
        
    Raises:
        HTTPException: 401 if API key is invalid
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SIGIL_GATE_URL}/verify_api_key",
                json={"api_key": api_key.credentials},
                timeout=5.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )
            
            data = response.json()
            return data.get("service_id", "unknown")
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {str(e)}",
        ) from e
