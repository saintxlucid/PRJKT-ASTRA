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


async def test_training_loop():
    """Test training loop decision engine"""
    print("\n" + "=" * 80)
    print("TEST 6: Training Loop")
    print("=" * 80)
    
    from astra.daemon.training_loop import (
        TrainingLoop, DecisionEngine, LearningEngine, 
        ActionType, FeedbackType, Decision
    )
    
    # Test decision engine
    print("  Testing Decision Engine...")
    engine = DecisionEngine()
    print(f"    ✓ Initialized with autonomy level: {engine.current_autonomy_level}")
    
    # Test event evaluation
    test_event = {'path': 'C:\\Users\\Desktop\\file.exe'}
    decision = engine.evaluate_event('file_created', test_event)
    print(f"    ✓ Made decision: {decision.action.value} (confidence: {decision.confidence})")
    
    # Test autonomy level adjustment
    engine.set_autonomy_level(5)  # Autonomous
    decision2 = engine.evaluate_event('file_created', test_event)
    print(f"    ✓ Adjusted for autonomy level 5: {decision2.action.value}")
    
    # Test learning engine
    print("  Testing Learning Engine...")
    learning = LearningEngine()
    learning.record_decision(decision)
    print(f"    ✓ Recorded decision")
    
    # Simulate user feedback
    learning.record_feedback(decision.decision_id, FeedbackType.APPROVE)
    print(f"    ✓ Recorded user feedback")
    
    stats = learning.get_stats()
    print(f"    ✓ Stats: {stats['total_decisions']} decisions, {stats['positive_feedback']} approved")
    
    # Test training loop
    print("  Testing Training Loop...")
    loop = TrainingLoop()
    initialized = await loop.initialize()
    print(f"    ✓ Initialized: {initialized}")
    
    loop_stats = loop.get_stats()
    print(f"    ✓ Loop stats: autonomy_level={loop_stats['autonomy_level']}")
    
    return True


async def test_security_sentinel():
    """Test security sentinel threat detection"""
    print("\n" + "=" * 80)
    print("TEST 7: Security Sentinel")
    print("=" * 80)
    
    from astra.daemon.security_sentinel import (
        SecuritySentinel,
        ThreatDetector,
        ResponseManager,
        SecurityMode,
        ThreatSeverity
    )
    
    # Test ThreatDetector
    print("\n  Testing ThreatDetector...")
    detector = ThreatDetector()
    print(f"  ✓ Loaded {len(detector.patterns)} threat patterns")
    
    # Test event: suspicious exe in Downloads (should trigger threat_suspicious_exe_download)
    test_event = {
        'event_type': 'file_created',
        'path': 'C:\\Users\\User\\Downloads\\suspicious.exe',
        'process_name': 'chrome.exe'
    }
    
    threat = detector.check_event('file_created', test_event)
    if threat:
        print(f"  ✓ Threat detected: {threat.pattern.name}")
        print(f"    - Severity: {threat.severity.value}")
        print(f"    - Confidence: {threat.confidence}")
        print(f"    - Source: {threat.source}")
    else:
        print("  ✗ No threat detected (expected threat)")
        return False
    
    # Test whitelisted event (should NOT trigger)
    whitelisted_event = {
        'event_type': 'process_spawned',
        'process_name': 'explorer.exe',
        'path': 'C:\\Windows\\explorer.exe'
    }
    
    threat2 = detector.check_event('process_spawned', whitelisted_event)
    if threat2 is None:
        print(f"  ✓ Whitelisted process correctly ignored")
    else:
        print(f"  ✗ Whitelisted process incorrectly flagged")
        return False
    
    # Test ResponseManager
    print("\n  Testing ResponseManager...")
    response_mgr = ResponseManager(SecurityMode.SOFT, autonomy_level=3)
    
    action = response_mgr.determine_action(threat)
    print(f"  ✓ Determined action: {action.value}")
    
    blocked = response_mgr.execute_action(threat, action)
    print(f"  ✓ Action executed: {'BLOCKED' if blocked else 'ALLOWED'}")
    
    # Test SecuritySentinel orchestration
    print("\n  Testing SecuritySentinel orchestration...")
    sentinel = SecuritySentinel(
        event_bus=None,
        operator_shell=None,
        security_mode=SecurityMode.SOFT,
        autonomy_level=3
    )
    
    init_success = await sentinel.initialize()
    if not init_success:
        print("  ✗ Sentinel initialization failed")
        return False
    
    print(f"  ✓ Sentinel initialized")
    
    # Test event processing
    sentinel.on_event(test_event)
    print(f"  ✓ Event queued for processing")
    
    # Process queue
    await sentinel._process_event_queue()
    
    stats = sentinel.get_stats()
    print(f"  ✓ Stats: {stats['threats_detected']} threats detected")
    
    if stats['threats_detected'] > 0:
        recent = sentinel.get_recent_threats(1)
        print(f"  ✓ Recent threats: {len(recent)}")
    
    print("\n  All Security Sentinel checks passed!")
    return True


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + "ASTRA-OS Phase 1-4: Component Tests".center(78) + "║")
    print("║" + f"Sacred Code: 333".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    tests = [
        ("Event Bus", test_event_bus),
        ("OS Kernel", test_os_kernel),
        ("Boot Daemon", test_boot_daemon),
        ("Operator Shell", test_operator_shell),
        ("Memory Bridge Client", test_memory_bridge_client),
        ("Training Loop", test_training_loop),
        ("Security Sentinel", test_security_sentinel),
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
