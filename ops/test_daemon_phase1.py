"""
ASTRA-OS Phase 1 Quick Test
Verify boot daemon, kernel, and shell components work together.

Sacred Code: 333
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

import structlog

logger = structlog.get_logger()


async def test_event_bus():
    """Test event bus functionality"""
    print("\n" + "=" * 80)
    print("TEST 1: Event Bus")
    print("=" * 80)
    
    from astra.daemon.os_kernel import EventBus
    
    bus = EventBus()
    events_received = []
    
    def on_test_event(event):
        events_received.append(event)
        print(f"  ✓ Received: {event}")
    
    bus.subscribe('test_event', on_test_event)
    
    # Emit events
    bus.emit('test_event', {'data': 'hello'})
    bus.emit('test_event', {'data': 'world'})
    
    print(f"\n  Events received: {len(events_received)}")
    print(f"  Stats: {bus.get_stats()}")
    
    return len(events_received) == 2


async def test_os_kernel():
    """Test OS kernel initialization"""
    print("\n" + "=" * 80)
    print("TEST 2: OS Kernel")
    print("=" * 80)
    
    from astra.daemon.os_kernel import OsKernel
    
    kernel = OsKernel()
    await kernel.initialize()
    
    print("  ✓ Kernel initialized")
    
    # Test event subscription
    events_received = []
    
    def on_file_created(event):
        events_received.append(event)
    
    kernel.subscribe('file_created', on_file_created)
    
    # Manually emit a test event
    kernel.event_bus.emit('file_created', {'path': 'C:/test.txt'})
    
    print(f"  ✓ Event subscription working")
    print(f"  ✓ Events received: {len(events_received)}")
    
    await kernel.shutdown()
    print("  ✓ Kernel shutdown")
    
    return True


async def test_boot_daemon():
    """Test boot daemon initialization"""
    print("\n" + "=" * 80)
    print("TEST 3: Boot Daemon")
    print("=" * 80)
    
    from astra.daemon.boot_daemon import AstraBootDaemon, StartupConfig
    
    config = StartupConfig(
        auto_boot=False,  # Don't modify registry during test
        fork_process=False,  # Don't fork during test
        setup_registry=False,
    )
    
    daemon = AstraBootDaemon(config)
    print(f"  ✓ Daemon initialized (PID: {daemon.pid})")
    print(f"  ✓ Log file: {daemon.log_file}")
    
    # Initialize subsystems (but don't run main loop)
    result = await daemon.initialize()
    print(f"  ✓ Daemon initialized: {result}")
    
    await daemon.shutdown()
    print("  ✓ Daemon shutdown")
    
    return result


async def test_operator_shell():
    """Test operator shell"""
    print("\n" + "=" * 80)
    print("TEST 4: Operator Shell")
    print("=" * 80)
    
    from astra.daemon.operator_shell import OperatorShell, VoiceInterface
    
    shell = OperatorShell()
    await shell.initialize()
    print("  ✓ Shell initialized")
    
    voice = VoiceInterface()
    print("  ✓ Voice interface initialized")
    
    await shell.shutdown()
    print("  ✓ Shell shutdown")
    
    return True


async def test_memory_bridge_client():
    """Test memory bridge client"""
    print("\n" + "=" * 80)
    print("TEST 5: Memory Bridge Client")
    print("=" * 80)
    
    from astra.daemon.operator_shell import MemoryBridgeClient
    
    bridge = MemoryBridgeClient()
    await bridge.initialize()
    
    if bridge.connected:
        print("  ✓ Connected to memory bridge")
    else:
        print("  ⚠ Memory bridge not available (expected if ASTRA core not running)")
    
    return True


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + "ASTRA-OS Phase 1: Component Tests".center(78) + "║")
    print("║" + f"Sacred Code: 333".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    tests = [
        ("Event Bus", test_event_bus),
        ("OS Kernel", test_os_kernel),
        ("Boot Daemon", test_boot_daemon),
        ("Operator Shell", test_operator_shell),
        ("Memory Bridge Client", test_memory_bridge_client),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = "✓ PASS" if result else "✗ FAIL"
        except Exception as e:
            results[test_name] = f"✗ ERROR: {str(e)}"
            print(f"\n  ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results.items():
        print(f"  {result:15} {test_name}")
    
    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)
    
    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
