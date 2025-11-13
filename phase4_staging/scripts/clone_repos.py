#!/usr/bin/env python3
"""
ASTRA Phase 4 - Clone Repositories
Clones 5 LLM-related repositories for asset ingestion
Date: November 13, 2025
"""

import logging
import subprocess
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent.parent
REPO_DIR = BASE_DIR / "phase4_staging" / "repos"
LOGDIR = BASE_DIR / "phase4_staging" / "logs"

REPO_DIR.mkdir(parents=True, exist_ok=True)
LOGDIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGDIR / "repo_clone.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger("astra.repos")

# Also print to console
console = logging.StreamHandler(sys.stdout)
console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console)

# ============================================================================
# REPOSITORIES TO CLONE
# ============================================================================

REPOS = [
    {
        "name": "llm-engineer-toolkit",
        "url": "https://github.com/KalyanKS-NLP/llm-engineer-toolkit.git",
    },
    {
        "name": "ragged",
        "url": "https://github.com/neulab/ragged.git",
    },
    {
        "name": "Awesome-LLMOps",
        "url": "https://github.com/tensorchord/Awesome-LLMOps.git",
    },
    {
        "name": "awesome-llm-agents",
        "url": "https://github.com/kaushikb11/awesome-llm-agents.git",
    },
    {
        "name": "llm-toolkit",
        "url": "https://github.com/tooniez/llm-toolkit.git",
    },
]

# ============================================================================
# CLONE FUNCTION
# ============================================================================

def clone_repo(name: str, url: str) -> bool:
    """Clone a repository."""
    dest = REPO_DIR / name

    try:
        logger.info(f"Processing: {name}")
        logger.info(f"  URL: {url}")
        logger.info(f"  Destination: {dest}")

        if dest.exists():
            logger.info(f"  Already exists, updating...")
            result = subprocess.run(
                ["git", "-C", str(dest), "pull"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                logger.info("  Success: updated")
                return True
            else:
                logger.warning(f"  Warning: update failed - {result.stderr}")
                return True  # Still count as success (already exists)
        else:
            logger.info("  Cloning...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(dest)],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info("  Success: cloned")
                return True
            else:
                logger.error(f"  Error: {result.stderr}")
                return False

    except subprocess.TimeoutExpired:
        logger.error(f"  Error: timeout during clone")
        return False
    except Exception as e:
        logger.error(f"  Error: {e}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("ASTRA PHASE 4 - REPOSITORY CLONE")
    logger.info("=" * 70)
    logger.info(f"Repository Directory: {REPO_DIR}")
    logger.info("")

    successful = 0
    failed = 0

    for repo_config in REPOS:
        if clone_repo(repo_config["name"], repo_config["url"]):
            successful += 1
        else:
            failed += 1
        logger.info("")

    logger.info("=" * 70)
    logger.info("CLONE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info("")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
