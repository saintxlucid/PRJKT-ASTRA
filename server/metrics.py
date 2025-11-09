"""
Metrics collection for ASTRA server
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
import threading
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self._metrics = {
            "requests": {
                "total": 0,
                "success": 0,
                "errors": 0,
                "timeouts": 0
            },
            "latency": {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0
            },
            "memory": {
                "cache_hits": 0,
                "cache_misses": 0,
                "token_budget_breaches": 0
            },
            "tokens": {
                "total": 0,
                "per_request": 0.0
            },
            "circuits": {
                "memory_trips": 0,
                "inference_trips": 0
            }
        }
        self._latencies = []
        self._lock = threading.Lock()
        
    def track_request(self, duration: float, success: bool = True, timeout: bool = False) -> None:
        """Track a request's latency and outcome"""
        with self._lock:
            self._metrics["requests"]["total"] += 1
            if success:
                self._metrics["requests"]["success"] += 1
            else:
                self._metrics["requests"]["errors"] += 1
            if timeout:
                self._metrics["requests"]["timeouts"] += 1
                
            # Track latency
            self._latencies.append(duration)
            if len(self._latencies) > 1000:
                self._latencies = sorted(self._latencies)[-1000:]
            
            # Update percentiles
            if self._latencies:
                sorted_latencies = sorted(self._latencies)
                self._metrics["latency"]["p50"] = sorted_latencies[len(sorted_latencies) // 2]
                self._metrics["latency"]["p95"] = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                self._metrics["latency"]["p99"] = sorted_latencies[int(len(sorted_latencies) * 0.99)]
                
    def track_memory(self, cache_hit: bool, token_budget_breach: bool = False) -> None:
        """Track memory and cache operations"""
        with self._lock:
            if cache_hit:
                self._metrics["memory"]["cache_hits"] += 1
            else:
                self._metrics["memory"]["cache_misses"] += 1
            if token_budget_breach:
                self._metrics["memory"]["token_budget_breaches"] += 1
                
    def track_tokens(self, count: int) -> None:
        """Track token usage"""
        with self._lock:
            self._metrics["tokens"]["total"] += count
            self._metrics["tokens"]["per_request"] = (
                self._metrics["tokens"]["total"] / 
                max(1, self._metrics["requests"]["total"])
            )
            
    def track_circuit_trip(self, circuit: str) -> None:
        """Track circuit breaker trips"""
        with self._lock:
            if circuit == "memory":
                self._metrics["circuits"]["memory_trips"] += 1
            elif circuit == "inference":
                self._metrics["circuits"]["inference_trips"] += 1
                
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self._lock:
            return {
                **self._metrics,
                "cache_hit_rate": (
                    self._metrics["memory"]["cache_hits"] /
                    max(1, self._metrics["memory"]["cache_hits"] + self._metrics["memory"]["cache_misses"])
                ),
                "error_rate": (
                    self._metrics["requests"]["errors"] /
                    max(1, self._metrics["requests"]["total"])
                ),
                "availability": (
                    self._metrics["requests"]["success"] /
                    max(1, self._metrics["requests"]["total"])
                )
            }
            
    def check_slos(self) -> Dict[str, bool]:
        """Check if we're meeting our SLOs"""
        metrics = self.get_metrics()
        return {
            "availability": metrics["availability"] >= 0.995,  # 99.5%
            "error_rate": metrics["error_rate"] <= 0.02,      # <2%
            "p95_latency": metrics["latency"]["p95"] <= 2.5,  # ≤2.5s
            "cache_hit_rate": metrics["cache_hit_rate"] >= 0.65  # ≥65%
        }

# Global metrics collector
metrics = MetricsCollector()