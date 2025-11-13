#!/usr/bin/env python3
"""
ASTRA Phase 4 - Download HuggingFace Datasets
Ingests 4 HF datasets to local disk for staging environment
Date: November 13, 2025
"""

import logging
import sys
from pathlib import Path

from datasets import load_dataset

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent.parent
DATASET_DIR = BASE_DIR / "phase4_staging" / "datasets"
LOGDIR = BASE_DIR / "phase4_staging" / "logs"

DATASET_DIR.mkdir(parents=True, exist_ok=True)
LOGDIR.mkdir(parents=True, exist_ok=True)

# Setup logging (file only to avoid encoding issues)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGDIR / "dataset_download.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger("astra.dataset")

# Also print to console
console = logging.StreamHandler(sys.stdout)
console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console)

# ============================================================================
# DATASETS TO DOWNLOAD (WITH REQUIRED CONFIGS)
# ============================================================================

DATASETS = [
    {
        "name": "rag-mini-wikipedia",
        "hf_id": "rag-datasets/rag-mini-wikipedia",
        "config": "text-corpus",
        "local_name": "rag_mini_wikipedia"
    },
    {
        "name": "rag-mini-bioasq",
        "hf_id": "rag-datasets/rag-mini-bioasq",
        "config": "text-corpus",
        "local_name": "rag_mini_bioasq"
    },
    {
        "name": "RAGBench",
        "hf_id": "rungalileo/ragbench",
        "config": "covidqa",
        "local_name": "ragbench"
    },
    {
        "name": "CXM_Arena",
        "hf_id": "sprinklr-huggingface/CXM_Arena",
        "config": "KB_Refinement",
        "local_name": "CXM_Arena"
    }
]

# ============================================================================
# DOWNLOAD FUNCTION
# ============================================================================

def download_dataset(dataset_config: dict) -> bool:
    """Download a HuggingFace dataset and save to disk."""
    name = dataset_config["name"]
    hf_id = dataset_config["hf_id"]
    config = dataset_config["config"]
    local_name = dataset_config["local_name"]

    try:
        logger.info(f"Processing: {name}")
        logger.info(f"  HF ID: {hf_id}")
        logger.info(f"  Config: {config}")

        save_path = DATASET_DIR / local_name
        if save_path.exists():
            logger.info(f"  Already exists at {save_path}, skipping")
            return True

        logger.info("  Loading dataset...")
        ds = load_dataset(hf_id, config, trust_remote_code=False)

        logger.info("  Saving to disk...")
        ds.save_to_disk(str(save_path))

        # Try to get record count from any available split
        try:
            if isinstance(ds, dict):
                record_count = len(ds[list(ds.keys())[0]])
            else:
                record_count = len(ds)
            logger.info(f"  Success: saved {record_count} records")
        except Exception as count_error:
            logger.info(f"  Success: dataset saved (record count unavailable: {count_error})")

        return True

    except Exception as e:
        logger.error(f"Failed to download {name}: {e}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("ASTRA PHASE 4 - DATASET DOWNLOAD")
    logger.info("=" * 70)
    logger.info(f"Dataset Directory: {DATASET_DIR}")
    logger.info("")

    successful = 0
    failed = 0

    for dataset_config in DATASETS:
        if download_dataset(dataset_config):
            successful += 1
        else:
            failed += 1
        logger.info("")

    logger.info("=" * 70)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info("")
    logger.info("Next: Run vector store ingestion")
    logger.info("  python3 ingest_to_vectorstore.py")
    logger.info("")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
