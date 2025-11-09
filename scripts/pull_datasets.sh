#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate

# OPTIONAL: Temporarily relax outbound block if your privacy layer is strict
# export ASTRA_ALLOW_NETWORK=1

python tools/bootstrap_datasets.py
python scripts/verify_downloads.py

echo "[ASTRA] Done. Datasets cached in ./data and ./cache."
