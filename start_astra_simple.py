"""
Simplified ASTRA Boot Script
Handles common import issues and provides clear error messages
"""

import sys
from pathlib import Path

# Ensure src is in path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

print("\n" + "="*60)
print("🌌 ASTRA 3.0 - SIMPLIFIED BOOT")
print("="*60)
print(f"\nProject Root: {project_root}")
print(f"Python Path Added: {src_path}\n")

# Try to import and start ASTRA
try:
    print("Loading ASTRA Master...")
    import astra_master
    
    print("✅ ASTRA Master loaded successfully")
    print("\nStarting FastAPI server...")
    print("Access at: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    print("="*60 + "\n")
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run(
        "astra_master:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
    
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Check that you're in the project root directory")
    print("  2. Verify src/astra/ directory exists")
    print("  3. Run: pip install -r requirements.txt")
    print(f"\nCurrent directory: {Path.cwd()}")
    print(f"Python version: {sys.version}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\nError type: {type(e).__name__}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
