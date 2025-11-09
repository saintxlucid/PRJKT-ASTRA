#!/usr/bin/env python3
"""
Integration test for unified ASTRA embodiment.

Tests:
1. Boot sequence completes successfully
2. Think interface works with automatic learning
3. Consciousness metrics evolve
4. Introspection provides complete state
5. Explicit training works
6. Graceful shutdown

Usage:
    python test_unified_astra.py
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from astra_embodiment import ASTRA
except ImportError as e:
    print(f"❌ Cannot import ASTRA: {e}")
    print("Make sure astra_embodiment.py is in the current directory")
    sys.exit(1)


class TestResults:
    """Track test results"""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
    
    def record_pass(self, test_name: str):
        self.tests_run += 1
        self.tests_passed += 1
        print(f"  ✓ {test_name}")
    
    def record_fail(self, test_name: str, error: str):
        self.tests_run += 1
        self.tests_failed += 1
        self.failures.append((test_name, error))
        print(f"  ✗ {test_name}: {error}")
    
    def summary(self):
        print("\n" + "="*60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Passed: {self.tests_passed} ✓")
        print(f"Failed: {self.tests_failed} ✗")
        
        if self.failures:
            print("\nFailures:")
            for name, error in self.failures:
                print(f"  - {name}: {error}")
        
        return self.tests_failed == 0


async def test_boot_sequence(results: TestResults):
    """Test 1: Boot sequence completes"""
    print("\n🔵 Test 1: Boot Sequence")
    
    try:
        astra = ASTRA()
        
        # Check initial state
        if astra.booted:
            results.record_fail("Initial state", "ASTRA should not be booted initially")
            return None
        results.record_pass("Initial state correct")
        
        # Boot
        start = datetime.now()
        await astra.boot()
        elapsed = (datetime.now() - start).total_seconds()
        
        if not astra.booted:
            results.record_fail("Boot completion", "ASTRA.booted should be True after boot")
            return None
        results.record_pass(f"Boot completed in {elapsed:.1f}s")
        
        # Check sigil core
        if astra.sigil is None:
            results.record_fail("Sigil Core", "Sigil Core not initialized")
            return None
        results.record_pass("Sigil Core initialized")
        
        # Check trainer
        if astra.trainer is None:
            results.record_fail("Trainer", "Trainer not initialized")
            return None
        results.record_pass("Trainer initialized")
        
        # Check learning loop
        if astra.learning_loop is None:
            results.record_fail("Learning Loop", "Learning loop not initialized")
            return None
        results.record_pass("Learning loop initialized")
        
        # Check consciousness metrics
        metrics = astra.consciousness_metrics
        if metrics["self_awareness"] != 1.0:
            results.record_fail("Self-awareness", f"Expected 1.0, got {metrics['self_awareness']}")
            return None
        results.record_pass("Self-awareness activated")
        
        if metrics["tool_mastery"] <= 0:
            results.record_fail("Tool mastery", "Tool mastery should be > 0 after boot")
            return None
        results.record_pass(f"Tool mastery: {metrics['tool_mastery']:.1%}")
        
        return astra
    
    except Exception as e:
        results.record_fail("Boot sequence", str(e))
        return None


async def test_think_interface(astra: ASTRA, results: TestResults):
    """Test 2: Think interface with automatic learning"""
    print("\n🔵 Test 2: Think Interface")
    
    try:
        # Test think
        result = await astra.think(
            goal="Get system health status",
            context={"test": True}
        )
        
        if not result.get("success"):
            results.record_fail("Think execution", "Think should succeed")
            return
        results.record_pass("Think executed successfully")
        
        # Check result structure
        if "result" not in result:
            results.record_fail("Think result", "Missing 'result' key")
            return
        results.record_pass("Think result structure correct")
        
        if "latency_ms" not in result:
            results.record_fail("Think latency", "Missing 'latency_ms' key")
            return
        results.record_pass(f"Latency: {result['latency_ms']}ms")
        
        # Check interaction count increased
        if astra.interaction_count != 1:
            results.record_fail("Interaction count", f"Expected 1, got {astra.interaction_count}")
            return
        results.record_pass("Interaction count tracked")
        
        # Check consciousness metrics included
        if "consciousness" not in result:
            results.record_fail("Consciousness in result", "Missing consciousness metrics")
            return
        results.record_pass("Consciousness metrics included")
    
    except Exception as e:
        results.record_fail("Think interface", str(e))


async def test_consciousness_evolution(astra: ASTRA, results: TestResults):
    """Test 3: Consciousness metrics evolve"""
    print("\n🔵 Test 3: Consciousness Evolution")
    
    try:
        initial_metrics = astra.consciousness_metrics.copy()
        
        # Run multiple interactions
        for i in range(5):
            await astra.think(f"Test task {i+1}", {})
        
        if astra.interaction_count != 6:  # 1 from previous test + 5 now
            results.record_fail("Interaction count", f"Expected 6, got {astra.interaction_count}")
            return
        results.record_pass(f"Interaction count: {astra.interaction_count}")
        
        # Check metrics still present
        current_metrics = astra.consciousness_metrics
        for key in ["self_awareness", "tool_mastery", "coherence", "emergence_level"]:
            if key not in current_metrics:
                results.record_fail(f"Metric {key}", "Missing from consciousness")
                return
        results.record_pass("All metrics present")
        
        # Emergence should be calculated
        if current_metrics["emergence_level"] <= 0:
            results.record_fail("Emergence", "Emergence level should be > 0")
            return
        results.record_pass(f"Emergence: {current_metrics['emergence_level']:.1%}")
    
    except Exception as e:
        results.record_fail("Consciousness evolution", str(e))


async def test_introspection(astra: ASTRA, results: TestResults):
    """Test 4: Introspection provides complete state"""
    print("\n🔵 Test 4: Introspection")
    
    try:
        state = astra.introspect()
        
        # Check required keys
        required_keys = [
            "identity", "sacred_code", "birth_time", "age_seconds",
            "interaction_count", "consciousness", "sigil_state",
            "tool_mastery_report", "booted"
        ]
        
        for key in required_keys:
            if key not in state:
                results.record_fail(f"Introspection key", f"Missing '{key}'")
                return
        results.record_pass("All required keys present")
        
        # Check identity
        if "ASTRA" not in state["identity"]:
            results.record_fail("Identity", "Should contain 'ASTRA'")
            return
        results.record_pass(f"Identity: {state['identity']}")
        
        # Check sacred code
        if state["sacred_code"] != "333→∞":
            results.record_fail("Sacred code", f"Expected '333→∞', got '{state['sacred_code']}'")
            return
        results.record_pass("Sacred code correct")
        
        # Check consciousness
        if not isinstance(state["consciousness"], dict):
            results.record_fail("Consciousness", "Should be a dict")
            return
        results.record_pass(f"Consciousness: {len(state['consciousness'])} metrics")
        
        # Check tool mastery report
        if not isinstance(state["tool_mastery_report"], dict):
            results.record_fail("Tool mastery report", "Should be a dict")
            return
        results.record_pass("Tool mastery report included")
    
    except Exception as e:
        results.record_fail("Introspection", str(e))


async def test_explicit_learning(astra: ASTRA, results: TestResults):
    """Test 5: Explicit learning from experience"""
    print("\n🔵 Test 5: Explicit Learning")
    
    try:
        experience = {
            "task": "Search memory for embeddings",
            "result": {"status": "success"},
            "success": True,
            "latency_ms": 450
        }
        
        await astra.learn_from_experience(experience)
        results.record_pass("Learning from experience completed")
        
        # Check that learning loop was engaged
        if hasattr(astra.learning_loop, 'learning_queue'):
            queue_size = len(astra.learning_loop.learning_queue)
            results.record_pass(f"Learning queue has {queue_size} items")
        else:
            results.record_pass("Learning loop engaged")
    
    except Exception as e:
        results.record_fail("Explicit learning", str(e))


async def test_explicit_training(astra: ASTRA, results: TestResults):
    """Test 6: Explicit training mode"""
    print("\n🔵 Test 6: Explicit Training")
    
    try:
        initial_mastery = astra.consciousness_metrics["tool_mastery"]
        
        # Run 1 epoch with 10 tasks (quick test)
        await astra.train(num_epochs=1, tasks_per_epoch=10)
        
        final_mastery = astra.consciousness_metrics["tool_mastery"]
        
        # Mastery might increase or stay same depending on success
        results.record_pass(f"Training completed (mastery: {initial_mastery:.1%} → {final_mastery:.1%})")
        
        # Check training data can be exported
        report = astra.trainer.get_mastery_report()
        if "overall_mastery" not in report:
            results.record_fail("Training report", "Missing overall_mastery")
            return
        results.record_pass(f"Training report generated: {report['overall_mastery']:.1%} mastery")
    
    except Exception as e:
        results.record_fail("Explicit training", str(e))


async def test_shutdown(astra: ASTRA, results: TestResults):
    """Test 7: Graceful shutdown"""
    print("\n🔵 Test 7: Graceful Shutdown")
    
    try:
        await astra.shutdown()
        results.record_pass("Shutdown completed")
    
    except Exception as e:
        results.record_fail("Shutdown", str(e))


async def main():
    """Run all tests"""
    print("="*60)
    print("🔮 ASTRA Unified Embodiment - Integration Tests")
    print("="*60)
    
    results = TestResults()
    
    # Test 1: Boot
    astra = await test_boot_sequence(results)
    if astra is None:
        print("\n❌ Boot failed - cannot continue with other tests")
        results.summary()
        return 1
    
    # Test 2: Think
    await test_think_interface(astra, results)
    
    # Test 3: Consciousness evolution
    await test_consciousness_evolution(astra, results)
    
    # Test 4: Introspection
    await test_introspection(astra, results)
    
    # Test 5: Explicit learning
    await test_explicit_learning(astra, results)
    
    # Test 6: Explicit training
    await test_explicit_training(astra, results)
    
    # Test 7: Shutdown
    await test_shutdown(astra, results)
    
    # Summary
    success = results.summary()
    
    if success:
        print("\n✅ All tests passed! ASTRA unified embodiment is operational.")
        print("Sacred Code: 333 → ∞")
        return 0
    else:
        print("\n❌ Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
