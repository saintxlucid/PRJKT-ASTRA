"""
Demonstration: CHAT OS integration with ASTRA Agent Kernel

This script shows how to use CHAT OS plan execution within the agent kernel's
ReAct loop. The executor is now fully integrated as a tool that can be called
by the agent during task execution.
"""

from agent_kernel.memory import MemoryManager
from agent_kernel.planner import create_agent
from agent_kernel.tools import ToolRegistry
from chat_os.agent_integration import register_chat_os_tools
from chat_os.executor import register_intent


# Register test handlers for demo
@register_intent("test.echo")
def handle_test_echo(step, ctx):
    """Test handler that echoes input."""
    return step.args.get("message", "no message")


@register_intent("test.increment")
def handle_test_increment(step, ctx):
    """Test handler that increments a counter."""
    value = step.args.get("value", 0)
    return value + 1


def demo_basic_integration():
    """Demo 1: Basic plan execution via tool registry."""
    print("=" * 60)
    print("DEMO 1: Basic Plan Execution via Tool Registry")
    print("=" * 60)

    # Create tool registry and register CHAT OS tools
    tool_registry = ToolRegistry()
    register_chat_os_tools(tool_registry)

    # List available tools
    tools = tool_registry.list_tools()
    print(f"\nRegistered tools: {[t['name'] for t in tools]}")

    # Create a simple test plan
    plan = {
        "id": "demo_plan_001",
        "meta": {
            "description": "Demo plan with test intents",
            "author": "demo",
            "max_time_ms": 5000,
        },
        "steps": [
            {"intent": "test.echo", "args": {"message": "Hello from CHAT OS!"}},
            {"intent": "test.increment", "args": {"value": 41}},
        ],
    }

    # Execute plan with auto-token (bypasses manual token generation)
    result = tool_registry.call_with_auto_token(
        name="plan.execute",
        args={"plan": plan, "admin_mode": True},
        ttl_s=30,
        budget_ms=10000,
    )

    print(f"\n✅ Plan executed: {result['ok']}")
    if result["ok"]:
        print(f"Steps completed: {result['result']['steps_completed']}")
        print(f"Outputs: {result['result']['outputs']}")
        print(f"Elapsed: {result['elapsed_ms']}ms")
    else:
        print(f"Error: {result['error']}")


def demo_memory_integration():
    """Demo 2: Load plan from memory and execute."""
    print("\n" + "=" * 60)
    print("DEMO 2: Load Plan from Memory")
    print("=" * 60)

    # Note: plan.load tool needs memory instance passed as arg,
    # but MemoryManager is not JSON serializable for token hashing.
    # In practice, the agent would have access to its own memory manager.
    # For this demo, we'll show a simpler workflow.

    memory = MemoryManager()
    tool_registry = ToolRegistry()
    register_chat_os_tools(tool_registry)

    # Store a plan in memory
    stored_plan = {
        "id": "workflow_research",
        "meta": {
            "description": "Research workflow",
            "author": "ASTRA",
            "max_time_ms": 60000,
        },
        "steps": [
            {"intent": "test.echo", "args": {"message": "Starting research..."}},
            {"intent": "test.increment", "args": {"value": 0}},
            {"intent": "test.echo", "args": {"message": "Research complete!"}},
        ],
    }
    memory.write("plans.research_workflow", stored_plan, tier="L2")
    print("\n📝 Stored plan in memory: plans.research_workflow")

    # In a real scenario, the agent would use plan.load tool internally
    # For demo, we'll directly retrieve and execute
    loaded_plan = memory.read("plans.research_workflow", tier="L2")
    print(f"✅ Retrieved plan: {loaded_plan['id']}")

    # Execute the loaded plan
    exec_result = tool_registry.call_with_auto_token(
        name="plan.execute",
        args={"plan": loaded_plan, "admin_mode": True},
        ttl_s=30,
        budget_ms=60000,
    )

    if exec_result["ok"]:
        print("✅ Executed loaded plan")
        print(f"Steps completed: {exec_result['result']['steps_completed']}")
        print(f"Final outputs: {exec_result['result']['outputs']}")


def demo_variable_passing():
    """Demo 3: Variable passing between steps."""
    print("\n" + "=" * 60)
    print("DEMO 3: Variable Passing Between Steps")
    print("=" * 60)

    tool_registry = ToolRegistry()
    register_chat_os_tools(tool_registry)

    # Plan with variable interpolation
    plan = {
        "id": "variable_demo",
        "meta": {
            "description": "Demo variable passing",
            "author": "demo",
            "max_time_ms": 5000,
        },
        "steps": [
            # Step 0: Echo initial input
            {"intent": "test.echo", "args": {"message": "{{start_message}}"}},
            # Step 1: Increment initial value
            {"intent": "test.increment", "args": {"value": "{{initial_count}}"}},
            # Step 2: Increment result from step 1
            {"intent": "test.increment", "args": {"value": "{{step.1}}"}},
            # Step 3: Echo step 2 result
            {"intent": "test.echo", "args": {"message": "Final count: {{step.2}}"}},
        ],
    }

    # Execute with initial variables
    result = tool_registry.call_with_auto_token(
        name="plan.execute",
        args={
            "plan": plan,
            "variables": {
                "start_message": "Beginning pipeline...",
                "initial_count": 10,
            },
            "admin_mode": True,
        },
        ttl_s=30,
        budget_ms=10000,
    )

    if result["ok"]:
        print("\n✅ Variable pipeline executed")
        for i, step in enumerate(result["steps"]):
            print(f"  Step {i} ({step['intent']}): {step['output']}")
        print(f"\nFinal variables: {result['result']['final_variables']}")


def demo_agent_kernel_integration():
    """Demo 4: Full agent kernel integration (conceptual)."""
    print("\n" + "=" * 60)
    print("DEMO 4: Agent Kernel Integration (Conceptual)")
    print("=" * 60)

    # Create agent with CHAT OS tools registered
    agent = create_agent()
    register_chat_os_tools(agent.tools)

    print(f"\n🤖 Agent created with {len(agent.tools.list_tools())} tools")
    print("Tools available to agent:")
    for tool in agent.tools.list_tools():
        print(f"  - {tool['name']} ({tool['scope']}): {tool['description'][:60]}...")

    print("\n📝 Agent can now use plan.execute in its ReAct loop:")
    print("   Human: 'Execute my research workflow plan'")
    print("   Agent: CALL_TOOL: plan.load {key: 'plans.research_workflow', memory: ...}")
    print("   [plan loaded successfully]")
    print("   Agent: CALL_TOOL: plan.execute {plan: {...}}")
    print("   [plan executes browser→compose→memory steps]")
    print("   Agent: ANSWER: Research complete. Results saved to memory.")


if __name__ == "__main__":
    # Run all demos
    demo_basic_integration()
    demo_memory_integration()
    demo_variable_passing()
    demo_agent_kernel_integration()

    print("\n" + "=" * 60)
    print("✅ All demos completed successfully!")
    print("=" * 60)
