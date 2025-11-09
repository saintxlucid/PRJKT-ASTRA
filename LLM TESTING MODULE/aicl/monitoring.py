import time
import json
import threading
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Metric:
    """Base metric class"""
    name: str
    value: Any
    timestamp: float
    tags: Dict[str, str]

class MetricsCollector:
    """Collect and manage system metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(deque)
        self.max_metrics_per_type = 1000
        self._lock = threading.Lock()
    
    def record_metric(self, name: str, value: Any, tags: Optional[Dict[str, str]] = None):
        """
        Record a metric
        
        Args:
            name (str): Metric name
            value (Any): Metric value
            tags (dict): Optional tags for the metric
        """
        with self._lock:
            metric = Metric(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags or {}
            )
            
            self.metrics[name].append(metric)
            
            # Trim old metrics if we exceed the limit
            if len(self.metrics[name]) > self.max_metrics_per_type:
                self.metrics[name].popleft()
    
    def get_metrics(self, name: Optional[str] = None) -> List[Metric]:
        """
        Get metrics
        
        Args:
            name (str): Optional metric name to filter by
            
        Returns:
            list: List of metrics
        """
        with self._lock:
            if name:
                return list(self.metrics.get(name, []))
            else:
                all_metrics = []
                for metric_list in self.metrics.values():
                    all_metrics.extend(metric_list)
                return all_metrics
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics
        
        Returns:
            dict: Summary of metrics
        """
        with self._lock:
            summary = {}
            for name, metrics in self.metrics.items():
                if metrics:
                    # Get the latest metric value
                    latest = metrics[-1]
                    summary[name] = {
                        "latest_value": latest.value,
                        "latest_timestamp": latest.timestamp,
                        "count": len(metrics),
                        "tags": latest.tags
                    }
            return summary

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.checks = {}
    
    def register_health_check(self, name: str, check_func):
        """
        Register a health check function
        
        Args:
            name (str): Name of the health check
            check_func (callable): Function that returns (is_healthy, details)
        """
        self.checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all registered health checks
        
        Returns:
            dict: Health check results
        """
        results = {}
        for name, check_func in self.checks.items():
            try:
                is_healthy, details = check_func()
                results[name] = {
                    "healthy": is_healthy,
                    "details": details,
                    "timestamp": time.time()
                }
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "details": {"error": str(e)},
                    "timestamp": time.time()
                }
        return results
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health
        
        Returns:
            dict: System health status
        """
        health_checks = self.run_health_checks()
        all_healthy = all(check["healthy"] for check in health_checks.values())
        
        return {
            "overall_status": "healthy" if all_healthy else "unhealthy",
            "checks": health_checks,
            "timestamp": time.time()
        }

class EventLogger:
    """Structured event logging for observability"""
    
    def __init__(self):
        self.events = deque(maxlen=10000)
        self._lock = threading.Lock()
    
    def log_event(self, event_type: str, message: str, severity: str = "info", details: Optional[Dict] = None):
        """
        Log an event
        
        Args:
            event_type (str): Type of event
            message (str): Event message
            severity (str): Severity level (info, warning, error, critical)
            details (dict): Additional event details
        """
        event = {
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "details": details or {},
            "timestamp": time.time(),
            "iso_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        with self._lock:
            self.events.append(event)
    
    def get_events(self, event_type: Optional[str] = None, severity: Optional[str] = None) -> List[Dict]:
        """
        Get events with optional filtering
        
        Args:
            event_type (str): Optional event type to filter by
            severity (str): Optional severity to filter by
            
        Returns:
            list: List of events
        """
        with self._lock:
            filtered_events = list(self.events)
            
            if event_type:
                filtered_events = [e for e in filtered_events if e["event_type"] == event_type]
            
            if severity:
                filtered_events = [e for e in filtered_events if e["severity"] == severity]
            
            return filtered_events
    
    def get_recent_events(self, count: int = 100) -> List[Dict]:
        """
        Get the most recent events
        
        Args:
            count (int): Number of events to return
            
        Returns:
            list: Recent events
        """
        with self._lock:
            return list(self.events)[-count:]

class PerformanceMonitor:
    """Monitor system performance"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.operation_timings = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_operation_timing(self, operation_name: str, duration_ms: float, success: bool = True):
        """
        Record the timing of an operation
        
        Args:
            operation_name (str): Name of the operation
            duration_ms (float): Duration in milliseconds
            success (bool): Whether the operation was successful
        """
        with self._lock:
            self.operation_timings[operation_name].append({
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": time.time()
            })
            
            # Keep only the last 1000 timings per operation
            if len(self.operation_timings[operation_name]) > 1000:
                self.operation_timings[operation_name] = self.operation_timings[operation_name][-1000:]
        
        # Record as metrics
        self.metrics_collector.record_metric(
            f"operation.duration.{operation_name}",
            duration_ms,
            {"operation": operation_name, "success": str(success)}
        )
        
        self.metrics_collector.record_metric(
            f"operation.success.{operation_name}",
            1 if success else 0,
            {"operation": operation_name}
        )
    
    def get_performance_stats(self, operation_name: str) -> Dict[str, Any]:
        """
        Get performance statistics for an operation
        
        Args:
            operation_name (str): Name of the operation
            
        Returns:
            dict: Performance statistics
        """
        with self._lock:
            timings = self.operation_timings.get(operation_name, [])
            
            if not timings:
                return {}
            
            durations = [t["duration_ms"] for t in timings]
            success_count = sum(1 for t in timings if t["success"])
            
            return {
                "operation": operation_name,
                "total_count": len(timings),
                "success_count": success_count,
                "error_count": len(timings) - success_count,
                "success_rate": success_count / len(timings) if timings else 0,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "recent_timings": timings[-10:]  # Last 10 timings
            }
    
    def get_all_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance statistics for all operations
        
        Returns:
            dict: Performance statistics for all operations
        """
        with self._lock:
            return {
                op_name: self.get_performance_stats(op_name)
                for op_name in self.operation_timings.keys()
            }

class AICLObserver:
    """Main observer class that combines all monitoring features"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker(self.metrics_collector)
        self.event_logger = EventLogger()
        self.performance_monitor = PerformanceMonitor(self.metrics_collector)
    
    def record_message_processed(self, message_type: str, duration_ms: float, success: bool = True):
        """Record that a message was processed"""
        self.performance_monitor.record_operation_timing(
            f"message.{message_type}", duration_ms, success
        )
        
        self.event_logger.log_event(
            "message_processed",
            f"Processed {message_type} message",
            "info" if success else "error",
            {
                "message_type": message_type,
                "duration_ms": duration_ms,
                "success": success
            }
        )
    
    def record_connection_event(self, event_type: str, peer: str, success: bool = True):
        """Record a connection event"""
        self.event_logger.log_event(
            f"connection_{event_type}",
            f"Connection {event_type} with {peer}",
            "info" if success else "error",
            {
                "peer": peer,
                "success": success
            }
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get complete system status
        
        Returns:
            dict: Complete system status
        """
        return {
            "timestamp": time.time(),
            "health": self.health_checker.get_system_health(),
            "metrics_summary": self.metrics_collector.get_metrics_summary(),
            "performance": self.performance_monitor.get_all_performance_stats(),
            "recent_events": self.event_logger.get_recent_events(10)
        }