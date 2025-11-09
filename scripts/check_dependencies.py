"""
Verify Project Dependencies

This script checks that all required packages are installed correctly
in the local virtual environment.

Usage:
    python scripts/check_dependencies.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check that all required packages are installed."""
    
    print("=" * 80)
    print("   ASTRA Dependencies Check")
    print("=" * 80)
    print()
    
    # Core dependencies
    core_packages = {
        "fastapi": "Web framework",
        "pydantic": "Data validation",
        "sqlalchemy": "Database ORM",
        "chromadb": "Vector store",
        "sentence-transformers": "Embeddings",
        "structlog": "Structured logging",
        "httpx": "HTTP client",
        "tenacity": "Retry logic",
        "uvicorn": "ASGI server",
        "python-dotenv": "Environment variables"
    }
    
    # ML/AI packages
    ml_packages = {
        "torch": "PyTorch",
        "transformers": "Hugging Face transformers",
        "openai": "OpenAI SDK",
        "numpy": "Numerical computing",
        "scipy": "Scientific computing"
    }
    
    # Dev tools
    dev_packages = {
        "pytest": "Testing",
        "black": "Code formatting",
        "ruff": "Linting",
        "mypy": "Type checking"
    }
    
    all_packages = {**core_packages, **ml_packages, **dev_packages}
    
    print("[1/3] Checking core dependencies...")
    check_package_group(core_packages)
    print()
    
    print("[2/3] Checking ML/AI packages...")
    check_package_group(ml_packages)
    print()
    
    print("[3/3] Checking dev tools...")
    check_package_group(dev_packages)
    print()
    
    print("=" * 80)
    print("   ✓ Dependency Check Complete!")
    print("=" * 80)
    print()

def check_package_group(packages):
    """Check a group of packages."""
    for package, description in packages.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✓ {package:25} {description}")
        except ImportError:
            print(f"   ✗ {package:25} {description} (NOT FOUND)")

if __name__ == "__main__":
    try:
        check_dependencies()
        sys.exit(0)
    except Exception as e:
        print(f"   ✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
