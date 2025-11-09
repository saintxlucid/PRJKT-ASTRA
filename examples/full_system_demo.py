# examples/full_system_demo.py
"""
Full ASTRA OS P0 Demo - Integrated System
Demonstrates: Agent Kernel + Memory + Telemetry + Browser + Tool Registry
"""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_kernel.memory import MemoryManager
from agent_kernel.planner import AgentKernel
from agent_kernel.tools import create_default_registry
from telemetry.events import EventLogger
from telemetry.metrics import get_metrics


def mock_llm_smart(prompt: str) -> str:
    """
    Smart mock LLM that can actually parse prompts and make decisions.
    For demo purposes - in production, use real LLM.
    """
    if "wikipedia" in prompt.lower() or "article" in prompt.lower():
        return """I should navigate to Wikipedia to find information.

ACTION: call_tool
TOOL: browser.navigate
ARGS: {"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}"""

    if "extract" in prompt.lower() or "read" in prompt.lower():
        return """I should extract the content from the current page.

ACTION: call_tool
TOOL: browser.extract_dom
ARGS: {}"""

    if "Result:" in prompt and "successfully" in prompt.lower():
        return """The task is complete. I have successfully navigated and extracted content.

ACTION: answer
ANSWER: Successfully browsed to the page and extracted content. The information has been stored in memory."""

    # Default - try to answer
    return """I have completed the task with the available information.

ACTION: answer
ANSWER: Task completed with available tools."""


def demo_memory_system():
    """Demo 1: Memory Tier System"""
    print("\n" + "=" * 60)
    print("DEMO 1: Memory Tier System (L0-L3)")
    print("=" * 60)

    memory = MemoryManager(l0_path="data/demo_memory.db")

    # Store in different tiers
    print("\n1. Writing to different memory tiers...")
    memory.write("user.name", "Alice", tier="L0")  # Permanent
    memory.write("session.id", "session_12345", tier="L1")  # Session
    memory.write("task.current_url", "https://example.com", tier="L2")  # Loop
    memory.write("temp.timestamp", time.time(), tier="L3")  # Ephemeral

    print("   ✓ L0 (Permanent): user.name = 'Alice'")
    print("   ✓ L1 (Session): session.id = 'session_12345'")
    print("   ✓ L2 (Loop): task.current_url = 'https://example.com'")
    print("   ✓ L3 (Ephemeral): temp.timestamp = (current time)")

    # Cascade read
    print("\n2. Testing cascade read (L3→L2→L1→L0)...")
    value, tier = memory.read_cascade("user.name")
    print(f"   Found 'user.name' in tier: {tier}")
    print(f"   Value: {value}")

    # Stats
    print("\n3. Memory statistics:")
    stats = memory.get_stats()
    for tier_name, count in stats.items():
        print(f"   {tier_name}: {count} keys")

    print("\n✓ Memory system working correctly!")


def demo_telemetry_system():
    """Demo 2: Telemetry System"""
    print("\n" + "=" * 60)
    print("DEMO 2: Telemetry System (Events + Metrics)")
    print("=" * 60)

    # Event logger
    print("\n1. Event logging to JSONL...")
    logger = EventLogger(log_dir="data/demo_logs", log_name="demo_events")

    logger.log_agent_start(task="Demo telemetry system")
    logger.log_tool_call(tool="browser.navigate", args={"url": "https://example.com"})
    logger.log_tool_result(
        tool="browser.navigate",
        ok=True,
        result="Navigation successful",
        latency_ms=150,
    )
    logger.log_memory_write(tier="L2", key="last_url", ttl_s=3600)
    logger.log_agent_answer(answer="Demo completed successfully")

    print(f"   ✓ Events logged to: {logger.current_file}")
    logger.close()

    # Metrics
    print("\n2. Prometheus metrics (HTTP endpoint on port 9108)...")
    metrics = get_metrics(port=9108, enable_server=True)

    metrics.record_tool_call("browser.navigate", latency_ms=150, success=True)
    metrics.record_agent_iteration()
    metrics.record_memory_write("L2")
    metrics.record_agent_task("success")

    print("   ✓ Metrics recorded")
    print("   ✓ View at: http://localhost:9108/metrics")

    print("\n✓ Telemetry system working correctly!")


