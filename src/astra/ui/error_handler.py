"""
ASTRA Global Error Handler
Created: October 22, 2025

Provides centralized error handling for the ASTRA desktop UI,
including error logging, user notifications, and crash recovery.
"""
from __future__ import annotations

import sys
import os
import traceback
import json
import logging
import inspect
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Dict, Optional, Type, List, cast

try:
    from PyQt6.QtWidgets import QMessageBox, QApplication
    from PyQt6.QtCore import QObject, pyqtSignal
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    # Stub classes for non-GUI mode
    class QObject:
        pass
    class pyqtSignal:
        def __init__(self, *args):
            pass
        def emit(self, *args):
            pass
            
import structlog

logger = structlog.get_logger()

class ServerExitStatus:
    """Server exit status codes and info"""
    SUCCESS = 0
    ERROR = 1
    CRASH = 2
    
    DESCRIPTIONS = {
        SUCCESS: "Clean shutdown",
        ERROR: "Error during operation",
        CRASH: "Unexpected crash"
    }
    
class ErrorContext:
    """Capture rich error context"""
    def __init__(self, error: Exception, **context: Any):
        self.error = error
        self.context = context
        self.time = datetime.now()
        self.traceback = traceback.extract_tb(error.__traceback__) if error.__traceback__ else None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to structured dict"""
        context = {
            "error": {
                "type": self.error.__class__.__name__,
                "message": str(self.error),
                "module": self.error.__class__.__module__,
            },
            "time": self.time.isoformat(),
            "context": self.context
        }
        
        if self.traceback:
            context["traceback"] = [{
                "filename": frame.filename,
                "lineno": frame.lineno,
                "name": frame.name,
                "line": frame.line
            } for frame in self.traceback]
            
        return context

class BaseErrorHandler:
    """Base error handler with no GUI dependencies"""
    
    def __init__(
        self,
        crash_dir: Optional[str] = None,
        max_crash_logs: int = 50,
        capture_locals: bool = True
    ):
        # Configure crash logging
        self.crash_dir = Path(crash_dir or "crashes")
        self.crash_dir.mkdir(exist_ok=True)
        self.max_crash_logs = max_crash_logs
        self.capture_locals = capture_locals
        
        # Error tracking
        self.last_error: Optional[ErrorContext] = None
        self.error_count: Dict[str, int] = {}
        
        # Install global exception handler
        sys.excepthook = self.handle_exception
        
    def on_error(self, title: str, message: str) -> None:
        """Hook for error notification"""
        logger.error("error_occurred", title=title, message=message)
        
    def on_crash(self, error: str, traceback: str) -> None:
        """Hook for crash notification"""
        logger.critical("crash_detected", error=error, traceback=traceback)
        
    def on_server_exit(self, status: int, description: str) -> None:
        """Hook for server exit notification"""
        level = "info" if status == ServerExitStatus.SUCCESS else "error"
        getattr(logger, level)("server_exit", status=status, description=description)


class ErrorHandler(QObject if GUI_AVAILABLE else BaseErrorHandler):
    """Error handler with optional GUI support"""
    
    # Signals for UI updates (only used in GUI mode)
    error_occurred = pyqtSignal(str, str) if GUI_AVAILABLE else None
    crash_detected = pyqtSignal(str, str) if GUI_AVAILABLE else None
    server_exit = pyqtSignal(int, str) if GUI_AVAILABLE else None
    
    def __init__(
        self,
        crash_dir: Optional[str] = None,
        max_crash_logs: int = 50,
        capture_locals: bool = True
    ):
        super().__init__(crash_dir, max_crash_logs, capture_locals)
        
        # Initialize error tracking
        self.error_stats: Dict[str, Any] = {
            "counts": {},  # Error type counts
            "last_occurrences": {},  # Last time each error occurred
            "sequences": []  # Recent error sequences for pattern detection
        }
        
        # Server exit tracking
        self.exit_status = ServerExitStatus.SUCCESS
        self.exit_info: Dict[str, Any] = {}
        
    def handle_exception(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_tb: Any
    ) -> None:
        """Handle uncaught exceptions with full context"""
        # Get formatted traceback
        tb_lines = traceback.format_exception(
            exc_type, exc_value, exc_tb
        )
        tb_text = "".join(tb_lines)
        
        # Capture stack frames
        frames = []
        if exc_tb:
            while exc_tb:
                frame_info = inspect.getframeinfo(exc_tb.tb_frame)
                
                # Get local variables if enabled
                locals_dict = {}
                if self.capture_locals:
                    try:
                        locals_dict = {
                            k: repr(v) for k, v in exc_tb.tb_frame.f_locals.items()
                            if not k.startswith('_')
                        }
                    except Exception:
                        pass
                        
                frames.append({
                    "filename": frame_info.filename,
                    "function": frame_info.function,
                    "lineno": frame_info.lineno,
                    "code_context": frame_info.code_context,
                    "locals": locals_dict
                })
                exc_tb = exc_tb.tb_next
                
        # Create rich error context
        error_context = ErrorContext(
            cast(Exception, exc_value),
            frames=frames,
            error_type=exc_type.__name__
        )
        
        # Update error stats
        self._update_error_stats(error_context)
        
        # Log with full context
        logger.error(
            "uncaught_exception",
            error_type=exc_type.__name__,
            error=str(exc_value),
            traceback=tb_text,
            error_context=error_context.to_dict()
        )
        
        # Save crash log
        self._save_crash_log(exc_type, exc_value, tb_text, error_context)
        
        # GUI notifications if available
        if GUI_AVAILABLE:
            title = "Unexpected Error"
            message = f"An error occurred: {str(exc_value)}"
            
            if self.error_occurred:
                self.error_occurred.emit(title, message)
            if self.crash_detected:
                self.crash_detected.emit(str(exc_value), tb_text)
                
            # Show error dialog if critical
            if self._is_critical_error(exc_type):
                self._show_critical_error(exc_value, tb_text)
            
    def _save_crash_log(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: str,
        error_context: Optional[ErrorContext] = None
    ) -> None:
        """Save crash details to log file with rich context"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = self.crash_dir / f"crash_{timestamp}.json"
        
        crash_data = {
            "timestamp": datetime.now().isoformat(),
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": traceback,
            "sys_info": {
                "platform": sys.platform,
                "python_version": sys.version,
                "argv": sys.argv,
                "pwd": str(Path.cwd()),
                "memory": self._get_memory_info()
            }
        }
        
        # Add rich error context if available
        if error_context:
            crash_data["error_context"] = error_context.to_dict()
            crash_data["error_stats"] = {
                "count": self.error_stats["counts"].get(exc_type.__name__, 0),
                "last_occurrence": self.error_stats["last_occurrences"].get(exc_type.__name__)
            }
        
        with open(crash_file, "w") as f:
            json.dump(crash_data, f, indent=2)
            
        # Cleanup old logs if needed
        self._cleanup_old_logs()
        
    def _cleanup_old_logs(self) -> None:
        """Remove old crash logs if maximum is exceeded"""
        crash_files = sorted(
            self.crash_dir.glob("crash_*.json"),
            key=lambda p: p.stat().st_mtime
        )
        
        if len(crash_files) > self.max_crash_logs:
            # Remove oldest files
            for f in crash_files[:-self.max_crash_logs]:
                try:
                    f.unlink()
                except Exception as e:
                    logger.warning(
                        "Failed to remove old crash log",
                        file=str(f),
                        error=str(e)
                    )
                    
    def _is_critical_error(
        self,
        exc_type: Type[BaseException]
    ) -> bool:
        """Check if error type requires immediate attention"""
        critical_types = (
            SystemError,
            MemoryError,
            OSError,
            IOError
        )
        return issubclass(exc_type, critical_types)
        
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get current memory usage information"""
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        
        return {
            "rss": mem.rss,  # Resident Set Size
            "vms": mem.vms,  # Virtual Memory Size
            "shared": getattr(mem, "shared", 0),  # Shared memory
            "percent": process.memory_percent()
        }
        
    def _update_error_stats(self, error_context: ErrorContext) -> None:
        """Update error statistics"""
        error_type = error_context.error.__class__.__name__
        
        # Update counts
        self.error_stats["counts"][error_type] = \
            self.error_stats["counts"].get(error_type, 0) + 1
            
        # Update last occurrence
        self.error_stats["last_occurrences"][error_type] = \
            error_context.time.isoformat()
            
        # Add to sequence (keep last 10)
        self.error_stats["sequences"].append({
            "type": error_type,
            "time": error_context.time.isoformat()
        })
        if len(self.error_stats["sequences"]) > 10:
            self.error_stats["sequences"].pop(0)
            
    def _show_critical_error(
        self,
        error: BaseException,
        traceback: str
    ) -> None:
        """Display critical error dialog"""
        if not GUI_AVAILABLE:
            return
            
        try:
            from PyQt6.QtWidgets import QMessageBox, QApplication
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Critical Error")
            msg.setText(str(error))
            msg.setInformativeText(
                "A critical error has occurred. The application may be unstable."
            )
            msg.setDetailedText(traceback)
            msg.addButton(
                "Copy Details",
                QMessageBox.ButtonRole.ActionRole
            )
            msg.addButton(
                QMessageBox.StandardButton.Close
            )
            
            result = msg.exec()
            
            # Copy to clipboard if requested
            if result == 0:  # First button (Copy Details)
                QApplication.clipboard().setText(traceback)
        except Exception as e:
            logger.error("Failed to show error dialog", error=str(e))