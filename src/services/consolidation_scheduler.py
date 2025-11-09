# Memory Consolidation Scheduler
# SPDX-License-Identifier: MIT
"""
ConsolidationScheduler: Background job for nightly memory consolidation.

Runs memory consolidation on a schedule (cron-like):
- Default: 2 AM daily (low system usage)
- Configurable schedule via astra.yaml
- Graceful shutdown support
- Job status tracking

Implementation: APScheduler (cron scheduler) + background thread.

Usage:
    scheduler = ConsolidationScheduler(
        consolidation_service=service,
        schedule="0 2 * * *"  # 2 AM daily (cron format)
    )
    
    scheduler.start()  # Start background thread
    # ... app runs ...
    scheduler.stop()   # Graceful shutdown
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# APScheduler for cron-like scheduling
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

from services.memory_consolidation import MemoryConsolidationService

logger = logging.getLogger(__name__)


@dataclass
class JobRun:
    """Single consolidation job run."""
    timestamp: str
    status: str  # "success", "error", "skipped"
    events_count: int
    clusters_count: int
    duration_seconds: float
    error: str | None = None


class ConsolidationScheduler:
    """
    Background scheduler for memory consolidation.
    
    Features:
    - Cron-like scheduling (e.g., "0 2 * * *" = 2 AM daily)
    - Graceful shutdown
    - Job history tracking
    - Error handling with retry logic
    
    Usage:
        scheduler = ConsolidationScheduler(
            consolidation_service=service,
            schedule="0 2 * * *"
        )
        
        scheduler.start()
        # ... app runs ...
        scheduler.stop()
    """
    
    def __init__(
        self,
        consolidation_service: MemoryConsolidationService,
        schedule: str = "0 2 * * *",  # 2 AM daily
        enabled: bool = True
    ):
        if not APSCHEDULER_AVAILABLE:
            raise RuntimeError(
                "APScheduler not installed. Run: pip install apscheduler"
            )
        
        self.service = consolidation_service
        self.schedule = schedule
        self.enabled = enabled
        
        # Job tracking
        self.job_history: list[JobRun] = []
        self.is_running = False
        self.lock = threading.Lock()
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
    
    def _run_consolidation_job(self):
        """
        Run consolidation job (internal).
        
        Called by APScheduler on schedule.
        Tracks job status and errors.
        """
        if not self.enabled:
            logger.info("Consolidation scheduler disabled, skipping job")
            return
        
        # Prevent concurrent runs
        if self.is_running:
            logger.warning("Consolidation job already running, skipping")
            return
        
        with self.lock:
            self.is_running = True
        
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        try:
            logger.info("Starting memory consolidation job")
            result = self.service.consolidate()
            
            # Track job run
            job_run = JobRun(
                timestamp=timestamp,
                status=result["status"],
                events_count=result["events_count"],
                clusters_count=result["clusters_count"],
                duration_seconds=result["duration_seconds"]
            )
            
            self.job_history.append(job_run)
            
            logger.info(
                f"Consolidation complete: {result['events_count']} events, "
                f"{result['clusters_count']} clusters, "
                f"{result['duration_seconds']}s"
            )
        
        except Exception as e:
            logger.error(f"Consolidation job failed: {e}")
            
            # Track error
            job_run = JobRun(
                timestamp=timestamp,
                status="error",
                events_count=0,
                clusters_count=0,
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
            
            self.job_history.append(job_run)
        
        finally:
            with self.lock:
                self.is_running = False
    
    def start(self):
        """
        Start scheduler (background thread).
        
        The scheduler will run consolidation on schedule until stop() is called.
        """
        if not self.enabled:
            logger.info("Consolidation scheduler disabled, not starting")
            return
        
        logger.info(f"Starting consolidation scheduler (schedule: {self.schedule})")
        
        # Add job with cron trigger
        self.scheduler.add_job(
            self._run_consolidation_job,
            CronTrigger.from_crontab(self.schedule),
            id="memory_consolidation",
            name="Memory Consolidation Job",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Consolidation scheduler started")
    
    def stop(self):
        """
        Stop scheduler (graceful shutdown).
        
        Waits for current job to complete before shutting down.
        """
        logger.info("Stopping consolidation scheduler...")
        
        # Wait for current job to finish
        while self.is_running:
            logger.info("Waiting for consolidation job to complete...")
            time.sleep(1)
        
        self.scheduler.shutdown(wait=True)
        logger.info("Consolidation scheduler stopped")
    
    def run_now(self, mode: str = "live", since: str | None = None, limit: int = 0) -> dict[str, Any]:
        """
        Run consolidation immediately (manual trigger).

        Args:
            mode: live|dry|backfill
            since: ISO timestamp for backfill
            limit: max events to process (0 = default)

        Returns:
            Consolidation result dict
        """
        logger.info(f"Running consolidation manually (mode={mode}, since={since}, limit={limit})")

        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            result = self.service.consolidate(mode=mode, since=since, limit=limit)

            # Track job run
            job_run = JobRun(
                timestamp=timestamp,
                status=result.get("status", "success"),
                events_count=result.get("events_count", 0),
                clusters_count=result.get("clusters_count", 0),
                duration_seconds=result.get("duration_seconds", 0.0)
            )

            self.job_history.append(job_run)

            logger.info(
                f"Consolidation complete: {result.get('events_count', 0)} events, "
                f"{result.get('clusters_count', 0)} clusters, "
                f"{result.get('duration_seconds', 0.0)}s"
            )

            return {
                "timestamp": timestamp,
                "status": job_run.status,
                "events_count": job_run.events_count,
                "clusters_count": job_run.clusters_count,
                "duration_seconds": job_run.duration_seconds,
                "error": None
            }

        except Exception as e:
            logger.error(f"Consolidation manual run failed: {e}")
            job_run = JobRun(
                timestamp=timestamp,
                status="error",
                events_count=0,
                clusters_count=0,
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
            self.job_history.append(job_run)
            return {
                "timestamp": timestamp,
                "status": "error",
                "events_count": 0,
                "clusters_count": 0,
                "duration_seconds": job_run.duration_seconds,
                "error": str(e)
            }
    
    def get_job_history(self, limit: int = 10) -> list[dict]:
        """
        Get recent job history.
        
        Args:
            limit: Number of recent jobs to return
        
        Returns:
            List of job run dicts
        """
        return [
            {
                "timestamp": run.timestamp,
                "status": run.status,
                "events_count": run.events_count,
                "clusters_count": run.clusters_count,
                "duration_seconds": run.duration_seconds,
                "error": run.error
            }
            for run in self.job_history[-limit:]
        ]
    
    def get_next_run_time(self) -> str | None:
        """
        Get next scheduled run time.
        
        Returns:
            ISO timestamp of next run, or None if not scheduled
        """
        job = self.scheduler.get_job("memory_consolidation")
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None


# Factory function
def build_scheduler_from_config(
    conf: dict,
    consolidation_service: MemoryConsolidationService
) -> ConsolidationScheduler:
    """
    Factory: Build ConsolidationScheduler from config.
    
    Config example (astra.yaml):
        memory_consolidation:
          enabled: true
          schedule: "0 2 * * *"  # 2 AM daily (cron format)
    """
    cons_conf = conf.get("memory_consolidation", {})
    
    return ConsolidationScheduler(
        consolidation_service=consolidation_service,
        schedule=cons_conf.get("schedule", "0 2 * * *"),
        enabled=cons_conf.get("enabled", True)
    )


# CLI for manual testing
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from gateways.event_store_sqlite import SQLiteEventStore
    from gateways.chroma_memory_gateway_bge import ChromaMemoryGatewayBGE
    from services.llm_service_local import LocalLLMService
    from services.memory_consolidation import (
        MemoryConsolidationService,
        ConsolidationConfig
    )
    
    print("=== Consolidation Scheduler Test ===\n")
    
    # Initialize dependencies
    print("Initializing dependencies...")
    event_store = SQLiteEventStore(db_path="data/eventlog.sqlite")
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()
    
    consolidation_service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig(min_events=5)
    )
    
    # Initialize scheduler (run every minute for testing)
    scheduler = ConsolidationScheduler(
        consolidation_service=consolidation_service,
        schedule="* * * * *",  # Every minute
        enabled=True
    )
    
    print("✅ Scheduler initialized\n")
    
    # Start scheduler
    print("Starting scheduler...")
    scheduler.start()
    
    print(f"✅ Scheduler started")
    print(f"   Next run: {scheduler.get_next_run_time()}\n")
    
    # Run manually
    print("Running consolidation manually...")
    result = scheduler.run_now()
    
    print("\n✅ Manual run complete:")
    print(f"   Status: {result['status']}")
    print(f"   Events: {result['events_count']}")
    print(f"   Clusters: {result['clusters_count']}")
    
    # Show history
    print("\n📊 Job History:")
    for i, run in enumerate(scheduler.get_job_history(), 1):
        print(f"   {i}. {run['timestamp']}: {run['status']} ({run['events_count']} events)")
    
    # Wait a bit, then stop
    print("\n⏳ Waiting 10 seconds...")
    time.sleep(10)
    
    print("\nStopping scheduler...")
    scheduler.stop()
    
    print("\n✅ Test complete")
