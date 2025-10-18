"""
Structured logging configuration for ASTRA.

This module sets up structured logging using structlog,
providing consistent, machine-readable logs across the application.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor

# Context variable for request ID (thread-safe, async-compatible)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    """Generate a new request ID"""
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get the current request ID from context"""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context"""
    _request_id.set(request_id)


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries"""
    event_dict["app"] = "astra"
    event_dict["app_version"] = "2.0.0"
    
    # Add request ID if available
    rid = get_request_id()
    if rid:
        event_dict["request_id"] = rid
    
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Drop the `color_message` key from the event dict.

    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it. This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = False,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output logs as JSON (for production)
    """
    # Set up shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        drop_color_message_key,
    ]

    if json_logs:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console output
        processors = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level.upper(),
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """
    Mixin class that provides a logger attribute.

    Usage:
        class MyClass(LoggerMixin):
            def some_method(self):
                self.logger.info("doing something")
    """

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)
