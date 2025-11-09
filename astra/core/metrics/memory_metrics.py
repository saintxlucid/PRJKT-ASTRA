"""
ASTRA Memory System Metrics
Tracks metrics related to memory operations and performance.
Created: October 21, 2025
"""
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from prometheus_client import Counter, Histogram, Gauge, Summary

logger = structlog.get_logger()

class MemoryMetrics:
    """Metrics for tracking memory system performance"""
    
    def __init__(self, registry=None):
        """Initialize memory metrics"""
        # Operation counters
        self.memory_operations = Counter(
            'astra_memory_operations_total',
            'Total number of memory operations',
            ['operation_type', 'memory_type', 'status'],
            registry=registry
        )
        
        # Operation latency
        self.operation_latency = Histogram(
            'astra_memory_operation_duration_seconds',
            'Duration of memory operations',
            ['operation_type', 'memory_type'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
            registry=registry
        )
        
        # Memory usage metrics
        self.memory_usage = Gauge(
            'astra_memory_usage_bytes',
            'Current memory usage by type',
            ['memory_type'],
            registry=registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'astra_memory_cache_hits_total',
            'Total number of cache hits',
            ['memory_type'],
            registry=registry
        )
        
        self.cache_misses = Counter(
            'astra_memory_cache_misses_total',
            'Total number of cache misses',
            ['memory_type'],
            registry=registry
        )
        
        # Query complexity metrics
        self.query_complexity = Summary(
            'astra_memory_query_complexity',
            'Complexity score of memory queries',
            ['memory_type', 'operation_type'],
            registry=registry
        )

    def record_operation(self, operation_type: str, memory_type: str, status: str = "success") -> None:
        """Record a memory operation"""
        self.memory_operations.labels(
            operation_type=operation_type,
            memory_type=memory_type,
            status=status
        ).inc()
        logger.debug("Memory operation recorded", 
                    operation_type=operation_type,
                    memory_type=memory_type,
                    status=status)

    def start_operation_timer(self, operation_type: str, memory_type: str) -> Histogram.Timer:
        """Start timing a memory operation"""
        return self.operation_latency.labels(
            operation_type=operation_type,
            memory_type=memory_type
        ).time()

    def update_memory_usage(self, memory_type: str, bytes_used: int) -> None:
        """Update memory usage for a specific type"""
        self.memory_usage.labels(memory_type=memory_type).set(bytes_used)
        logger.debug("Memory usage updated", 
                    memory_type=memory_type,
                    bytes_used=bytes_used)

    def record_cache_result(self, memory_type: str, hit: bool) -> None:
        """Record cache hit or miss"""
        if hit:
            self.cache_hits.labels(memory_type=memory_type).inc()
        else:
            self.cache_misses.labels(memory_type=memory_type).inc()

    def record_query_complexity(self, memory_type: str, operation_type: str, complexity_score: float) -> None:
        """Record complexity score of a memory query"""
        self.query_complexity.labels(
            memory_type=memory_type,
            operation_type=operation_type
        ).observe(complexity_score)
        
    def get_cache_hit_ratio(self, memory_type: str) -> float:
        """Calculate cache hit ratio for a memory type"""
        hits = self.cache_hits.labels(memory_type=memory_type)._value.get()
        misses = self.cache_misses.labels(memory_type=memory_type)._value.get()
        total = hits + misses
        return hits / total if total > 0 else 0.0

    def get_memory_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive memory statistics"""
        memory_types = ['semantic', 'episodic', 'procedural']
        stats = {}
        
        for memory_type in memory_types:
            stats[memory_type] = {
                'usage_bytes': self.memory_usage.labels(memory_type=memory_type)._value.get(),
                'cache_hit_ratio': self.get_cache_hit_ratio(memory_type),
                'operation_count': self.memory_operations.labels(
                    operation_type='total',
                    memory_type=memory_type,
                    status='success'
                )._value.get()
            }
        
        return stats