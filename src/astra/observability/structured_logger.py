"""
Structured logging system for ASTRA with correlation IDs and structured output.

Provides JSON-formatted logging with correlation tracking across async operations,
enabling full request tracing and observability.
"""

import json
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')

logger = structlog.get_logger(__name__)


class StructuredLogger:
    """Structured JSON logging with correlation ID tracking."""

    def __init__(
        self,
        log_path: str = "./logs/astra.jsonl",
        level: str = "INFO",
        service_name: str = "ASTRA",
    ):
        """
        Initialize structured logger.

        Args:
            log_path: Path to JSONL log file
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            service_name: Service identifier for logs
        """
        self.log_path = log_path
        self.service_name = service_name
        self.level = level
        self._ensure_log_file()
        self._configure_structlog()

    def _ensure_log_file(self) -> None:
        """Create log file and directory if needed."""
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def _configure_structlog(self) -> None:
        """Configure structlog for JSON output."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def get_correlation_id(self) -> str:
        """
        Get or create correlation ID for current context.

        Returns:
            Correlation ID string (UUID)
        """
        corr_id = correlation_id_var.get()
        if not corr_id:
            corr_id = str(uuid.uuid4())
            correlation_id_var.set(corr_id)
        return corr_id

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for current context."""
        correlation_id_var.set(correlation_id)

    def log_event(
        self,
        event: str,
        level: str = "INFO",
        **context: Any,
    ) -> str:
        """
        Log structured event with correlation ID.

        Args:
            event: Event name/description
            level: Log level
            **context: Additional context fields

        Returns:
            Correlation ID
        """
        corr_id = self.get_correlation_id()

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": self.service_name,
            "level": level,
            "event": event,
            "correlation_id": corr_id,
            "context": context,
        }

        # Write to JSONL file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Also log to structlog
        logger_func = getattr(logger, level.lower(), logger.info)
        logger_func(event, correlation_id=corr_id, **context)

        return corr_id

    def log_request(
        self,
        operation: str,
        agent_id: str,
        **metadata: Any,
    ) -> str:
        """
        Log request start with correlation ID.

        Args:
            operation: Operation name
            agent_id: Agent identifier
            **metadata: Additional metadata

        Returns:
            Correlation ID for request tracking
        """
        corr_id = self.get_correlation_id()

        self.log_event(
            f"request_start:{operation}",
            level="INFO",
            agent_id=agent_id,
            operation=operation,
            **metadata,
        )

        return corr_id

    def log_response(
        self,
        operation: str,
        agent_id: str,
        status: str,
        duration_ms: float,
        **metadata: Any,
    ) -> str:
        """
        Log response with duration and status.

        Args:
            operation: Operation name
            agent_id: Agent identifier
            status: Response status (success, error, etc.)
            duration_ms: Operation duration in milliseconds
            **metadata: Additional metadata

        Returns:
            Correlation ID
        """
        corr_id = self.get_correlation_id()

        self.log_event(
            f"request_complete:{operation}",
            level="INFO",
            agent_id=agent_id,
            operation=operation,
            status=status,
            duration_ms=duration_ms,
            **metadata,
        )

        return corr_id

    def log_error(
        self,
        operation: str,
        error: str,
        error_type: str = "UnknownError",
        **context: Any,
    ) -> str:
        """
        Log error event with traceback context.

        Args:
            operation: Operation where error occurred
            error: Error message
            error_type: Error class name
            **context: Additional error context

        Returns:
            Correlation ID
        """
        corr_id = self.get_correlation_id()

        self.log_event(
            f"error:{operation}",
            level="ERROR",
            error=error,
            error_type=error_type,
            **context,
        )

        return corr_id

    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        **tags: Any,
    ) -> str:
        """
        Log metric value with tags.

        Args:
            metric_name: Name of metric
            value: Metric value
            unit: Unit of measurement
            **tags: Additional tags for metric

        Returns:
            Correlation ID
        """
        corr_id = self.get_correlation_id()

        self.log_event(
            f"metric:{metric_name}",
            level="DEBUG",
            metric=metric_name,
            value=value,
            unit=unit,
            **tags,
        )

        return corr_id

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        threshold_ms: float = 100.0,
        **context: Any,
    ) -> str:
        """
        Log performance metric with threshold warning.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            threshold_ms: Performance threshold
            **context: Additional context

        Returns:
            Correlation ID
        """
        corr_id = self.get_correlation_id()

        level = "WARNING" if duration_ms > threshold_ms else "INFO"

        self.log_event(
            f"performance:{operation}",
            level=level,
            operation=operation,
            duration_ms=duration_ms,
            threshold_ms=threshold_ms,
            exceeded=duration_ms > threshold_ms,
            **context,
        )

        return corr_id

    def get_logs(self, limit: int = 100, filter_level: str | None = None) -> list[dict[str, Any]]:
        """
        Retrieve recent logs.

        Args:
            limit: Maximum logs to retrieve
            filter_level: Optional level filter (INFO, ERROR, etc.)

        Returns:
            List of log entries
        """
        entries = []
        try:
            with open(self.log_path) as f:
                for line in f.readlines()[-limit:]:
                    entry = json.loads(line)
                    if filter_level is None or entry.get('level') == filter_level:
                        entries.append(entry)
        except FileNotFoundError:
            pass

        return entries

    def get_correlation_logs(self, correlation_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all logs for correlation ID.

        Args:
            correlation_id: Correlation ID to filter by

        Returns:
            List of log entries for correlation
        """
        entries = []
        try:
            with open(self.log_path) as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('correlation_id') == correlation_id:
                        entries.append(entry)
        except FileNotFoundError:
            pass

        return entries

    def get_operation_logs(self, operation: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieve logs for specific operation.

        Args:
            operation: Operation name
            limit: Maximum logs to retrieve

        Returns:
            List of log entries for operation
        """
        entries = []
        try:
            with open(self.log_path) as f:
                for line in f.readlines()[-limit * 5:]:  # Check more lines
                    entry = json.loads(line)
                    if operation in entry.get('event', ''):
                        entries.append(entry)
        except FileNotFoundError:
            pass

        return entries[:limit]
