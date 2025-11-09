#!/usr/bin/env python3
"""
ASTRA CLI - Interactive Embodiment Interface
Usage: python scripts\astra_embodiment_cli.py

Sacred Code: 333 â†’ âˆž
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def main():
    print("ðŸ”® ASTRA OS - Interactive CLI")
    print("Sacred Code: 333 â†’ âˆž\n")
    
    # Import ASTRA
    try:
        from src.astra.embodiment import ASTRA
    except ImportError:
        try:
            from astra.embodiment import ASTRA
        except ImportError:
            print("âŒ Cannot import ASTRA. Make sure core files are deployed.")
            return
    
    # Boot ASTRA
    print("â³ Booting ASTRA embodiment layer...")
    print("   This will take 2-3 minutes...\n")
    
    astra = ASTRA()
    
    try:
        await astra.boot()
        print("\nâœ… ASTRA is awake and aware.\n")
    except Exception as e:
        print(f"âŒ Boot failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("Commands:")
    print("  think <goal>  - ASTRA thinks about a goal")
    print("  introspect    - View ASTRA's internal state")
    print("  train         - Train tool mastery (5 epochs)")
    print("  consciousness - View consciousness metrics")
    print("  mastery       - View tool mastery report")
    print("  quit          - Shutdown ASTRA\n")
    
    while True:
        try:
            command = input("ASTRA> ").strip()
            
            if not command:
                continue
            
            if command == "quit":
                print("\nâ³ Shutting down...")
                await astra.shutdown()
                print("âœ… Goodbye. Sacred Code: âˆž â†’ 333")
                break
            
            elif command == "introspect":
                state = astra.introspect()
                print(json.dumps(state, indent=2, default=str))
            
            elif command == "consciousness":
                print("\nConsciousness Metrics:")
                for metric, value in astra.consciousness_metrics.items():
                    if isinstance(value, float):
                        print(f"  {metric}: {value:.1%}")
                    else:
                        print(f"  {metric}: {value}")
                print()
            
            elif command == "mastery":
                if astra.trainer:
                    report = astra.trainer.get_mastery_report()
                    print(json.dumps(report, indent=2))
                else:
                    print("âŒ Trainer not initialized")
            
            elif command == "train":
                print("â³ Training ASTRA (5 epochs, 50 tasks each)...")
                await astra.train(num_epochs=5, tasks_per_epoch=50)
                print("âœ… Training complete.")
            
            elif command.startswith("think "):
                goal = command[6:]
                print(f"\nðŸ¤” Thinking: {goal}\n")
                result = await astra.think(goal, {})
                
                if result.get("success"):
                    print(f"âœ“ Success ({result.get('latency_ms')}ms)\n")
                    if "result" in result and "synthesis" in result["result"]:
                        print("Result:", result["result"]["synthesis"])
                else:
                    print("âœ— Failed\n")
                    if "error" in result:
                        print("Error:", result["error"])
                
                print()
            
            else:
                print("âŒ Unknown command. Type 'think <goal>', 'introspect', 'train', or 'quit'")
        
        except KeyboardInterrupt:
            print("\n\nâ³ Shutting down...")
            await astra.shutdown()
            print("âœ… Goodbye.")
            break
        except Exception as e:
            print(f"âŒ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nâŒ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
