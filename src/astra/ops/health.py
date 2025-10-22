"""
Health check system for component status monitoring.
"""
import os
import time
import psutil
import structlog
from pathlib import Path
from typing import Dict, Any, Optional

from astra.core.cache import CACHE
from astra.telemetry.metrics import GAUGES

logger = structlog.get_logger()

def check_disk_space(path: Path, min_gb: float = 1.0) -> bool:
    """Check if path has minimum required disk space."""
    try:
        usage = psutil.disk_usage(str(path))
        free_gb = usage.free / (1024 * 1024 * 1024)
        return free_gb >= min_gb
    except Exception as e:
        logger.error("disk_space_check_failed",
                    path=str(path),
                    error=str(e))
        return False

def check_memory() -> bool:
    """Check if system has sufficient memory."""
    try:
        mem = psutil.virtual_memory()
        return mem.available >= 500 * 1024 * 1024  # 500MB min
    except Exception as e:
        logger.error("memory_check_failed", error=str(e))
        return False

def check_cache() -> bool:
    """Verify cache system is operational."""
    try:
        test_key = f"health_check_{time.time()}"
        CACHE.set(test_key, "test")
        result = CACHE.get(test_key) == "test"
        return result
    except Exception as e:
        logger.error("cache_check_failed", error=str(e))
        return False

def check_required_paths() -> Dict[str, bool]:
    """Check existence of required paths."""
    paths = {
        "cache_dir": Path("cache").exists(),
        "logs_dir": Path("logs").exists(),
        "events_log": Path("logs/events.jsonl").exists(),
        "telemetry_dir": Path("telemetry").exists()
    }
    return paths

def liveness() -> Dict[str, Any]:
    """Basic liveness check."""
    return {
        "ok": True,
        "ts": time.time(),
        "process_uptime": time.time() - psutil.Process().create_time()
    }

def readiness() -> Dict[str, Any]:
    """Comprehensive readiness check of all components."""
    # Check paths
    path_checks = check_required_paths()
    
    # Component checks
    component_checks = {
        "cache": check_cache(),
        "memory": check_memory(),
        "disk_space": check_disk_space(Path(".")),
        "metrics": True  # Set to False if metrics server fails
    }
    
    # Combine all checks
    all_checks = {**path_checks, **component_checks}
    system_ready = all(all_checks.values())
    
    # Update gauge for monitoring
    GAUGES["system_ready"] = float(system_ready)
    
    result = {
        "ok": system_ready,
        "ts": time.time(),
        "checks": all_checks
    }
    
    # Log failures
    if not system_ready:
        failed = [k for k, v in all_checks.items() if not v]
        logger.warning("system_not_ready",
                      failed_checks=failed)
    
    return result

def get_system_metrics() -> Dict[str, Any]:
    """Get detailed system metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(".")
        
        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "memory_available_mb": mem.available / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024 * 1024 * 1024)
        }
        
        # Update gauges
        for k, v in metrics.items():
            GAUGES[f"system_{k}"] = float(v)
            
        return metrics
    except Exception as e:
        logger.error("system_metrics_failed", error=str(e))
        return {}