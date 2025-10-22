"""
Memory reconciliation job scheduler.
Manages scheduling and execution of nightly reconciliation jobs.
"""
import asyncio
from datetime import datetime, time, timedelta
import structlog
from typing import Optional

from .reconciliation import MemoryReconciliationJob, ReconciliationReport
from .write_cache import MemoryWriteCache

logger = structlog.get_logger(__name__)

class ReconciliationScheduler:
    """Schedules and manages memory reconciliation jobs"""
    
    def __init__(
        self,
        write_cache: MemoryWriteCache,
        schedule_time: time = time(hour=2, minute=0),  # 2 AM default
        max_runtime_minutes: int = 120  # 2 hour max runtime
    ):
        self.write_cache = write_cache
        self.schedule_time = schedule_time
        self.max_runtime = timedelta(minutes=max_runtime_minutes)
        self.running = False
        self.last_report: Optional[ReconciliationReport] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the reconciliation scheduler"""
        if self.running:
            return
            
        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            "Reconciliation scheduler started",
            schedule_time=self.schedule_time.strftime("%H:%M")
        )

    async def stop(self) -> None:
        """Stop the reconciliation scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Reconciliation scheduler stopped")

    async def run_now(self) -> ReconciliationReport:
        """
        Trigger immediate reconciliation run
        
        Returns:
            ReconciliationReport with results
        """
        job = MemoryReconciliationJob(self.write_cache)
        self.last_report = await job.reconcile()
        return self.last_report

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self.running:
            try:
                # Calculate time until next run
                now = datetime.now()
                target = datetime.combine(now.date(), self.schedule_time)
                
                # If we've passed today's time, schedule for tomorrow
                if now.time() >= self.schedule_time:
                    target += timedelta(days=1)
                    
                # Sleep until scheduled time
                delay = (target - now).total_seconds()
                await asyncio.sleep(delay)
                
                # Run reconciliation with timeout
                try:
                    async with asyncio.timeout(self.max_runtime.total_seconds()):
                        await self.run_now()
                        
                except asyncio.TimeoutError:
                    logger.error(
                        "Reconciliation job timed out",
                        max_runtime_minutes=self.max_runtime.total_seconds() / 60
                    )
                    
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                # Sleep for a bit before retrying
                await asyncio.sleep(60)

    @property
    def next_run_time(self) -> datetime:
        """Get the next scheduled run time"""
        now = datetime.now()
        target = datetime.combine(now.date(), self.schedule_time)
        if now.time() >= self.schedule_time:
            target += timedelta(days=1)
        return target

    @property
    def status(self) -> dict:
        """Get current scheduler status"""
        return {
            "running": self.running,
            "next_run": self.next_run_time,
            "last_report": self.last_report.__dict__ if self.last_report else None,
            "schedule_time": self.schedule_time.strftime("%H:%M")
        }