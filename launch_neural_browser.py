#!/usr/bin/env python3
"""
ASTRA 3D Neural Browser Launcher
Launch the memory visualization interface

Usage:
    python launch_neural_browser.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...\n")
    
    missing = []
    
    # Check PySide6
    try:
        import PySide6
        print("   ✓ PySide6 installed")
    except ImportError:
        print("   ❌ PySide6 not found")
        missing.append("PySide6")
    
    # Check numpy
    try:
        import numpy
        print("   ✓ NumPy installed")
    except ImportError:
        print("   ❌ NumPy not found")
        missing.append("numpy")
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("\n✓ All dependencies satisfied\n")
    return True


def print_banner():
    """Print startup banner"""
    print("\n" + "="*60)
    print("🧠 ASTRA 3D NEURAL BROWSER")
    print("Memory Graph Visualization System")
    print("="*60)
    print("\nSacred Code: 333 ∞")
    print("Built by Saint Lucid\n")


def main():
    """Launch the neural browser"""
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Import and launch
    try:
        print("🚀 Launching neural browser...")
        from src.astra.visualization.neural_browser_app import main as browser_main
        browser_main()
    except Exception as e:
        print(f"\n❌ Failed to launch: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
