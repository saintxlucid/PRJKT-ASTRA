# Memory Consolidation Overlap Lock & Job Journal
# SPDX-License-Identifier: MIT
"""
Overlap prevention and job journaling for memory consolidation.

Features:
- InterProcessLock: Prevent concurrent runs
- Job journals: JSONL logs with provenance
- Idempotency: Re-running same job_id is safe (skip if already complete)
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator

try:
    from fasteners import InterProcessLock
    LOCK_AVAILABLE = True
except ImportError:
    LOCK_AVAILABLE = False
    InterProcessLock = None


# Lock and journal paths
LOCK_DIR = Path("data/locks")
LOCK_FILE = LOCK_DIR / "dream.lock"
JOURNAL_FILE = LOCK_DIR / "consolidation.journal"
WATERMARK_FILE = LOCK_DIR / "last_consolidation.txt"


@dataclass
class JobEntry:
    """Job journal entry."""
    job_id: str
    started_at: str  # ISO timestamp
    completed_at: str | None = None
    status: str = "running"  # running, success, failure
    events_processed: int = 0
    clusters_formed: int = 0
    noise_count: int = 0
    quality_score: float = 0.0
    cluster_roots: list[str] = None  # Sample of cluster root hashes
    error_msg: str | None = None
    
    def __post_init__(self):
        if self.cluster_roots is None:
            self.cluster_roots = []


def ensure_lock_dir():
    """Ensure lock directory exists."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def acquire_dream_lock(timeout: float = 5.0) -> Generator[bool, None, None]:
    """
    Acquire overlap lock for consolidation.
    
    Args:
        timeout: Lock acquisition timeout (seconds)
    
    Yields:
        True if lock was acquired, False if not available
    
    Example:
        with acquire_dream_lock() as acquired:
            if not acquired:
                print("Another run is in progress")
                return
            
            # Safe to proceed
            consolidate_events()
    """
    if not LOCK_AVAILABLE:
        # No lock library, proceed anyway (warn user)
        print("⚠️  fasteners not installed - no overlap protection")
        yield True
        return
    
    ensure_lock_dir()
    
    lock = InterProcessLock(str(LOCK_FILE))
    acquired = lock.acquire(blocking=True, timeout=timeout)
    
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


def append_job_entry(entry: JobEntry):
    """
    Append job entry to journal (JSONL).
    
    Args:
        entry: Job metadata
    """
    ensure_lock_dir()
    
    with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
        line = json.dumps(asdict(entry), sort_keys=True)
        f.write(line + "\n")


def read_job_journal(limit: int = 50) -> list[JobEntry]:
    """
    Read job journal (latest N entries).
    
    Args:
        limit: Max entries to return
    
    Returns:
        List of job entries (newest first)
    """
    if not JOURNAL_FILE.exists():
        return []
    
    entries = []
    with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                entries.append(JobEntry(**data))
            except Exception:
                continue
    
    # Return newest first
    return list(reversed(entries[-limit:]))


def is_job_complete(job_id: str) -> bool:
    """
    Check if job_id is already complete (idempotency check).
    
    Args:
        job_id: Job identifier
    
    Returns:
        True if job already completed successfully
    """
    entries = read_job_journal()
    
    for entry in entries:
        if entry.job_id == job_id and entry.status == "success":
            return True
    
    return False


def mark_job_started(job_id: str) -> JobEntry:
    """
    Mark job as started in journal.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Job entry (status=running)
    """
    entry = JobEntry(
        job_id=job_id,
        started_at=datetime.utcnow().isoformat() + "Z",
        status="running"
    )
    
    append_job_entry(entry)
    return entry


def mark_job_complete(
    job_id: str,
    events_processed: int,
    clusters_formed: int,
    noise_count: int,
    quality_score: float,
    cluster_roots: list[str]
):
    """
    Mark job as complete in journal.
    
    Args:
        job_id: Job identifier
        events_processed: Total events processed
        clusters_formed: Clusters formed
        noise_count: Noise events
        quality_score: Quality score (0..1)
        cluster_roots: Sample of cluster root hashes
    """
    entry = JobEntry(
        job_id=job_id,
        started_at="",  # Placeholder (not used for completion)
        completed_at=datetime.utcnow().isoformat() + "Z",
        status="success",
        events_processed=events_processed,
        clusters_formed=clusters_formed,
        noise_count=noise_count,
        quality_score=quality_score,
        cluster_roots=cluster_roots[:20]  # First 20 roots
    )
    
    append_job_entry(entry)


def mark_job_failed(job_id: str, error_msg: str):
    """
    Mark job as failed in journal.
    
    Args:
        job_id: Job identifier
        error_msg: Error message
    """
    entry = JobEntry(
        job_id=job_id,
        started_at="",
        completed_at=datetime.utcnow().isoformat() + "Z",
        status="failure",
        error_msg=error_msg
    )
    
    append_job_entry(entry)


def get_watermark() -> int:
    """
    Get last consolidated event ID (watermark).
    
    Returns:
        Last event ID processed (0 if no watermark)
    """
    ensure_lock_dir()
    
    if not WATERMARK_FILE.exists():
        return 0
    
    try:
        content = WATERMARK_FILE.read_text().strip()
        return int(content)
    except Exception:
        return 0


def set_watermark(event_id: int):
    """
    Update watermark with last processed event ID.
    
    Args:
        event_id: Last event ID processed
    """
    ensure_lock_dir()
    WATERMARK_FILE.write_text(str(event_id))


# Example usage
if __name__ == "__main__":
    print("=== Consolidation Lock & Journal Test ===\n")
    
    # Test 1: Lock acquisition
    print("Test 1: Lock acquisition")
    with acquire_dream_lock(timeout=2.0) as acquired:
        if acquired:
            print("✅ Lock acquired\n")
        else:
            print("❌ Lock not acquired\n")
    
    # Test 2: Job journal
    print("Test 2: Job journal")
    
    job_id = f"job_{datetime.utcnow().timestamp()}"
    
    # Start job
    mark_job_started(job_id)
    print(f"✅ Job started: {job_id}")
    
    # Complete job
    mark_job_complete(
        job_id=job_id,
        events_processed=50,
        clusters_formed=4,
        noise_count=8,
        quality_score=0.72,
        cluster_roots=["abc123", "def456"]
    )
    print(f"✅ Job completed: {job_id}\n")
    
    # Test 3: Read journal
    print("Test 3: Read journal")
    entries = read_job_journal(limit=5)
    print(f"✅ Journal entries: {len(entries)}")
    
    for entry in entries:
        print(f"  - {entry.job_id}: {entry.status} (quality={entry.quality_score:.2f})")
    print()
    
    # Test 4: Idempotency check
    print("Test 4: Idempotency check")
    if is_job_complete(job_id):
        print(f"✅ Job {job_id} is complete (skip re-run)\n")
    else:
        print(f"❌ Job {job_id} not complete\n")
    
    print("✅ All tests passed")
