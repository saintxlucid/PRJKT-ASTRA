"""
System initialization and configuration.
"""
import threading
import time
from pathlib import Path
import structlog

from astra.telemetry.metrics import serve_metrics
from astra.ops.health import readiness
from astra.ops.maintenance import maintenance_cycle, AutoTuner

logger = structlog.get_logger()

def init_system(
    metrics_port: int = 9108,
    maintenance_interval: int = 3600,
    auto_tune_interval: int = 60
):
    """
    Initialize system components and background tasks.
    
    Args:
        metrics_port: Port for metrics server
        maintenance_interval: Seconds between maintenance runs
        auto_tune_interval: Seconds between auto-tune checks
    """
    # Ensure directories exist
    Path("cache").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("telemetry").mkdir(exist_ok=True)
    
    # Start metrics server
    serve_metrics(port=metrics_port)
    logger.info("metrics_server_started", port=metrics_port)
    
    # Initialize auto-tuner
    tuner = AutoTuner()
    
    # Start maintenance thread
    def maintenance_loop():
        while True:
            try:
                maintenance_cycle()
            except Exception as e:
                logger.error("maintenance_cycle_failed",
                           error=str(e))
            time.sleep(maintenance_interval)
    
    maintenance_thread = threading.Thread(
        target=maintenance_loop,
        daemon=True,
        name="maintenance"
    )
    maintenance_thread.start()
    
    # Start auto-tuner thread
    def auto_tune_loop():
        while True:
            try:
                tuner.check()
            except Exception as e:
                logger.error("auto_tune_failed",
                           error=str(e))
            time.sleep(auto_tune_interval)
    
    tune_thread = threading.Thread(
        target=auto_tune_loop,
        daemon=True,
        name="auto-tune"
    )
    tune_thread.start()
    
    # Check readiness
    ready = readiness()
    if not ready["ok"]:
        logger.warning("system_not_ready",
                      checks=ready["checks"])
    else:
        logger.info("system_ready")