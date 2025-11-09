"""Browser intent handlers for CHAT OS."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from chat_os.executor import ExecutionContext, register_intent  # noqa: I001
from chat_os.plan import PlanStep
from comet_browser.dom.driver import DOMDriver


# Global driver instance (lazy-initialized)
_driver: DOMDriver | None = None


def _get_driver() -> DOMDriver:
    """Get or create global DOM driver instance."""
    global _driver
    if _driver is None:
        _driver = DOMDriver(headless=True)
    return _driver


def _run_async(coro: Any) -> dict[str, Any]:
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result: dict[str, Any] = loop.run_until_complete(coro)
    return result


@register_intent("browser.navigate")
def handle_navigate(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Navigate to URL using DOM driver."""
    url = step.args.get("url")
    if not url:
        return {"ok": False, "error": "Missing required arg: url"}

    timeout_ms = int(step.args.get("timeout_ms", 15000))

    driver = _get_driver()
    result = _run_async(driver.navigate(url, timeout_ms=timeout_ms))

    # Store URL in context for next steps
    if result.get("ok"):
        ctx.variables["browser.current_url"] = result["url"]
        ctx.variables["browser.current_title"] = result.get("title", "")

    return result


@register_intent("browser.extract_markdown")
def handle_extract_markdown(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Extract page content as sanitized markdown."""
    max_tokens = int(step.args.get("max_tokens", 1200))
    sanitize = step.args.get("sanitize", True)

    driver = _get_driver()

    # Ensure driver is started
    if not driver._page:
        return {"ok": False, "error": "No page loaded - call browser.navigate first"}

    result = _run_async(driver.extract_dom(max_tokens=max_tokens, sanitize=sanitize))

    # Handle pagination if requested
    if step.args.get("paginate", False) and result.get("ok"):
        max_pages = int(step.args.get("max_pages", 3))
        pages = [result["markdown"]]

        for _ in range(2, max_pages + 1):
            # Try to find and click "Next" link (common patterns)
            next_selectors = [
                'a[rel="next"]',
                'a:has-text("Next")',
                'button:has-text("Next")',
                ".pagination .next a",
            ]

            clicked = False
            for selector in next_selectors:
                click_result = _run_async(driver.click(selector, timeout_ms=2000))
                if click_result.get("ok"):
                    clicked = True
                    # Wait for new content
                    time.sleep(1)
                    page_result = _run_async(driver.extract_dom(max_tokens=max_tokens, sanitize=sanitize))
                    if page_result.get("ok"):
                        pages.append(page_result["markdown"])
                    break

            if not clicked:
                break

        # Combine all pages
        result["markdown"] = "\n\n---\n\n".join(pages)
        result["pages_extracted"] = len(pages)

    return result


@register_intent("browser.query")
def handle_query(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Query element by CSS selector."""
    selector = step.args.get("selector")
    if not selector:
        return {"ok": False, "error": "Missing required arg: selector"}

    driver = _get_driver()

    if not driver._page:
        return {"ok": False, "error": "No page loaded - call browser.navigate first"}

    return _run_async(driver.query(selector))


@register_intent("browser.click")
def handle_click(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Click element by CSS selector."""
    selector = step.args.get("selector")
    if not selector:
        return {"ok": False, "error": "Missing required arg: selector"}

    timeout_ms = int(step.args.get("timeout_ms", 5000))

    driver = _get_driver()

    if not driver._page:
        return {"ok": False, "error": "No page loaded - call browser.navigate first"}

    return _run_async(driver.click(selector, timeout_ms=timeout_ms))


@register_intent("browser.type")
def handle_type(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Type text into element."""
    selector = step.args.get("selector")
    text = step.args.get("text")

    if not selector or text is None:
        return {"ok": False, "error": "Missing required args: selector, text"}

    timeout_ms = int(step.args.get("timeout_ms", 5000))
    clear_first = step.args.get("clear_first", True)

    driver = _get_driver()

    if not driver._page:
        return {"ok": False, "error": "No page loaded - call browser.navigate first"}

    return _run_async(driver.type_text(selector, str(text), timeout_ms=timeout_ms, clear_first=clear_first))


async def cleanup_driver() -> None:
    """Stop and cleanup global driver."""
    global _driver
    if _driver:
        await _driver.stop()
        _driver = None
