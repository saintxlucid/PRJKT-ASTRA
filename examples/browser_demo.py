# examples/browser_demo.py
"""
Simple demo of COMET browser DOM driver.
Shows basic navigation, extraction, and automation.
"""
import asyncio
from comet_browser.dom.driver import DOMDriver, DOMSession


async def demo_basic_navigation():
    """Demo: Navigate to a page and extract content."""
    print("=== Demo 1: Basic Navigation ===\n")

    async with DOMSession(headless=True) as driver:
        # Navigate to a page
        result = await driver.navigate("https://example.com")
        
        if result["ok"]:
            print(f"✓ Navigated to: {result['url']}")
            print(f"  Title: {result['title']}")
        else:
            print(f"✗ Navigation failed: {result['error']}")
            return

        # Extract DOM as Markdown
        extract_result = await driver.extract_dom(max_tokens=500)
        
        if extract_result["ok"]:
            print(f"\n✓ Extracted {extract_result['length']} chars")
            print(f"\nMarkdown preview:")
            print("-" * 60)
            print(extract_result['markdown'][:300] + "...")
            print("-" * 60)


async def demo_form_interaction():
    """Demo: Search on a website."""
    print("\n=== Demo 2: Form Interaction ===\n")

    async with DOMSession(headless=True) as driver:
        # Navigate to search engine
        result = await driver.navigate("https://duckduckgo.com")
        
        if not result["ok"]:
            print(f"✗ Navigation failed: {result['error']}")
            return

        print(f"✓ Navigated to {result['title']}")

        # Type into search box
        type_result = await driver.type_text("#searchbox_input", "ASTRA OS")
        
        if type_result["ok"]:
            print("✓ Typed search query")
        else:
            print(f"✗ Type failed: {type_result['error']}")

        # Click search button
        click_result = await driver.click("button[type='submit']")
        
        if click_result["ok"]:
            print("✓ Clicked search button")
            
            # Wait a bit for results
            await asyncio.sleep(2)
            
            # Extract results
            extract_result = await driver.extract_dom(max_tokens=800)
            print(f"✓ Extracted search results ({extract_result['length']} chars)")


async def demo_element_query():
    """Demo: Query specific elements."""
    print("\n=== Demo 3: Element Querying ===\n")

    async with DOMSession(headless=True) as driver:
        await driver.navigate("https://example.com")

        # Query heading
        heading = await driver.query("h1")
        
        if heading["found"]:
            print(f"✓ Found heading: '{heading['text']}'")
            print(f"  Visible: {heading['visible']}")

        # Query non-existent element
        missing = await driver.query("#nonexistent")
        
        if not missing["found"]:
            print("✓ Correctly reported missing element")


async def demo_screenshot():
    """Demo: Take a screenshot."""
    print("\n=== Demo 4: Screenshot ===\n")

    async with DOMSession(headless=True) as driver:
        await driver.navigate("https://example.com")

        # Take screenshot
        screenshot_result = await driver.screenshot("example_screenshot.png")
        
        if screenshot_result["ok"]:
            print(f"✓ Screenshot saved to: {screenshot_result['path']}")
        else:
            print(f"✗ Screenshot failed: {screenshot_result['error']}")


async def demo_javascript_execution():
    """Demo: Execute JavaScript."""
    print("\n=== Demo 5: JavaScript Execution ===\n")

    async with DOMSession(headless=True) as driver:
        await driver.navigate("https://example.com")

        # Execute JavaScript
        js_result = await driver.evaluate("document.title")
        
        if js_result["ok"]:
            print(f"✓ JavaScript result: '{js_result['result']}'")

        # Get page info
        page_info = await driver.evaluate("""
            ({
                url: window.location.href,
                width: window.innerWidth,
                height: window.innerHeight,
                userAgent: navigator.userAgent
            })
        """)
        
        if page_info["ok"]:
            print(f"✓ Page info:")
            print(f"  Viewport: {page_info['result']['width']}x{page_info['result']['height']}")
            print(f"  User Agent: {page_info['result']['userAgent'][:50]}...")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("COMET Browser DOM Driver Demo")
    print("=" * 60 + "\n")

    try:
        await demo_basic_navigation()
        await demo_form_interaction()
        await demo_element_query()
        await demo_screenshot()
        await demo_javascript_execution()

        print("\n" + "=" * 60)
        print("✓ All demos completed")
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
