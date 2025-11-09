"""
Phase 11: StructuredLogger - JSON-based Event Logging

Provides structured, async-first logging with JSON serialization and
context propagation for centralized log aggregation and correlation.
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable
from collections import deque
from contextvars import ContextVar
import traceback


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    def __lt__(self, other):
        """Allow severity comparison."""
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        return levels.index(self) < levels.index(other)


@dataclass
class LogContext:
    """Logging context with request/session/component tracking."""
    request_id: str                           # Unique request identifier
    user_id: Optional[str] = None             # Acting user
    session_id: Optional[str] = None          # Session identifier
    component: Optional[str] = None           # Source component
    module: Optional[str] = None              # Source module
    tags: Dict[str, str] = field(default_factory=dict)  # Custom tags
    parent_span_id: Optional[str] = None      # Distributed tracing


@dataclass
class LogEvent:
    """A structured log event with full context."""
    timestamp: datetime
    level: LogLevel
    message: str
    context: LogContext
    error: Optional[str] = None               # Error traceback
    metrics: Dict[str, Any] = field(default_factory=dict)  # Associated metrics
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'request_id': self.context.request_id,
            'user_id': self.context.user_id,
            'session_id': self.context.session_id,
            'component': self.context.component,
            'module': self.context.module,
            'tags': self.context.tags,
            'parent_span_id': self.context.parent_span_id,
            'error': self.error,
            'metrics': self.metrics,
            'metadata': self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class StructuredLogger:
    """JSON-based structured logger with async support and context propagation."""
    
    def __init__(self, app_name: str = "astra", version: str = "1.0.0", max_history: int = 10000):
        """Initialize logger.
        
        Args:
            app_name: Application name for logging
            version: Application version
            max_history: Maximum log events to keep in memory
        """
        self.app_name = app_name
        self.version = version
        self.max_history = max_history
        
        # Core state
        self._min_level = LogLevel.INFO
        self._log_history: deque = deque(maxlen=max_history)
        self._filters: List[Callable[[LogEvent], bool]] = []
        self._outputs: List[Callable[[LogEvent], Awaitable]] = []
        self._context_stack: ContextVar[Optional[LogContext]] = ContextVar('log_context', default=None)
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            'debug': 0,
            'info': 0,
            'warning': 0,
            'error': 0,
            'critical': 0,
            'filtered': 0,
            'components': {},
        }
    
    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self._min_level = level
    
    def add_filter(self, filter_func: Callable[[LogEvent], bool]) -> None:
        """Add filter function. Returns True to include log event."""
        self._filters.append(filter_func)
    
    def add_output(self, output_handler: Callable[[LogEvent], Awaitable]) -> None:
        """Add async output handler that receives log events."""
        self._outputs.append(output_handler)
    
    def create_context(
        self,
        request_id: str,
        component: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **tags
    ) -> LogContext:
        """Create a new log context."""
        return LogContext(
            request_id=request_id,
            component=component,
            user_id=user_id,
            session_id=session_id,
            tags=tags,
        )
    
    def push_context(self, context: LogContext) -> None:
        """Push context onto stack."""
        self._context_stack.set(context)
    
    def pop_context(self) -> Optional[LogContext]:
        """Pop context from stack."""
        context = self._context_stack.get()
        self._context_stack.set(None)
        return context
    
    async def _log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[LogContext] = None,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LogEvent:
        """Internal log implementation."""
        # Check level
        if level < self._min_level:
            async with self._lock:
                self._stats['filtered'] += 1
            return None
        
        # Use provided context or get from stack
        if context is None:
            context = self._context_stack.get()
        if context is None:
            context = LogContext(request_id='unknown')
        
        # Create log event
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            context=context,
            error=error,
            metrics=metrics or {},
            metadata=metadata or {},
        )
        
        # Check filters
        for filter_func in self._filters:
            if not filter_func(event):
                async with self._lock:
                    self._stats['filtered'] += 1
                return None
        
        # Update statistics
        async with self._lock:
            level_key = level.value.lower()
            self._stats[level_key] = self._stats.get(level_key, 0) + 1
            
            if context.component:
                if context.component not in self._stats['components']:
                    self._stats['components'][context.component] = 0
                self._stats['components'][context.component] += 1
            
            # Store in history
            self._log_history.append(event)
        
        # Call output handlers
        for handler in self._outputs:
            try:
                await handler(event)
            except Exception as e:
                # Silently fail to avoid recursive logging
                pass
        
        return event
    
    async def debug(
        self,
        message: str,
        context: Optional[LogContext] = None,
        **metadata
    ) -> LogEvent:
        """Log debug message."""
        return await self._log(LogLevel.DEBUG, message, context, metadata=metadata)
    
    async def info(
        self,
        message: str,
        context: Optional[LogContext] = None,
        **metadata
    ) -> LogEvent:
        """Log info message."""
        return await self._log(LogLevel.INFO, message, context, metadata=metadata)
    
    async def warning(
        self,
        message: str,
        context: Optional[LogContext] = None,
        **metadata
    ) -> LogEvent:
        """Log warning message."""
        return await self._log(LogLevel.WARNING, message, context, metadata=metadata)
    
    async def error(
        self,
        message: str,
        context: Optional[LogContext] = None,
        error: Optional[Exception] = None,
        **metadata
    ) -> LogEvent:
        """Log error message."""
        error_str = None
        if error:
            error_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        return await self._log(LogLevel.ERROR, message, context, error=error_str, metadata=metadata)
    
    async def critical(
        self,
        message: str,
        context: Optional[LogContext] = None,
        error: Optional[Exception] = None,
        **metadata
    ) -> LogEvent:
        """Log critical message."""
        error_str = None
        if error:
            error_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        return await self._log(LogLevel.CRITICAL, message, context, error=error_str, metadata=metadata)
    
    async def get_recent_logs(self, limit: int = 100) -> List[LogEvent]:
        """Get recent log events."""
        async with self._lock:
            return list(self._log_history)[-limit:]
    
    async def get_logs_by_context(
        self,
        request_id: Optional[str] = None,
        component: Optional[str] = None,
        user_id: Optional[str] = None,
        level: Optional[LogLevel] = None,
    ) -> List[LogEvent]:
        """Get logs matching context criteria."""
        async with self._lock:
            result = []
            for event in self._log_history:
                if request_id and event.context.request_id != request_id:
                    continue
                if component and event.context.component != component:
                    continue
                if user_id and event.context.user_id != user_id:
                    continue
                if level and event.level != level:
                    continue
                result.append(event)
            return result
    
    async def export_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Export logs as dictionaries."""
        async with self._lock:
            result = []
            for event in self._log_history:
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                result.append(event.to_dict())
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            'app_name': self.app_name,
            'version': self.version,
            'min_level': self._min_level.value,
            'total_events': len(self._log_history),
            'by_level': {
                'debug': self._stats['debug'],
                'info': self._stats['info'],
                'warning': self._stats['warning'],
                'error': self._stats['error'],
                'critical': self._stats['critical'],
            },
            'filtered': self._stats['filtered'],
            'by_component': dict(self._stats['components']),
            'output_handlers': len(self._outputs),
            'filters': len(self._filters),
        }


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """Get or create global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger()
    return _global_logger


def set_logger(logger: StructuredLogger) -> None:
    """Set global logger instance."""
    global _global_logger
    _global_logger = logger
