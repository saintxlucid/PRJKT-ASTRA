#!/usr/bin/env python3
"""
ASTRA Phase 4 - Repository Verification
Verifies cloned repositories for integrity and structure
Date: November 13, 2025
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent.parent
REPO_DIR = BASE_DIR / "phase4_staging" / "repos"
LOGDIR = BASE_DIR / "phase4_staging" / "logs"
OUTPUT_DIR = BASE_DIR / "phase4_staging" / "reports"

LOGDIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGDIR / "repo_verification.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("astra.verify_repos")

# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def verify_git_repo(repo_path: Path) -> Dict[str, Any]:
    """Verify a git repository is valid."""
    try:
        # Check if .git directory exists
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return {"valid": False, "error": "No .git directory found"}

        # Get current HEAD
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return {"valid": False, "error": f"Failed to read HEAD: {result.stderr}"}

        commit_hash = result.stdout.strip()

        # Get remote URL
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=10
        )
        remote_url = result.stdout.strip() if result.returncode == 0 else "unknown"

        return {
            "valid": True,
            "commit_hash": commit_hash,
            "remote_url": remote_url,
        }

    except subprocess.TimeoutExpired:
        return {"valid": False, "error": "Git command timeout"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

def count_files(repo_path: Path, pattern: str) -> int:
    """Count files matching a pattern."""
    try:
        return len(list(repo_path.glob(pattern)))
    except Exception:
        return 0

def analyze_repo_structure(repo_path: Path) -> Dict[str, Any]:
    """Analyze repository structure."""
    return {
        "python_files": count_files(repo_path, "**/*.py"),
        "readme_files": count_files(repo_path, "README*"),
        "requirements_files": count_files(repo_path, "**/requirements*.txt"),
        "setup_files": count_files(repo_path, "setup.py"),
        "pyproject_files": count_files(repo_path, "pyproject.toml"),
        "total_files": len(list(repo_path.glob("**/*"))),
    }

def verify_repository(repo_path: Path) -> Dict[str, Any]:
    """Verify a single repository."""
    repo_name = repo_path.name

    logger.info(f"Verifying: {repo_name}")

    result = {
        "name": repo_name,
        "path": str(repo_path),
        "exists": repo_path.exists(),
        "is_directory": repo_path.is_dir(),
    }

    if not repo_path.exists():
        result["status"] = "NOT_FOUND"
        logger.error(f"  Repository not found: {repo_path}")
        return result

    # Verify git
    git_info = verify_git_repo(repo_path)
    result["git"] = git_info

    if not git_info.get("valid"):
        result["status"] = "INVALID_GIT"
        logger.error(f"  Invalid git repository: {git_info.get('error')}")
        return result

    # Analyze structure
    structure = analyze_repo_structure(repo_path)
    result["structure"] = structure

    result["status"] = "VERIFIED"
    logger.info(f"  Status: VERIFIED")
    logger.info(f"  Commit: {git_info.get('commit_hash', 'unknown')[:8]}...")
    logger.info(f"  Python files: {structure['python_files']}")
    logger.info(f"  Total files: {structure['total_files']}")

    return result

# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("ASTRA PHASE 4 - REPOSITORY VERIFICATION")
    logger.info("=" * 70)
    logger.info(f"Repository Directory: {REPO_DIR}")
    logger.info("")

    # Get list of repositories
    if not REPO_DIR.exists():
        logger.error(f"Repository directory not found: {REPO_DIR}")
        return 1

    repos = sorted([d for d in REPO_DIR.iterdir() if d.is_dir()])
    if not repos:
        logger.warning("No repositories found")
        return 1

    logger.info(f"Found {len(repos)} repositories")
    logger.info("")

    # Verify each repository
    results = []
    verified = 0
    failed = 0

    for repo_path in repos:
        verification = verify_repository(repo_path)
        results.append(verification)

        if verification.get("status") == "VERIFIED":
            verified += 1
        else:
            failed += 1

        logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("VERIFICATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Verified: {verified}/{len(repos)}")
    logger.info(f"Failed: {failed}/{len(repos)}")
    logger.info("")

    # Save results
    output_file = OUTPUT_DIR / "repo_verification_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": str(Path.cwd()),
            "total_repos": len(repos),
            "verified": verified,
            "failed": failed,
            "results": results,
        }, f, indent=2)

    logger.info(f"Report saved to: {output_file}")
    logger.info("")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
