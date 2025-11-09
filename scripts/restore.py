"""
Restore script for Phase 0 backups.

Usage:
    python scripts/restore.py backups/postgres_20250101_120000.sql

This script assumes `psql` is available and DATABASE_URL env var points to target DB.
"""
import sys
import os
import subprocess


def restore_postgres(file_path: str):
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Set DATABASE_URL for target Postgres")

    if not os.path.exists(file_path):
        raise RuntimeError(f"Backup file not found: {file_path}")

    print(f"Restoring {file_path} to {dsn}")
    subprocess.check_call(["pg_restore", "-d", dsn, "-c", file_path])


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore.py <postgres_backup_file>")
        sys.exit(2)

    restore_postgres(sys.argv[1])


if __name__ == "__main__":
    main()
