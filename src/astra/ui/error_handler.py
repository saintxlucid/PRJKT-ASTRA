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
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal
import structlog

logger = structlog.get_logger()

class ErrorHandler(QObject):
    """Global error handler for ASTRA desktop UI"""
    
    # Signals for UI updates
    error_occurred = pyqtSignal(str, str)  # title, message
    crash_detected = pyqtSignal(str, str)  # error, traceback
    
    def __init__(
        self,
        crash_dir: Optional[str] = None,
        max_crash_logs: int = 50
    ):
        super().__init__()
        
        # Configure crash logging
        self.crash_dir = Path(crash_dir or "crashes")
        self.crash_dir.mkdir(exist_ok=True)
        self.max_crash_logs = max_crash_logs
        
        # Install global exception handler
        sys.excepthook = self.handle_exception
        
    def handle_exception(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: traceback.TracebackType
    ) -> None:
        """Handle uncaught exceptions"""
        # Get formatted traceback
        tb_lines = traceback.format_exception(
            exc_type, exc_value, exc_traceback
        )
        tb_text = "".join(tb_lines)
        
        # Log the error
        logger.error(
            "Uncaught exception",
            error_type=exc_type.__name__,
            error=str(exc_value),
            traceback=tb_text
        )
        
        # Save crash log
        self._save_crash_log(exc_type, exc_value, tb_text)
        
        # Emit signals
        self.error_occurred.emit(
            "Unexpected Error",
            f"An error occurred: {str(exc_value)}"
        )
        self.crash_detected.emit(
            str(exc_value),
            tb_text
        )
        
        # Show error dialog if critical
        if self._is_critical_error(exc_type):
            self._show_critical_error(exc_value, tb_text)
            
    def _save_crash_log(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: str
    ) -> None:
        """Save crash details to log file"""
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
                "argv": sys.argv
            }
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
        
    def _show_critical_error(
        self,
        error: BaseException,
        traceback: str
    ) -> None:
        """Display critical error dialog"""
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
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(traceback)