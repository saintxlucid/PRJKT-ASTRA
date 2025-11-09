#!/usr/bin/env bash
# ASTRA Mini-Corpus Builder (Bash)
# Build normalized JSONL corpora from downloaded datasets
# Offline-only: uses local data only

set -euo pipefail

# Activate venv
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Set environment
export PYTHONPATH="$PWD"
export ASTRA_ALLOW_NETWORK=0  # Enforce offline mode
export ASTRA_DATA_DIR="./data"
export ASTRA_CORPUS_DIR="./corpora"

echo "[ASTRA] Building mini-corpora (offline)..."
echo "[*] Data dir: $ASTRA_DATA_DIR"
echo "[*] Output dir: $ASTRA_CORPUS_DIR"
echo ""

# Run builder
python tools/build_mini_corpus.py

echo ""
echo "[OK] Mini-corpora ready under ./corpora"
echo ""
echo "Usage:"
echo "  head -5 ./corpora/*.jsonl"
echo "  jq . ./corpora/contemmcm__clinc150.jsonl | head -20"