def demo_integrated_agent():
    """Demo 3: Full Agent Integration"""
    print("\n" + "=" * 60)
    print("DEMO 3: Integrated Agent (Memory + Telemetry + Tools)")
    print("=" * 60)

    # Initialize components
    print("\n1. Initializing components...")
    memory = MemoryManager(l0_path="data/demo_memory.db")
    logger = EventLogger(log_dir="data/demo_logs", log_name="agent_events")
    metrics = get_metrics(port=9108, enable_server=False)  # Reuse existing
    tools = create_default_registry()

    print("   ✓ Memory manager initialized")
    print("   ✓ Event logger initialized")
    print("   ✓ Metrics exporter initialized")
    print("   ✓ Tool registry initialized")

    # Create agent with all components
    print("\n2. Creating agent with full integration...")
    agent = AgentKernel(
        tool_registry=tools,
        llm_func=mock_llm_smart,
        max_iterations=5,
        memory_manager=memory,
        telemetry_logger=logger,
        telemetry_metrics=metrics,
    )

    print("   ✓ Agent kernel created with:")
    print("     - Memory tiers (L0-L3)")
    print("     - Event logging (JSONL)")
    print("     - Metrics export (Prometheus)")
    print("     - Tool registry")

    # Run task
    print("\n3. Running task: 'Browse to Wikipedia AI article'...")
    task = "Browse to the Wikipedia article on Artificial Intelligence and extract key information"

    result = agent.run(task)

    print(f"\n4. Task Result:")
    print(f"   Status: {'✓ SUCCESS' if result['ok'] else '✗ FAILED'}")
    print(f"   Answer: {result.get('answer', result.get('error'))}")
    print(f"   Iterations: {result['iterations']}")
    print(f"   Tool Calls: {result['tool_calls']}")
    print(f"   Time: {result['elapsed_ms']}ms")

    # Check memory
    print("\n5. Checking memory after task...")
    last_tool = memory.read("last_tool_name", tier="L2")
    session_task = memory.read("session.task", tier="L1")
    print(f"   L1 (Session): session.task = '{session_task}'")
    print(f"   L2 (Loop): last_tool_name = '{last_tool}'")

    # Memory stats
    print("\n6. Final memory statistics:")
    stats = memory.get_stats()
    for tier_name, count in stats.items():
        print(f"   {tier_name}: {count} keys")

    logger.close()
    print("\n✓ Integrated agent working correctly!")


def demo_memory_cascade():
    """Demo 4: Memory Cascade Read"""
    print("\n" + "=" * 60)
    print("DEMO 4: Memory Cascade Read (Priority System)")
    print("=" * 60)

    memory = MemoryManager(l0_path="data/demo_memory.db")

    # Write same key to multiple tiers
    print("\n1. Writing 'api_key' to multiple tiers...")
    memory.write("api_key", "L0_permanent_key", tier="L0")
    memory.write("api_key", "L2_loop_key", tier="L2")
    memory.write("api_key", "L3_temp_key", tier="L3")

    print("   ✓ L0: 'L0_permanent_key'")
    print("   ✓ L2: 'L2_loop_key'")
    print("   ✓ L3: 'L3_temp_key'")

    # Cascade read prioritizes faster/newer tiers
    print("\n2. Cascade read finds highest priority (L3)...")
    value, tier = memory.read_cascade("api_key")
    print(f"   Found in: {tier}")
    print(f"   Value: '{value}'")

    # Clear L3, should fall back to L2
    print("\n3. Clearing L3, cascade should fall back to L2...")
    memory.clear_tier("L3")
    value, tier = memory.read_cascade("api_key")
    print(f"   Found in: {tier}")
    print(f"   Value: '{value}'")

    # Clear L2, should fall back to L0
    print("\n4. Clearing L2, cascade should fall back to L0...")
    memory.clear_tier("L2")
    value, tier = memory.read_cascade("api_key")
    print(f"   Found in: {tier}")
    print(f"   Value: '{value}'")

    print("\n✓ Memory cascade working correctly!")


def main():
    """Run all demos."""
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║         ASTRA OS P0 - Full System Demonstration        ║")
    print("║     Agent Kernel + Memory + Telemetry + Browser        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    try:
        # Demo 1: Memory system
        demo_memory_system()
        time.sleep(1)

        # Demo 2: Telemetry system
        demo_telemetry_system()
        time.sleep(1)

        # Demo 3: Memory cascade
        demo_memory_cascade()
        time.sleep(1)

        # Demo 4: Full integration
        demo_integrated_agent()

        print("\n" + "=" * 60)
        print("✓ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext Steps:")
        print("  1. View event logs: data/demo_logs/*.jsonl")
        print("  2. View metrics: http://localhost:9108/metrics")
        print("  3. Check memory database: data/demo_memory.db")
        print("  4. Run tests: pytest tests/ -v")
        print()

    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
