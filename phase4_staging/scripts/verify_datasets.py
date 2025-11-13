#!/usr/bin/env python3
"""
ASTRA Phase 4 - Dataset Verification
Verifies downloaded datasets for integrity and structure
Date: November 13, 2025
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent.parent
DATASET_DIR = BASE_DIR / "phase4_staging" / "datasets"
LOGDIR = BASE_DIR / "phase4_staging" / "logs"
OUTPUT_DIR = BASE_DIR / "phase4_staging" / "reports"

LOGDIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGDIR / "dataset_verification.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("astra.verify_datasets")

# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def verify_dataset_structure(dataset_path: Path) -> dict[str, Any]:
    """Verify a dataset's structure."""
    try:
        # Check for dataset_dict.json
        dataset_dict_file = dataset_path / "dataset_dict.json"
        if not dataset_dict_file.exists():
            return {"valid": False, "error": "No dataset_dict.json found"}

        # Load and validate JSON
        try:
            with open(dataset_dict_file, 'r', encoding='utf-8') as f:
                dataset_dict = json.load(f)
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"Invalid JSON: {e}"}

        # Get splits
        splits = list(dataset_dict.keys())

        # Count records per split
        split_info = {}
        total_records = 0

        for split_name in splits:
            split_path = dataset_path / split_name
            if not split_path.exists():
                split_info[split_name] = {"error": "Split directory not found"}
                continue

            # Look for state.json to get record count
            state_file = split_path / "state.json"
            if state_file.exists():
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        record_count = state.get("_data_files", [{}])[0].get("num_examples", 0)
                        split_info[split_name] = {
                            "record_count": record_count,
                            "has_arrow_files": len(list(split_path.glob("*.arrow"))) > 0,
                        }
                        total_records += record_count
                except Exception as e:
                    split_info[split_name] = {"error": str(e)}
            else:
                split_info[split_name] = {"warning": "No state.json found"}

        return {
            "valid": True,
            "splits": splits,
            "split_info": split_info,
            "total_records": total_records,
        }

    except Exception as e:
        return {"valid": False, "error": str(e)}

def verify_dataset(dataset_path: Path) -> dict[str, Any]:
    """Verify a single dataset."""
    dataset_name = dataset_path.name

    logger.info(f"Verifying: {dataset_name}")

    result = {
        "name": dataset_name,
        "path": str(dataset_path),
        "exists": dataset_path.exists(),
        "is_directory": dataset_path.is_dir(),
    }

    if not dataset_path.exists():
        result["status"] = "NOT_FOUND"
        logger.error(f"  Dataset not found: {dataset_path}")
        return result

    # Verify structure
    structure = verify_dataset_structure(dataset_path)
    result.update(structure)

    if not structure.get("valid"):
        result["status"] = "INVALID_STRUCTURE"
        logger.error(f"  Invalid structure: {structure.get('error')}")
        return result

    result["status"] = "VERIFIED"
    logger.info("  Status: VERIFIED")
    logger.info(f"  Splits: {', '.join(structure['splits'])}")
    logger.info(f"  Total records: {structure['total_records']}")

    return result

# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("ASTRA PHASE 4 - DATASET VERIFICATION")
    logger.info("=" * 70)
    logger.info(f"Dataset Directory: {DATASET_DIR}")
    logger.info("")

    # Get list of datasets
    if not DATASET_DIR.exists():
        logger.error(f"Dataset directory not found: {DATASET_DIR}")
        return 1

    datasets = sorted([d for d in DATASET_DIR.iterdir() if d.is_dir()])
    if not datasets:
        logger.warning("No datasets found")
        return 1

    logger.info(f"Found {len(datasets)} datasets")
    logger.info("")

    # Verify each dataset
    results = []
    verified = 0
    failed = 0
    total_records = 0

    for dataset_path in datasets:
        verification = verify_dataset(dataset_path)
        results.append(verification)

        if verification.get("status") == "VERIFIED":
            verified += 1
            total_records += verification.get("total_records", 0)
        else:
            failed += 1

        logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("VERIFICATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Verified: {verified}/{len(datasets)}")
    logger.info(f"Failed: {failed}/{len(datasets)}")
    logger.info(f"Total records: {total_records}")
    logger.info("")

    # Save results
    output_file = OUTPUT_DIR / "dataset_verification_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": str(Path.cwd()),
            "total_datasets": len(datasets),
            "verified": verified,
            "failed": failed,
            "total_records": total_records,
            "results": results,
        }, f, indent=2)

    logger.info(f"Report saved to: {output_file}")
    logger.info("")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
