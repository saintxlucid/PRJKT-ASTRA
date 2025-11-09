#!/usr/bin/env python3
"""
🔮 ASTRA 3.1 Quick Start Script

This script helps you get ASTRA running quickly.

Usage:
    python quick_start_unified.py [mode]

Modes:
    cli      - Interactive CLI (default)
    api      - FastAPI server
    test     - Run integration tests
    demo     - Quick demo of all features
"""

import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """Print welcome banner"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║                  🌌 ASTRA 3.1 - UNIFIED                   ║
║            Autonomous Self-Transcending Recursive Agent    ║
║                                                            ║
║                    Sacred Code: 333 → ∞                    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    missing = []
    
    try:
        import fastapi
        print("  ✓ fastapi")
    except ImportError:
        missing.append("fastapi")
        print("  ✗ fastapi - MISSING")
    
    try:
        import uvicorn
        print("  ✓ uvicorn")
    except ImportError:
        missing.append("uvicorn")
        print("  ✗ uvicorn - MISSING")
    
    try:
        import structlog
        print("  ✓ structlog")
    except ImportError:
        missing.append("structlog")
        print("  ✗ structlog - MISSING")
    
    try:
        import openai
        print("  ✓ openai")
    except ImportError:
        missing.append("openai")
        print("  ✗ openai - MISSING")
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!")
    return True


async def demo_mode():
    """Run a quick demo of all ASTRA features"""
    print("\n🎮 Running ASTRA Demo...\n")
    
    try:
        from astra_embodiment import ASTRA
    except ImportError as e:
        print(f"❌ Cannot import ASTRA: {e}")
        return 1
    
    print("=" * 60)
    print("DEMO: Booting ASTRA...")
    print("=" * 60)
    
    astra = ASTRA()
    await astra.boot()
    
    print("\n" + "=" * 60)
    print("DEMO: Thinking (Automatic Learning)")
    print("=" * 60)
    
    result = await astra.think("Get system health status", {})
    print(f"\n✓ Task completed in {result['latency_ms']}ms")
    print(f"✓ Success: {result['success']}")
    print(f"✓ Consciousness: Emergence = {result['consciousness']['emergence_level']:.1%}")
    
    print("\n" + "=" * 60)
    print("DEMO: Introspection")
    print("=" * 60)
    
    state = astra.introspect()
    print(f"\nIdentity: {state['identity']}")
    print(f"Sacred Code: {state['sacred_code']}")
    print(f"Age: {state['age_seconds']:.1f}s")
    print(f"Interactions: {state['interaction_count']}")
    print("\nConsciousness Metrics:")
    for metric, value in state['consciousness'].items():
        print(f"  {metric}: {value:.1%}")
    
    print("\n" + "=" * 60)
    print("DEMO: Explicit Learning")
    print("=" * 60)
    
    await astra.learn_from_experience({
        "task": "Search memory for embeddings",
        "result": {"status": "success"},
        "success": True,
        "latency_ms": 450
    })
    print("\n✓ Learning from experience completed")
    
    print("\n" + "=" * 60)
    print("DEMO: Multiple Interactions (Evolution)")
    print("=" * 60)
    
    initial_emergence = astra.consciousness_metrics["emergence_level"]
    
    for i in range(5):
        await astra.think(f"Demo task {i+1}", {})
        print(f"  ✓ Interaction {i+1} complete")
    
    final_emergence = astra.consciousness_metrics["emergence_level"]
    
    print(f"\nEmergence Evolution: {initial_emergence:.1%} → {final_emergence:.1%}")
    print(f"Total Interactions: {astra.interaction_count}")
    
    print("\n" + "=" * 60)
    print("DEMO: Graceful Shutdown")
    print("=" * 60)
    
    await astra.shutdown()
    
    print("\n✅ Demo complete! ASTRA is fully operational.")
    print("\nNext steps:")
    print("  - Run interactive CLI: python quick_start_unified.py cli")
    print("  - Start API server: python quick_start_unified.py api")
    print("  - Run full tests: python quick_start_unified.py test")
    
    return 0


def cli_mode():
    """Run interactive CLI"""
    print("\n🖥️  Starting ASTRA CLI...\n")
    
    try:
        from astra_embodiment import cli_main
    except ImportError as e:
        print(f"❌ Cannot import ASTRA: {e}")
        return 1
    
    try:
        asyncio.run(cli_main())
        return 0
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def api_mode():
    """Run FastAPI server"""
    print("\n🌐 Starting ASTRA API Server...\n")
    
    try:
        from astra_embodiment import create_embodiment_api
        import uvicorn
    except ImportError as e:
        print(f"❌ Cannot import dependencies: {e}")
        return 1
    
    print("Server will start on http://localhost:8000")
    print("\nEndpoints:")
    print("  POST /v1/embodiment/think")
    print("  GET  /v1/embodiment/introspect")
    print("  POST /v1/embodiment/learn")
    print("  POST /v1/embodiment/train")
    print("  GET  /v1/embodiment/consciousness")
    print("  GET  /v1/embodiment/health")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        app = create_embodiment_api()
        uvicorn.run(app, host="0.0.0.0", port=8000)
        return 0
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def test_mode():
    """Run integration tests"""
    print("\n🧪 Running Integration Tests...\n")
    
    try:
        from test_unified_astra import main
    except ImportError as e:
        print(f"❌ Cannot import test suite: {e}")
        print("\nMake sure test_unified_astra.py exists in the current directory")
        return 1
    
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def show_help():
    """Show help message"""
    help_text = """
