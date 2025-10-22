"""
ASTRA Desktop UI Application
Created: October 22, 2025

Main application entry point integrating all UI components.
"""
from __future__ import annotations

import os
import sys
import asyncio
from typing import Optional
import structlog
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QStatusBar
)
from PyQt6.QtCore import Qt

from .error_handler import ErrorHandler
from .retry import ToastManager
from .health import HealthBanner

logger = structlog.get_logger()

class MainWindow(QMainWindow):
    """ASTRA main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.setWindowTitle("ASTRA")
        self.resize(1400, 900)  # Default size
        
        # Apply environment size settings
        width = int(os.getenv("ASTRA_UI_WIDTH", "1400"))
        height = int(os.getenv("ASTRA_UI_HEIGHT", "900"))
        self.resize(width, height)
        
        if title := os.getenv("ASTRA_UI_TITLE"):
            self.setWindowTitle(title)
            
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        
        # Health banner at top
        self.health_banner = HealthBanner(self)
        layout.addWidget(self.health_banner)
        
        # Content area (to be filled by specific views)
        self.content = QWidget()
        layout.addWidget(self.content)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initialize managers
        self.setupErrorHandler()
        self.setupToastManager()
        
    def setupErrorHandler(self):
        """Initialize error handler"""
        self.error_handler = ErrorHandler(
            crash_dir="crashes"
        )
        
        # Connect error signals
        self.error_handler.error_occurred.connect(
            self.onErrorOccurred
        )
        self.error_handler.crash_detected.connect(
            self.onCrashDetected
        )
        
    def setupToastManager(self):
        """Initialize toast notification manager"""
        ToastManager.init(self)
        
    def onErrorOccurred(self, title: str, message: str):
        """Handle error notification"""
        # Show in status bar
        self.status_bar.showMessage(
            f"Error: {message}",
            5000  # 5 seconds
        )
        
    def onCrashDetected(self, error: str, traceback: str):
        """Handle crash notification"""
        logger.critical(
            "Application crash detected",
            error=error,
            traceback=traceback
        )
        # Status bar shows critical error
        self.status_bar.showMessage(
            "Critical Error Detected - Check Logs",
            0  # No timeout
        )

def main():
    """Application entry point"""
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(
            "Failed to start application",
            error=str(e),
            exc_info=True
        )
        sys.exit(1)

if __name__ == "__main__":
    main()