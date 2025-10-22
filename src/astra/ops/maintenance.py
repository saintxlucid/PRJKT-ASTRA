"""
System maintenance and auto-tuning utilities.
"""
import time
import json
import statistics
from pathlib import Path
import structlog
from typing import Dict, Any, Optional

from astra.core.cache import CACHE
from astra.telemetry.metrics import GAUGES, set_gauge

logger = structlog.get_logger()

class SystemStats:
    """Collect and analyze system statistics."""
    
    def __init__(self, log_path: str = "logs/events.jsonl"):
        self.log_path = Path(log_path)
        self.reset()
    
    def reset(self):
        """Reset collected statistics."""
        self.latencies = []
        self.cache_lookups = 0
        self.cache_hits = 0
        self.errors = 0
        self.last_processed = 0
    
    def analyze_logs(self, window_s: float = 300) -> Dict[str, Any]:
        """
        Analyze logs within time window.
        
        Args:
            window_s: Analysis window in seconds
            
        Returns:
            Statistics dictionary
        """
        cutoff = time.time() - window_s
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                # Skip to last processed position
                if self.last_processed:
                    f.seek(self.last_processed)
                
                for line in f:
                    try:
                        record = json.loads(line)
                        
                        # Skip old records
                        ts = record.get('timestamp', 0)
                        if ts < cutoff:
                            continue
                        
                        # Track metrics
                        if record.get('evt') == 'orc.action':
                            self.latencies.append(
                                record.get('latency_ms', 0)
                            )
                        elif record.get('evt') == 'cache.lookup':
                            self.cache_lookups += 1
                            self.cache_hits += int(record.get('hit', 0))
                        elif record.get('level') == 'error':
                            self.errors += 1
                            
                    except json.JSONDecodeError:
                        continue
                        
                # Remember position
                self.last_processed = f.tell()
                
        except FileNotFoundError:
            logger.warning("log_file_not_found",
                         path=str(self.log_path))
        
        # Calculate statistics
        stats = {
            'p50_latency': self._percentile(self.latencies, 0.5),
            'p95_latency': self._percentile(self.latencies, 0.95),
            'p99_latency': self._percentile(self.latencies, 0.99),
            'cache_hit_rate': self.cache_hits / max(1, self.cache_lookups),
            'error_rate': self.errors / max(1, len(self.latencies)),
            'sample_size': len(self.latencies)
        }
        
        # Update gauges
        for k, v in stats.items():
            set_gauge(f"system_{k}", float(v))
        
        return stats
    
    @staticmethod
    def _percentile(values: list, pct: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        return statistics.quantiles(sorted(values), n=int(1/pct))[-1]


def maintenance_cycle():
    """Run system maintenance tasks."""
    logger.info("maintenance_cycle_started")
    
    # Clear memory cache
    CACHE.clear_memory()
    
    # Vacuum disk cache
    CACHE.vacuum_disk()
    
    # Log cache statistics
    stats = CACHE.stats
    logger.info("cache_stats",
                memory_hit_rate=stats['memory_hit_rate'],
                disk_hit_rate=stats['disk_hit_rate'])
    
    # Update metrics
    for k, v in stats.items():
        set_gauge(f"cache_{k}", float(v))


class AutoTuner:
    """
    Auto-tuning system for performance optimization.
    """
    
    def __init__(
        self,
        target_p95_ms: float = 100.0,
        target_cache_rate: float = 0.7,
        check_interval_s: float = 60.0
    ):
        """
        Initialize auto-tuner.
        
        Args:
            target_p95_ms: Target P95 latency in milliseconds
            target_cache_rate: Target cache hit rate
            check_interval_s: Check interval in seconds
        """
        self.target_p95_ms = target_p95_ms
        self.target_cache_rate = target_cache_rate
        self.check_interval_s = check_interval_s
        self.stats = SystemStats()
        
        logger.info("auto_tuner_initialized",
                   target_p95_ms=target_p95_ms,
                   target_cache_rate=target_cache_rate)
    
    def check(self) -> Dict[str, Any]:
        """
        Check system performance and adjust settings.
        
        Returns:
            Current statistics and adjustments made
        """
        # Get current stats
        stats = self.stats.analyze_logs(self.check_interval_s)
        
        adjustments = {}
        
        # Check latency
        if stats['p95_latency'] > self.target_p95_ms:
            # Reduce batch sizes
            new_size = CACHE.mem.capacity // 2
            if new_size >= 256:  # Don't go too small
                CACHE.mem.capacity = new_size
                adjustments['memory_capacity'] = new_size
        
        # Check cache hit rate
        if stats['cache_hit_rate'] < self.target_cache_rate:
            # Increase cache size
            new_size = CACHE.mem.capacity * 2
            if new_size <= 8192:  # Don't go too large
                CACHE.mem.capacity = new_size
                adjustments['memory_capacity'] = new_size
        
        if adjustments:
            logger.info("auto_tuner_adjustments",
                       **adjustments)
        
        return {
            'stats': stats,
            'adjustments': adjustments
        }