#!/usr/bin/env python3
"""
WAL Checkpoint Maintenance Script

Runs PRAGMA wal_checkpoint(TRUNCATE) on ASTRA database to clean up WAL files.
Schedule this to run weekly to prevent WAL bloat.

Usage:
  python scripts/wal_checkpoint.py

Scheduling (Windows Task Scheduler):
  schtasks /create /tn "ASTRA WAL Checkpoint" /tr "python X:\PROJECT_ASTRA_1.0\scripts\wal_checkpoint.py" /sc weekly /d SUN /st 03:00
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def checkpoint_database(db_path: str) -> bool:
    """
    Run WAL checkpoint on database.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"[{datetime.now().isoformat()}] Starting WAL checkpoint for: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"ERROR: Database not found: {db_path}")
            return False
        
        # Connect and run checkpoint
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get WAL info before checkpoint
        cursor.execute("PRAGMA wal_checkpoint")
        before = cursor.fetchone()
        print(f"  Before: busy={before[0]}, log_frames={before[1]}, checkpointed_frames={before[2]}")
        
        # Run TRUNCATE checkpoint
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        after = cursor.fetchone()
        print(f"  After:  busy={after[0]}, log_frames={after[1]}, checkpointed_frames={after[2]}")
        
        # Verify WAL mode is still enabled
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        print(f"  Journal mode: {mode}")
        
        conn.close()
        
        print(f"[{datetime.now().isoformat()}] Checkpoint completed successfully")
        return True
        
    except Exception as e:
        print(f"ERROR: Checkpoint failed: {e}")
        return False


def main():
    """Main entry point."""
    # Default database path
    repo_root = Path(__file__).parent.parent
    db_path = repo_root / "data" / "database" / "astra.db"
    
    # Allow override via environment variable
    db_path_env = os.getenv("ASTRA_DATABASE_PATH")
    if db_path_env:
        db_path = Path(db_path_env)
    
    print("=" * 60)
    print("ASTRA Database WAL Checkpoint")
    print("=" * 60)
    
    success = checkpoint_database(str(db_path))
    
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
