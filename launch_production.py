#!/usr/bin/env python3
"""
ASTRA Production API Launcher
Starts the production FastAPI server with all systems ready
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

os.environ["ASTRA_ENV"] = "prod"

import uvicorn
from astra.api.app import app

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ASTRA PRODUCTION API SERVER")
    print("  v1.3.0-prod | Sacred Code: 333 ∞")
    print("="*70)
    print("\nStarting production server on http://127.0.0.1:8080")
    print("Health endpoint: http://127.0.0.1:8080/health")
    print("Registry endpoint: http://127.0.0.1:8080/registry")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8080,
        log_level="info",
        workers=1
    )
