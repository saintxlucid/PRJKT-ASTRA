"""
JWT-based session management for ASTRA multi-user support.
"""
import time
from typing import Dict, Optional
from dataclasses import dataclass
import jwt
from astra.core.config import get_config

# Constants for JWT configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = 24 * 60 * 60  # 24 hours in seconds

@dataclass
class UserSession:
    """Represents an authenticated user session."""
    user_id: str
    scopes: list[str]
    expires_at: int
    session_id: str

class SessionManager:
    """Manages JWT-based user sessions."""
    
    def __init__(self):
        """Initialize the session manager."""
        config = get_config()
        self.secret_key = config.get("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be configured")
        self._active_sessions: Dict[str, UserSession] = {}

    def create_session(self, user_id: str, scopes: list[str]) -> UserSession:
        """Create a new user session with specified scopes.
        
        Args:
            user_id: Unique identifier for the user
            scopes: List of RBAC scope strings granted to this session
            
        Returns:
            UserSession object with JWT token and metadata
        """
        session_id = f"sess_{int(time.time())}_{user_id}"
        expires_at = int(time.time() + JWT_EXPIRY)
        
        session = UserSession(
            user_id=user_id,
            scopes=scopes,
            expires_at=expires_at,
            session_id=session_id
        )
        
        self._active_sessions[session_id] = session
        return session
    
    def encode_jwt(self, session: UserSession) -> str:
        """Generate a JWT token for the session."""
        payload = {
            "sub": session.user_id,
            "scopes": session.scopes,
            "exp": session.expires_at,
            "jti": session.session_id
        }
        return jwt.encode(payload, self.secret_key, algorithm=JWT_ALGORITHM)
    
    def validate_token(self, token: str) -> Optional[UserSession]:
        """Validate a JWT token and return the associated session.
        
        Args:
            token: JWT token string
            
        Returns:
            UserSession if valid, None if invalid/expired
            
        Raises:
            jwt.InvalidTokenError: If token is malformed/invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[JWT_ALGORITHM]
            )
            
            session_id = payload.get("jti")
            if not session_id or session_id not in self._active_sessions:
                return None
                
            session = self._active_sessions[session_id]
            if time.time() > session.expires_at:
                del self._active_sessions[session_id]
                return None
                
            return session
            
        except jwt.InvalidTokenError:
            return None
    
    def revoke_session(self, session_id: str) -> None:
        """Revoke/invalidate a specific session."""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            
    def cleanup_expired(self) -> None:
        """Remove expired sessions from memory."""
        now = time.time()
        expired = [
            sid for sid, sess in self._active_sessions.items() 
            if now > sess.expires_at
        ]
        for sid in expired:
            del self._active_sessions[sid]