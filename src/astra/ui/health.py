"""
ASTRA Health Status Banner
Created: October 22, 2025

Provides real-time health status monitoring for API and WebSocket connections.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict
import structlog
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

logger = structlog.get_logger()

class HealthStatus(Enum):
    """Health status indicators"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class HealthMetrics:
    """Health check metrics"""
    def __init__(self):
        self.last_check = datetime.now()
        self.status = HealthStatus.UNKNOWN
        self.latency_ms: Optional[float] = None
        self.error_count = 0
        self.error_window = timedelta(minutes=5)
        self.last_error: Optional[str] = None

class HealthBanner(QFrame):
    """
    Banner showing API and WebSocket health status
    """
    
    # Signals for status updates
    status_changed = pyqtSignal(str, HealthStatus)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        check_interval: int = 10000  # 10 seconds
    ):
        super().__init__(parent)
        
        self.api_health = HealthMetrics()
        self.ws_health = HealthMetrics()
        self.check_interval = check_interval
        
        self.setupUi()
        self.startMonitoring()
        
    def setupUi(self):
        """Setup banner UI"""
        self.setFrameStyle(
            QFrame.Shape.Box | QFrame.Shadow.Sunken
        )
        
        # Colors for status
        self.status_colors = {
            HealthStatus.HEALTHY: "#4CAF50",
            HealthStatus.DEGRADED: "#FFC107", 
            HealthStatus.UNHEALTHY: "#F44336",
            HealthStatus.UNKNOWN: "#9E9E9E"
        }
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        
        # API Status
        self.api_label = QLabel("API:")
        layout.addWidget(self.api_label)
        
        self.api_status = QLabel()
        self.api_status.setStyleSheet(
            f"color: {self.status_colors[HealthStatus.UNKNOWN]}"
        )
        layout.addWidget(self.api_status)
        
        layout.addSpacing(20)
        
        # WebSocket Status
        self.ws_label = QLabel("WebSocket:")
        layout.addWidget(self.ws_label)
        
        self.ws_status = QLabel()
        self.ws_status.setStyleSheet(
            f"color: {self.status_colors[HealthStatus.UNKNOWN]}"
        )
        layout.addWidget(self.ws_status)
        
        # Stretch to push everything left
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Set initial status
        self.updateApiStatus(self.api_health)
        self.updateWsStatus(self.ws_health)
        
    def startMonitoring(self):
        """Start health check timer"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkHealth)
        self.timer.start(self.check_interval)
        
        # Do initial check
        self.checkHealth()
        
    def checkHealth(self):
        """Perform health checks"""
        asyncio.create_task(self._check_api_health())
        asyncio.create_task(self._check_ws_health())
        
    async def _check_api_health(self):
        """Check API health"""
        try:
            # TODO: Implement actual API health check
            # For now, simulate health check
            await asyncio.sleep(0.1)
            
            self.api_health.last_check = datetime.now()
            self.api_health.latency_ms = 50
            self.api_health.status = HealthStatus.HEALTHY
            
            self.updateApiStatus(self.api_health)
            
        except Exception as e:
            logger.error("API health check failed", error=str(e))
            self._record_error("api", str(e))
            
    async def _check_ws_health(self):
        """Check WebSocket health"""
        try:
            # TODO: Implement actual WebSocket health check
            # For now, simulate health check
            await asyncio.sleep(0.1)
            
            self.ws_health.last_check = datetime.now()
            self.ws_health.latency_ms = 20
            self.ws_health.status = HealthStatus.HEALTHY
            
            self.updateWsStatus(self.ws_health)
            
        except Exception as e:
            logger.error("WebSocket health check failed", error=str(e))
            self._record_error("ws", str(e))
            
    def _record_error(self, service: str, error: str):
        """Record an error for a service"""
        metrics = (
            self.api_health if service == "api"
            else self.ws_health
        )
        
        now = datetime.now()
        cutoff = now - metrics.error_window
        
        # Reset error count if outside window
        if metrics.last_check < cutoff:
            metrics.error_count = 0
            
        metrics.error_count += 1
        metrics.last_error = error
        metrics.last_check = now
        
        # Update status based on error count
        if metrics.error_count >= 5:
            metrics.status = HealthStatus.UNHEALTHY
        elif metrics.error_count >= 2:
            metrics.status = HealthStatus.DEGRADED
        
        # Update UI
        if service == "api":
            self.updateApiStatus(metrics)
        else:
            self.updateWsStatus(metrics)
            
    def updateApiStatus(self, metrics: HealthMetrics):
        """Update API status display"""
        status_text = f"{metrics.status.value.title()}"
        if metrics.latency_ms is not None:
            status_text += f" ({metrics.latency_ms:.0f}ms)"
            
        self.api_status.setText(status_text)
        self.api_status.setStyleSheet(
            f"color: {self.status_colors[metrics.status]}"
        )
        
        # Emit signal
        self.status_changed.emit("api", metrics.status)
        
    def updateWsStatus(self, metrics: HealthMetrics):
        """Update WebSocket status display"""
        status_text = f"{metrics.status.value.title()}"
        if metrics.latency_ms is not None:
            status_text += f" ({metrics.latency_ms:.0f}ms)"
            
        self.ws_status.setText(status_text)
        self.ws_status.setStyleSheet(
            f"color: {self.status_colors[metrics.status]}"
        )
        
        # Emit signal
        self.status_changed.emit("ws", metrics.status)
        
    def getTooltip(self, metrics: HealthMetrics) -> str:
        """Get tooltip text for status"""
        lines = [
            f"Status: {metrics.status.value.title()}",
            f"Last Check: {metrics.last_check.strftime('%H:%M:%S')}"
        ]
        
        if metrics.latency_ms is not None:
            lines.append(f"Latency: {metrics.latency_ms:.0f}ms")
            
        if metrics.error_count > 0:
            lines.append(f"Recent Errors: {metrics.error_count}")
            
        if metrics.last_error:
            lines.append(f"Last Error: {metrics.last_error}")
            
        return "\n".join(lines)