#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d-%H%M)
OUT=/var/backups/astra/$TS
mkdir -p "$OUT"
# SQLite episodic/procedural
cp /data/astra/episodic.sqlite "$OUT/episodic.sqlite"
cp /data/astra/procedural.sqlite "$OUT/procedural.sqlite"
# Chroma or Qdrant (file-based example; adapt for remote)
tar czf "$OUT/vector_store.tgz" -C /data/astra/vector .
echo "$TS backup complete -> $OUT"
find /var/backups/astra -type d -mtime +14 -exec rm -rf {} + || true