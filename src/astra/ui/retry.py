"""
ASTRA Retry and Toast Manager
Created: October 22, 2025

Provides retry mechanism for operations and toast notifications for user feedback.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps
import structlog
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve

logger = structlog.get_logger()

# Type for function return value
T = TypeVar("T")

class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        jitter: float = 0.1
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

def with_retry(
    error_types: tuple[type[Exception], ...] = (Exception,),
    notify: bool = True,
    config: Optional[RetryConfig] = None
):
    """
    Decorator to add retry behavior to functions
    
    Args:
        error_types: Tuple of exception types to retry on
        notify: Whether to show toast notifications
        config: Retry configuration
    """
    config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                last_error = None
                
                for attempt in range(config.max_attempts):
                    try:
                        result = await func(*args, **kwargs)
                        if notify and attempt > 0:
                            # Show success toast after retry
                            ToastManager.show_toast(
                                "Operation Succeeded",
                                "Operation completed successfully after retry",
                                "success"
                            )
                        return result
                        
                    except error_types as e:
                        last_error = e
                        if attempt < config.max_attempts - 1:
                            # Calculate delay with exponential backoff
                            delay = min(
                                config.base_delay * (2 ** attempt),
                                config.max_delay
                            )
                            # Add jitter
                            delay *= (1 + random.uniform(
                                -config.jitter,
                                config.jitter
                            ))
                            
                            if notify:
                                ToastManager.show_toast(
                                    "Operation Failed",
                                    f"Retrying in {delay:.1f}s... "
                                    f"({attempt + 1}/{config.max_attempts})",
                                    "warning"
                                )
                                
                            await asyncio.sleep(delay)
                            
                # Max retries exceeded
                if notify:
                    ToastManager.show_toast(
                        "Operation Failed",
                        f"Max retries exceeded: {str(last_error)}",
                        "error"
                    )
                raise last_error
                
        else:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                last_error = None
                
                for attempt in range(config.max_attempts):
                    try:
                        result = func(*args, **kwargs)
                        if notify and attempt > 0:
                            ToastManager.show_toast(
                                "Operation Succeeded",
                                "Operation completed successfully after retry",
                                "success"
                            )
                        return result
                        
                    except error_types as e:
                        last_error = e
                        if attempt < config.max_attempts - 1:
                            delay = min(
                                config.base_delay * (2 ** attempt),
                                config.max_delay
                            )
                            delay *= (1 + random.uniform(
                                -config.jitter,
                                config.jitter
                            ))
                            
                            if notify:
                                ToastManager.show_toast(
                                    "Operation Failed",
                                    f"Retrying in {delay:.1f}s... "
                                    f"({attempt + 1}/{config.max_attempts})",
                                    "warning"
                                )
                                
                            time.sleep(delay)
                            
                if notify:
                    ToastManager.show_toast(
                        "Operation Failed",
                        f"Max retries exceeded: {str(last_error)}",
                        "error"
                    )
                raise last_error
                
        return wrapper
    return decorator

class Toast(QFrame):
    """
    Toast notification widget
    
    Displays a temporary message with optional type styling
    """
    
    COLORS = {
        "info": "#2196F3",
        "success": "#4CAF50", 
        "warning": "#FFC107",
        "error": "#F44336"
    }
    
    def __init__(
        self,
        title: str,
        message: str,
        toast_type: str = "info",
        parent: Optional[QWidget] = None,
        duration: int = 3000
    ):
        super().__init__(parent)
        
        self.duration = duration
        self.setupUi(title, message, toast_type)
        
    def setupUi(
        self,
        title: str,
        message: str,
        toast_type: str
    ):
        """Setup toast UI"""
        # Set frame style
        self.setFrameStyle(
            QFrame.Shape.Box | QFrame.Shadow.Raised
        )
        self.setLineWidth(1)
        
        # Set background color
        color = self.COLORS.get(toast_type, self.COLORS["info"])
        self.setStyleSheet(f"""
            Toast {{
                background-color: {color};
                color: white;
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        
        # Layout
        layout = QHBoxLayout()
        
        # Title and message
        text = QLabel(f"<b>{title}</b><br>{message}")
        text.setWordWrap(True)
        layout.addWidget(text)
        
        self.setLayout(layout)
        
        # Size
        self.adjustSize()
        self.setFixedWidth(300)
        
        # Start hide timer
        QTimer.singleShot(
            self.duration,
            self.animate_out
        )
        
    def animate_out(self):
        """Animate toast hiding"""
        anim = QPropertyAnimation(self, b"pos")
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.setDuration(500)
        
        start = self.pos()
        end = QPoint(
            start.x() + self.width(),
            start.y()
        )
        
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.finished.connect(self.deleteLater)
        anim.start()

class ToastManager:
    """
    Manages creation and positioning of toast notifications
    """
    _toasts: list[Toast] = []
    _margin = 20
    _spacing = 10
    _parent: Optional[QWidget] = None
    
    @classmethod
    def init(cls, parent: QWidget):
        """Initialize with parent widget"""
        cls._parent = parent
        
    @classmethod
    def show_toast(
        cls,
        title: str,
        message: str,
        toast_type: str = "info",
        duration: int = 3000
    ) -> None:
        """Show a new toast notification"""
        if not cls._parent:
            logger.warning(
                "Toast manager not initialized with parent widget"
            )
            return
            
        # Create toast
        toast = Toast(
            title,
            message,
            toast_type,
            cls._parent,
            duration
        )
        
        # Position toast
        margin = cls._margin
        spacing = cls._spacing
        width = toast.width()
        height = toast.height()
        
        parent_rect = cls._parent.rect()
        
        # Position in bottom right
        x = parent_rect.width() - width - margin
        y = parent_rect.height() - height - margin
        
        # Adjust for existing toasts
        for existing in cls._toasts:
            if not existing.isVisible():
                continue
            y -= (existing.height() + spacing)
            
        toast.move(x, y)
        toast.show()
        
        # Track toast
        cls._toasts.append(toast)
        
        # Clean up hidden toasts
        cls._toasts = [
            t for t in cls._toasts
            if t.isVisible()
        ]