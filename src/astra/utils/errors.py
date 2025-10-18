"""
Custom exception classes for ASTRA.

This module defines the exception hierarchy for the application,
providing structured error handling across all components.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AstraError(Exception):
    """
    Base exception for all ASTRA errors.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ConfigurationError(AstraError):
    """Raised when there's a configuration problem"""

    pass


class ValidationError(AstraError):
    """Raised when data validation fails"""

    pass


class LLMError(AstraError):
    """Base exception for LLM provider errors"""

    pass


class LLMConnectionError(LLMError):
    """Raised when unable to connect to LLM service"""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out"""

    pass


class LLMResponseError(LLMError):
    """Raised when LLM returns an invalid or error response"""

    pass


class MemoryError(AstraError):
    """Base exception for memory/vector store errors"""

    pass


class MemoryConnectionError(MemoryError):
    """Raised when unable to connect to vector store"""

    pass


class MemoryQueryError(MemoryError):
    """Raised when a memory query fails"""

    pass


class DatabaseError(AstraError):
    """Base exception for database errors"""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when unable to connect to database"""

    pass


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails"""

    pass


class NotFoundError(AstraError):
    """Raised when a requested resource is not found"""

    pass


class AuthenticationError(AstraError):
    """Raised when authentication fails"""

    pass


class AuthorizationError(AstraError):
    """Raised when user lacks permission for an action"""

    pass


class RateLimitError(AstraError):
    """Raised when rate limit is exceeded"""

    pass
