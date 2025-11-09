# examples/agent_demo.py
"""
Demo of ASTRA OS Agent Kernel with browser integration.
Shows ReAct planning loop with tool execution.
"""
import asyncio
import sys

from agent_kernel.planner import AgentKernel
from agent_kernel.tools import ToolRegistry
from comet_browser.dom.driver import DOMDriver


def create_browser_registry(driver: DOMDriver) -> ToolRegistry:
    """
    Create tool registry with browser tools.

    Args:
        driver: Initialized DOMDriver instance

    Returns:
        ToolRegistry with browser tools
    """
    registry = ToolRegistry()

    # Browser navigation
    async def nav_wrapper(args):
        url = args.get("url")
        if not url:
            return {"ok": False, "error": "Missing 'url' argument"}

        result = await driver.navigate(url)
        if not result["ok"]:
            return result

        # Extract content
        extract_result = await driver.extract_dom(max_tokens=1200)
        return extract_result

    def navigate_sync(args):
        return asyncio.run(nav_wrapper(args))

    registry.register(
        name="browser.navigate",
        func=navigate_sync,
        description="Navigate to URL and extract page content as Markdown",
        scope="action",
        policy="action",
        requires_token=True,
    )

    # Browser click
    async def click_wrapper(args):
        selector = args.get("selector")
        if not selector:
            return {"ok": False, "error": "Missing 'selector' argument"}
        return await driver.click(selector)

    def click_sync(args):
        return asyncio.run(click_wrapper(args))

    registry.register(
        name="browser.click",
        func=click_sync,
        description="Click element by CSS selector",
        scope="action",
        policy="action",
        requires_token=True,
    )

    # Browser type
    async def type_wrapper(args):
        selector = args.get("selector")
        text = args.get("text")
        if not selector or not text:
            return {"ok": False, "error": "Missing 'selector' or 'text' argument"}
        return await driver.type_text(selector, text)

    def type_sync(args):
        return asyncio.run(type_wrapper(args))

    registry.register(
        name="browser.type",
        func=type_sync,
        description="Type text into element by CSS selector",
        scope="action",
        policy="action",
        requires_token=True,
    )

    # Info tools (no token required)
    import time

    registry.register(
        name="info.time",
        func=lambda args: {
            "result": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        },
        description="Get current system time",
        scope="info",
        policy="info",
        requires_token=False,
    )

    return registry


def create_mock_llm():
    """
    Create a mock LLM that simulates planning.

    In production, this would call an actual LLM API.
    """
    iteration = [0]

    def llm_func(prompt):
        iteration[0] += 1

        print(f"\n[LLM Call #{iteration[0]}]")
        print(f"Prompt length: {len(prompt)} chars")

        # Simulate simple planning logic
        if "Navigate to" in prompt or iteration[0] == 1:
            # First call: navigate to example.com
            return "CALL_TOOL: browser.navigate {\"url\": \"https://example.com\"}"
        elif iteration[0] == 2:
            # Second call: return answer after observing navigation result
            return "ANSWER: Successfully navigated to example.com and extracted content"
        else:
            return "ANSWER: Task completed"

    return llm_func


async def main():
    """Run agent demo with browser integration."""
    print("=" * 60)
    print("ASTRA OS Agent Kernel Demo")
    print("=" * 60)

    # Initialize browser driver
    print("\n[1/4] Initializing browser driver...")
    driver = DOMDriver(headless=True)
    await driver.start()
    print("✓ Browser ready")

    # Create tool registry
    print("\n[2/4] Creating tool registry...")
    registry = create_browser_registry(driver)
    tools = registry.list_tools()
    print(f"✓ Registered {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    # Create agent
    print("\n[3/4] Creating agent kernel...")
    llm_func = create_mock_llm()
    agent = AgentKernel(
        tool_registry=registry,
        llm_func=llm_func,
        max_iterations=10,
        max_tool_calls=5,
    )
    print("✓ Agent kernel ready")

    # Run agent on task
    print("\n[4/4] Running agent on task...")
    print("-" * 60)

    task = "Navigate to example.com and tell me what you find"
    print(f"Task: {task}")
    print("-" * 60)

    result = agent.run(task)

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)

    if result["ok"]:
        print(f"✓ Success: {result['answer']}")
    else:
        print(f"✗ Failed: {result['error']}")

    print(f"\nStats:")
    print(f"  Iterations: {result['iterations']}")
    print(f"  Tool calls: {result['tool_calls']}")
    print(f"  Elapsed: {result['elapsed_ms']}ms")

    # Cleanup
    print("\n[Cleanup] Stopping browser...")
    await driver.stop()
    print("✓ Done")

    print("\n" + "=" * 60)


def run_simple_demo():
    """Run a simple demo without browser (for quick testing)."""
    print("=" * 60)
    print("ASTRA OS Agent Kernel - Simple Demo")
    print("=" * 60)

    # Create simple registry
    registry = ToolRegistry()

    registry.register(
        name="info.echo",
        func=lambda args: {"result": args.get("message", "echo")},
        description="Echo a message",
        scope="info",
        requires_token=False,
    )

    # Simple LLM that uses echo tool
    call_count = [0]

    def simple_llm(prompt):
        call_count[0] += 1
        if call_count[0] == 1:
            return "CALL_TOOL: info.echo {\"message\": \"Hello ASTRA!\"}"
        else:
            return "ANSWER: Successfully echoed the message"

    # Create agent
    agent = AgentKernel(
        tool_registry=registry,
        llm_func=simple_llm,
        max_iterations=5,
    )

    # Run
    result = agent.run("Echo a greeting")

    print(f"\nResult: {result}")

    if result["ok"]:
        print(f"✓ {result['answer']}")
    else:
        print(f"✗ {result['error']}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        run_simple_demo()
    else:
        print("\nStarting browser demo...")
        print("(Use --simple for non-browser demo)\n")
        asyncio.run(main())
