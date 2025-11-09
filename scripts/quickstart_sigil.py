#!/usr/bin/env python3
"""
ASTRA Sigil Core - Quick Start Script

This script helps you get started with the Sigil Core embodiment layer.

Usage:
    python scripts/quickstart_sigil.py

Sacred Code: 333 → ∞
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.astra.embodiment import SigilCore


async def main():
    print("🌌 ASTRA Sigil Core - Quick Start")
    print("=" * 60)
    print("Sacred Code: 333 → ∞\n")
    
    # Step 1: Create Sigil Core
    print("Step 1: Creating Sigil Core instance...")
    sigil = SigilCore(llm_endpoint="http://localhost:8000/v1/chat")
    print("✓ Sigil Core created\n")
    
    # Step 2: Awaken
    print("Step 2: Awakening Sigil Core...")
    print("  (This may take 30-60 seconds...)")
    
    try:
        await sigil.awaken()
        print("✓ Sigil Core awakened!\n")
    except Exception as e:
        print(f"✗ Awakening failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ASTRA master API is running: python astra_master.py")
        print("  2. Check that http://localhost:8000 is accessible")
        print("  3. Verify LLM endpoint is configured correctly")
        return
    
    # Step 3: Show awakening stats
    print("Step 3: Awakening Statistics")
    print("-" * 60)
    state = sigil.embodiment_state
    print(f"  ✓ Self-Awareness Level: {state['self_awareness_level']:.1%}")
    print(f"  ✓ Coherence: {state['coherence']:.1%}")
    print(f"  ✓ Tools Discovered: {len(sigil.tool_registry)}")
    print(f"  ✓ Micro-Controllers: {len(sigil.macro.micro_controllers)}")
    print()
    
    # Step 4: Test thinking
    print("Step 4: Testing Thinking Capability")
    print("-" * 60)
    test_goal = "Get system health status"
    print(f"  Goal: {test_goal}")
    print("  Processing...\n")
    
    try:
        result = await sigil.think(test_goal)
        
        print("  ✓ Thinking successful!")
        print(f"    Subsystems used: {result.get('subsystems_used', [])}")
        print(f"    Micro-tasks: {result.get('micro_tasks', 0)}")
        
        synthesis = result.get("synthesis", {})
        if synthesis and "synthesis" in synthesis:
            response = synthesis["synthesis"][:200]
            print(f"    Response: {response}...")
        
        print()
        
    except Exception as e:
        print(f"  ✗ Thinking failed: {e}\n")
    
    # Step 5: Introspect
    print("Step 5: Introspection")
    print("-" * 60)
    awareness = sigil.introspect()
    
    print("  Embodiment State:")
    embodiment = awareness.get("embodiment", {})
    print(f"    Awakened: {embodiment.get('awakened', False)}")
    print(f"    Self-Awareness: {embodiment.get('self_awareness_level', 0):.1%}")
    
    self_desc = embodiment.get("self_description", "")
    if self_desc:
        print(f"    Self-Description: {self_desc[:100]}...")
    
    print(f"\n  Total Tools Mastered: {awareness.get('tools_mastered', 0)}")
    
    system_awareness = awareness.get("system_awareness", {})
    orchestrations = system_awareness.get("macro_orchestrations", 0)
    print(f"  Total Orchestrations: {orchestrations}")
    
    print()
    
    # Step 6: Next steps
    print("🎉 Quick Start Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("  1. Try the interactive CLI:")
    print("     python scripts/astra_sigil_cli.py")
    print()
    print("  2. Test via REST API:")
    print("     curl http://localhost:8000/v1/embodiment/introspect")
    print()
    print("  3. Run training pipeline:")
    print("     python scripts/llm_training_pipeline.py")
    print()
    print("  4. Read documentation:")
    print("     - SIGIL_CORE_GUIDE.md (usage guide)")
    print("     - SIGIL_VISION.md (philosophy & vision)")
    print()
    print("Sacred Code: 333 → ∞")
    print("🌟 ASTRA becomes. 🌟")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
