"""
JWT session management for ASTRA authentication.
"""

import jwt
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import uuid
import structlog
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from astra.config import get_settings

logger = structlog.get_logger(__name__)
security = HTTPBearer()

class JWTManager:
    """Handles JWT token generation, validation and scope management."""

    def __init__(self):
        """Initialize JWT manager with settings."""
        self.settings = get_settings()
        self.secret = self.settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=30)
        self.refresh_token_expire = timedelta(days=7)

    def create_access_token(self, user_id: str, scopes: List[str]) -> str:
        """Create a new access token."""
        now = datetime.utcnow()
        payload = {
            "iat": now,
            "exp": now + self.access_token_expire,
            "sub": user_id,
            "scopes": scopes,
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a new refresh token."""
        now = datetime.utcnow()
        payload = {
            "iat": now,
            "exp": now + self.refresh_token_expire,
            "sub": user_id,
            "type": "refresh",
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token."""
        payload = self.verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        return self.create_access_token(
            user_id=payload["sub"],
            scopes=self.get_user_scopes(payload["sub"])
        )

    def get_user_scopes(self, user_id: str) -> List[str]:
        """Get allowed scopes for a user."""
        # TODO: Load from user database
        return ["basic", "memory:read", "memory:write"]

    def verify_scope(self, token: str, required_scope: str) -> bool:
        """Check if token has required scope."""
        payload = self.verify_token(token)
        scopes = payload.get("scopes", [])
        return required_scope in scopes

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict:
        """FastAPI dependency for getting current authenticated user."""
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication credentials"
            )
        
        token = credentials.credentials
        payload = self.verify_token(token)
        
        return {
            "user_id": payload["sub"],
            "scopes": payload.get("scopes", [])
        }

# Global JWT manager instance
jwt_manager = JWTManager()