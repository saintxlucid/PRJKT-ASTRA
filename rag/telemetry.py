"""
Token budget telemetry and monitoring
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
import json
import logging
from datetime import datetime
import structlog

logger = structlog.get_logger()

@dataclass
class TokenUsage:
    """Token usage metrics for a request"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    timestamp: datetime

@dataclass
class BudgetMetrics:
    """Token budget allocation and usage metrics"""
    allocated: Dict[str, int]
    used: Dict[str, int]
    efficiency: float
    overages: Dict[str, int]
    duration_ms: int

class TokenBudgetMonitor:
    """Tracks and reports token budget metrics"""
    
    def __init__(
        self,
        log_metrics: bool = True,
        should_export: bool = True
    ):
        self.log_metrics = log_metrics
        self.should_export = should_export
        self._start_time = None
        self._usage_log = []
        
    def start_request(self):
        """Start tracking a new request"""
        self._start_time = time.time()
        
    def record_usage(
        self,
        component: str,
        allocated: int,
        used: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record token usage for a component"""
        if not self._start_time:
            raise RuntimeError("Must call start_request() first")
            
        duration = int((time.time() - self._start_time) * 1000)
        
        usage = {
            "component": component,
            "allocated": allocated,
            "used": used,
            "overage": max(0, used - allocated),
            "efficiency": used / allocated if allocated > 0 else 0,
            "duration_ms": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if metadata:
            usage.update(metadata)
            
        self._usage_log.append(usage)
        
        if self.log_metrics:
            logger.info(
                "token_budget_usage",
                **usage
            )
            
    def get_metrics(self) -> BudgetMetrics:
        """Get aggregated metrics for current request"""
        if not self._usage_log:
            return BudgetMetrics(
                allocated={},
                used={},
                efficiency=0,
                overages={},
                duration_ms=0
            )
            
        # Aggregate by component
        allocated = {}
        used = {}
        overages = {}
        
        for entry in self._usage_log:
            component = entry["component"]
            allocated[component] = entry["allocated"]
            used[component] = entry["used"]
            overages[component] = entry["overage"]
            
        # Calculate overall efficiency
        total_allocated = sum(allocated.values())
        total_used = sum(used.values())
        efficiency = total_used / total_allocated if total_allocated > 0 else 0
        
        # Get total duration
        duration = max(entry["duration_ms"] for entry in self._usage_log)
        
        return BudgetMetrics(
            allocated=allocated,
            used=used,
            efficiency=efficiency,
            overages=overages,
            duration_ms=duration
        )
        
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        if not self.export_metrics:
            return
            
        metrics = {
            "request_metrics": self.get_metrics().__dict__,
            "detailed_log": self._usage_log
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
            
    def reset(self):
        """Reset tracking for new request"""
        self._start_time = None
        self._usage_log = []

# Global monitor instance
token_monitor = TokenBudgetMonitor()