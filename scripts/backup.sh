#!/usr/bin/env bash
# Simple backup script for Phase 0
# - dumps Postgres DB to backups/postgres_YYYYMMDD_HHMM.sql
# - copies WAL files and local vault

set -euo pipefail

OUTDIR="backups"
mkdir -p "$OUTDIR"

TS=$(date +"%Y%m%d_%H%M%S")
PG_DSN=${DATABASE_URL:-"postgres://astra:password@localhost:5432/astra"}

echo "[backup] timestamp=$TS"

echo "[backup] dumping postgres..."
PG_FILE="$OUTDIR/postgres_${TS}.sql"
pg_dump "$PG_DSN" -Fc -f "$PG_FILE" || { echo "pg_dump failed"; exit 2; }
echo "[backup] postgres -> $PG_FILE"

echo "[backup] copying WAL files (if any)..."
if [ -d "data/wal" ]; then
  cp -r data/wal "$OUTDIR/wal_${TS}" || true
  echo "[backup] wal copied"
fi

if [ -f "data/local_vault.json" ]; then
  cp data/local_vault.json "$OUTDIR/local_vault_${TS}.json" || true
  echo "[backup] local vault copied"
fi

echo "[backup] complete"