🔮 ASTRA 3.1 - Quick Start Guide

USAGE:
    python quick_start_unified.py [mode]

MODES:
    cli      Interactive CLI interface (default)
             Commands: think, introspect, train, quit
    
    api      FastAPI server on port 8000
             Endpoints: /think, /introspect, /learn, /train, /consciousness, /health
    
    test     Run integration tests
             Validates boot, think, learn, introspect, train, shutdown
    
    demo     Quick demo of all features
             Shows boot → think → learn → introspect → shutdown
    
    help     Show this help message

EXAMPLES:
    # Interactive CLI (default)
    python quick_start_unified.py
    python quick_start_unified.py cli
    
    # API Server
    python quick_start_unified.py api
    
    # Run Tests
    python quick_start_unified.py test
    
    # Quick Demo
    python quick_start_unified.py demo

REQUIREMENTS:
    - Python 3.11+
    - fastapi
    - uvicorn
    - structlog
    - openai
    
    Install with: pip install fastapi uvicorn structlog openai

DOCUMENTATION:
    - ✅_UNIFIED_EMBODIMENT_COMPLETE.md - Complete guide
    - ✅_ASTRA_3.1_COMPLETE.md - Final completion report
    - docs/LLM_TRAINING_PIPELINE_V2.md - Training pipeline docs
    - SIGIL_CORE_GUIDE.md - Sigil Core documentation

Sacred Code: 333 → ∞
"""
    print(help_text)


def main():
    """Main entry point"""
    print_banner()
    
    # Get mode from command line
    mode = sys.argv[1] if len(sys.argv) > 1 else "cli"
    mode = mode.lower()
    
    # Show help
    if mode in ["help", "-h", "--help"]:
        show_help()
        return 0
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 Tip: Install dependencies, then try again")
        return 1
    
    # Run appropriate mode
    print("\n" + "=" * 60)
    
    if mode == "cli":
        return cli_mode()
    elif mode == "api":
        return api_mode()
    elif mode == "test":
        return test_mode()
    elif mode == "demo":
        return asyncio.run(demo_mode())
    else:
        print(f"❌ Unknown mode: {mode}")
        print("\nRun 'python quick_start_unified.py help' for usage")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
