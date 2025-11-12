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

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent.parent
DATASET_DIR = BASE_DIR / "phase4_staging" / "datasets"
LOGDIR = BASE_DIR / "phase4_staging" / "logs"

DATASET_DIR.mkdir(parents=True, exist_ok=True)
LOGDIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGDIR / "dataset_download.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("astra.dataset")

# ============================================================================
# DATASETS TO DOWNLOAD
# ============================================================================

DATASETS = [
    {
        "name": "rag-mini-wikipedia",
        "hf_id": "rag-datasets/rag-mini-wikipedia",
        "local_name": "rag_mini_wikipedia"
    },
    {
        "name": "rag-mini-bioasq",
        "hf_id": "rag-datasets/rag-mini-bioasq",
        "local_name": "rag_mini_bioasq"
    },
    {
        "name": "RAGBench",
        "hf_id": "rungalileo/ragbench",
        "local_name": "ragbench"
    },
    {
        "name": "CXM_Arena",
        "hf_id": "sprinklr-huggingface/CXM_Arena",
        "local_name": "CXM_Arena"
    }
]

# ============================================================================
# DOWNLOAD FUNCTION
# ============================================================================

def download_dataset(name: str, hf_id: str, local_name: str) -> bool:
    """
    Download a HuggingFace dataset and save to disk.
    
    Args:
        name: Human-readable name
        hf_id: HuggingFace dataset ID (org/name)
        local_name: Local directory name
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        save_path = DATASET_DIR / local_name
        logger.info(f"Loading dataset: {name} (HF ID: {hf_id})")
        
        # Load dataset
        ds = load_dataset(hf_id)
        logger.info(f"  ✅ Loaded successfully")
        logger.info(f"  Dataset info: {ds}")
        
        # Save to disk
        logger.info(f"  Saving to: {save_path}")
        ds.save_to_disk(str(save_path))
        logger.info(f"  ✅ Saved successfully")
        
        # Verify
        ds_verify = datasets.load_from_disk(str(save_path))
        record_count = len(ds_verify['train']) if 'train' in ds_verify else len(ds_verify[0])
        logger.info(f"  ✅ Verified with {record_count} records")
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Failed to download {name}: {e}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("╔════════════════════════════════════════════════════════════════╗")
    logger.info("║     ASTRA PHASE 4 - DATASET DOWNLOAD                          ║")
    logger.info("╚════════════════════════════════════════════════════════════════╝")
    logger.info("")
    logger.info(f"Dataset Directory: {DATASET_DIR}")
    logger.info("")
    
    successful = 0
    failed = 0
    
    for dataset_config in DATASETS:
        logger.info(f"Processing: {dataset_config['name']}")
        if download_dataset(
            dataset_config['name'],
            dataset_config['hf_id'],
            dataset_config['local_name']
        ):
            successful += 1
        else:
            failed += 1
        logger.info("")
    
    # Summary
    logger.info("╔════════════════════════════════════════════════════════════════╗")
    logger.info("║                 DOWNLOAD COMPLETE                              ║")
    logger.info("╚════════════════════════════════════════════════════════════════╝")
    logger.info(f"  ✅ Successful: {successful}")
    logger.info(f"  ❌ Failed: {failed}")
    logger.info("")
    logger.info(f"Next: Run vector store ingestion")
    logger.info(f"  python3 ingest_to_vectorstore.py")
    logger.info("")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    # Import datasets here to avoid issues if not installed
    try:
        import datasets
    except ImportError:
        logger.error("datasets library not found. Install with: pip install datasets huggingface_hub")
        sys.exit(1)
    
    sys.exit(main())
