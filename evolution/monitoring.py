"""Monitoring and observability for ASTRA evolution system."""

import time
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from prometheus_client import (
    Counter, Gauge, Histogram,
    start_http_server
)

# Metrics
model_operations = Counter(
    'astra_model_operations_total',
    'Total number of model operations',
    ['operation_type', 'status']
)

model_operation_duration = Histogram(
    'astra_model_operation_duration_seconds',
    'Duration of model operations',
    ['operation_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

memory_size = Gauge(
    'astra_memory_entries_total',
    'Total number of memory entries'
)

memory_coherence = Gauge(
    'astra_memory_coherence_score',
    'Memory coherence score'
)

security_events = Counter(
    'astra_security_events_total',
    'Security-related events',
    ['event_type', 'level']
)

model_size = Gauge(
    'astra_model_size_bytes',
    'Size of models in bytes',
    ['model_type']
)

@dataclass
class MetricContext:
    """Context for tracking metrics."""
    start_time: float
    operation_type: str
    labels: Dict[str, str]

class MonitoringManager:
    """Manager for system monitoring and metrics."""
    
    def __init__(
        self,
        port: int = 9090,
        log_path: Optional[Path] = None
    ):
        """Initialize monitoring manager.
        
        Args:
            port: Prometheus metrics port
            log_path: Path for logs
        """
        # Start Prometheus HTTP server
        start_http_server(port)
        
        # Setup logging
        self.logger = logging.getLogger("astra.monitoring")
        if log_path:
            handler = logging.FileHandler(log_path / "monitoring.log")
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            self.logger.addHandler(handler)
            
    def track_operation(
        self,
        operation_type: str,
        **labels
    ) -> MetricContext:
        """Create tracking context for operation.
        
        Args:
            operation_type: Type of operation
            **labels: Additional labels
            
        Returns:
            Metric context
        """
        return MetricContext(
            start_time=time.time(),
            operation_type=operation_type,
            labels=labels
        )
        
    def complete_operation(
        self,
        context: MetricContext,
        status: str = "success"
    ):
        """Complete operation tracking.
        
        Args:
            context: Metric context
            status: Operation status
        """
        duration = time.time() - context.start_time
        
        # Record metrics
        model_operations.labels(
            operation_type=context.operation_type,
            status=status
        ).inc()
        
        model_operation_duration.labels(
            operation_type=context.operation_type
        ).observe(duration)
        
        # Log completion
        self.logger.info(
            f"Operation completed - type:{context.operation_type} "
            f"status:{status} duration:{duration:.2f}s"
        )
        
    def track_memory_stats(
        self,
        total_entries: int,
        coherence_score: float
    ):
        """Track memory statistics.
        
        Args:
            total_entries: Number of memory entries
            coherence_score: Memory coherence score
        """
        memory_size.set(total_entries)
        memory_coherence.set(coherence_score)
        
    def track_security_event(
        self,
        event_type: str,
        level: str
    ):
        """Track security event.
        
        Args:
            event_type: Type of security event
            level: Security level
        """
        security_events.labels(
            event_type=event_type,
            level=level
        ).inc()
        
        self.logger.info(
            f"Security event - type:{event_type} level:{level}"
        )
        
    def track_model_size(
        self,
        model_path: Path,
        model_type: str
    ):
        """Track model file size.
        
        Args:
            model_path: Path to model file
            model_type: Type of model
        """
        size = model_path.stat().st_size
        model_size.labels(model_type=model_type).set(size)
        
        self.logger.debug(
            f"Model size - type:{model_type} size:{size} bytes"
        )
        
    def export_metrics(
        self,
        path: Path
    ):
        """Export current metrics to file.
        
        Args:
            path: Export file path
        """
        from prometheus_client import write_to_textfile
        write_to_textfile(str(path), registry)