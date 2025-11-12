#!/usr/bin/env bash
# ASTRA Asset Ingestion Script - Clone Repos & Download Datasets
# Phase 4 Staging Environment Setup
# Date: November 13, 2025

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_DIR="$BASE_DIR/phase4_staging/repos"
DATASET_DIR="$BASE_DIR/phase4_staging/datasets"
SCRIPTS_DIR="$BASE_DIR/phase4_staging/scripts"
LOGDIR="$BASE_DIR/phase4_staging/logs"
REGISTRY="$BASE_DIR/phase4_staging/registry/assets_registry.yml"

# Create directories
mkdir -p "$REPO_DIR" "$DATASET_DIR" "$SCRIPTS_DIR" "$LOGDIR"

# Setup logging
LOGFILE="$LOGDIR/ingestion_$(date +%Y%m%d_%H%M%S).log"
exec 1> >(tee -a "$LOGFILE")
exec 2>&1

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        ASTRA PHASE 4 - ASSET INGESTION SCRIPT                 ║"
echo "║            Staging Environment Setup                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Base Directory: $BASE_DIR"
echo "Repo Directory: $REPO_DIR"
echo "Dataset Directory: $DATASET_DIR"
echo "Log File: $LOGFILE"
echo ""

# ============================================================================
# CLONE REPOSITORIES
# ============================================================================

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting repository cloning..."
echo ""

REPOS=(
  "https://github.com/KalyanKS-NLP/llm-engineer-toolkit.git"
  "https://github.com/neulab/ragged.git"
  "https://github.com/tensorchord/Awesome-LLMOps.git"
  "https://github.com/kaushikb11/awesome-llm-agents.git"
  "https://github.com/tooniez/llm-toolkit.git"
)

CLONED_REPOS=0
FAILED_REPOS=0

for url in "${REPOS[@]}"; do
  name=$(basename "$url" .git)
  dest="$REPO_DIR/$name"
  
  echo "Repository: $name"
  echo "  URL: $url"
  echo "  Destination: $dest"
  
  if [ -d "$dest" ]; then
    echo "  Status: Already exists, pulling latest..."
    if git -C "$dest" pull 2>&1 | tee -a "$LOGFILE"; then
      echo "  ✅ Pull successful"
      ((CLONED_REPOS++))
    else
      echo "  ⚠️  Pull failed (may be offline or permission issue)"
      ((FAILED_REPOS++))
    fi
  else
    echo "  Status: Cloning..."
    if git clone --depth 1 "$url" "$dest" 2>&1 | tee -a "$LOGFILE"; then
      echo "  ✅ Clone successful"
      ((CLONED_REPOS++))
    else
      echo "  ❌ Clone failed"
      ((FAILED_REPOS++))
    fi
  fi
  echo ""
done

echo "Repositories Summary:"
echo "  ✅ Cloned/Updated: $CLONED_REPOS"
echo "  ❌ Failed: $FAILED_REPOS"
echo ""

# ============================================================================
# DOWNLOAD DATASETS
# ============================================================================

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting dataset download..."
echo ""

# Call Python script to download datasets
if command -v python3 &> /dev/null; then
  python3 "$SCRIPTS_DIR/download_datasets.py" 2>&1 | tee -a "$LOGFILE"
else
  echo "⚠️  Python3 not found. Skipping dataset download."
  echo "    Install Python3 and run: python3 $SCRIPTS_DIR/download_datasets.py"
fi

# ============================================================================
# COMPLETION SUMMARY
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                 INGESTION SCRIPT COMPLETE                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next Steps:"
echo "  1. Review cloned repositories:"
echo "     ls -la $REPO_DIR"
echo ""
echo "  2. Review downloaded datasets:"
echo "     ls -la $DATASET_DIR"
echo ""
echo "  3. Run smoke tests on repositories:"
echo "     cd $SCRIPTS_DIR && python3 test_repo_builds.py"
echo ""
echo "  4. Ingest datasets to vector store:"
echo "     python3 $SCRIPTS_DIR/ingest_to_vectorstore.py"
echo ""
echo "  5. Run integration tests:"
echo "     python3 $SCRIPTS_DIR/run_integration_tests.py"
echo ""
echo "  6. Update registry with results:"
echo "     Registry file: $REGISTRY"
echo ""
echo "Log file: $LOGFILE"
echo ""
