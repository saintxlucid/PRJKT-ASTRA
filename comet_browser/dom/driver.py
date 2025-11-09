# comet_browser/dom/driver.py
"""
DOM driver using Chromium CDP (via Playwright).
Provides navigate, query, click, type, extract primitives.
"""
import asyncio
import json
from typing import Any
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    TimeoutError as PlaywrightTimeout,
)

from comet_browser.dom.sanitizer import sanitize_html, html_to_markdown


class DOMDriver:
    """
    COMET browser DOM driver.
    Wraps Playwright for CDP-based page automation.
    """

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        user_agent: str | None = None,
    ):
        """
        Initialize driver (does not launch browser yet).

        Args:
            headless: Run browser without GUI
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            user_agent: Custom user agent string
        """
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self.user_agent = user_agent

        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def start(self) -> None:
        """Launch browser and create page."""
        if self._browser:
            return  # Already running

        self._playwright = await async_playwright().start()

        browser_args = []
        if not self.headless:
            browser_args.extend(["--disable-blink-features=AutomationControlled"])

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=browser_args,
        )

        context_options = {"viewport": self.viewport}
        if self.user_agent:
            context_options["user_agent"] = self.user_agent

        context = await self._browser.new_context(**context_options)
        self._page = await context.new_page()

    async def stop(self) -> None:
        """Close browser and cleanup."""
        if self._page:
            await self._page.close()
            self._page = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def navigate(self, url: str, timeout_ms: int = 15000) -> dict[str, Any]:
        """
        Navigate to URL.

        Args:
            url: Target URL
            timeout_ms: Navigation timeout in milliseconds

        Returns:
            Dict with keys: ok, url, title, error
        """
        if not self._page:
            await self.start()

        try:
            response = await self._page.goto(url, timeout=timeout_ms, wait_until="load")
            
            title = await self._page.title()
            final_url = self._page.url

            return {
                "ok": True,
                "url": final_url,
                "title": title,
                "status": response.status if response else None,
            }

        except PlaywrightTimeout:
            return {
                "ok": False,
                "error": f"Navigation timeout after {timeout_ms}ms",
                "url": url,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Navigation failed: {e}",
                "url": url,
            }

    async def query(self, selector: str) -> dict[str, Any]:
        """
        Query element by CSS selector.

        Args:
            selector: CSS selector

        Returns:
            Dict with keys: ok, found, text, error
        """
        if not self._page:
            return {"ok": False, "error": "Browser not started"}

        try:
            element = await self._page.query_selector(selector)
            
            if not element:
                return {"ok": True, "found": False, "selector": selector}

            # Get text content
            text = await element.text_content()
            
            # Check visibility
            visible = await element.is_visible()

            return {
                "ok": True,
                "found": True,
                "selector": selector,
                "text": text,
                "visible": visible,
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Query failed: {e}",
                "selector": selector,
            }

    async def click(self, selector: str, timeout_ms: int = 5000) -> dict[str, Any]:
        """
        Click element by CSS selector.

        Args:
            selector: CSS selector
            timeout_ms: Click timeout

        Returns:
            Dict with keys: ok, error
        """
        if not self._page:
            return {"ok": False, "error": "Browser not started"}

        try:
            await self._page.click(selector, timeout=timeout_ms)
            
            # Wait for navigation if triggered
            try:
                await self._page.wait_for_load_state("load", timeout=2000)
            except PlaywrightTimeout:
                pass  # No navigation triggered, continue

            return {"ok": True, "selector": selector}

        except PlaywrightTimeout:
            return {
                "ok": False,
                "error": f"Click timeout after {timeout_ms}ms",
                "selector": selector,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Click failed: {e}",
                "selector": selector,
            }

    async def type_text(
        self,
        selector: str,
        text: str,
        timeout_ms: int = 5000,
        clear_first: bool = True,
    ) -> dict[str, Any]:
        """
        Type text into element.

        Args:
            selector: CSS selector
            text: Text to type
            timeout_ms: Timeout
            clear_first: Clear existing content first

        Returns:
            Dict with keys: ok, error
        """
        if not self._page:
            return {"ok": False, "error": "Browser not started"}

        try:
            if clear_first:
                await self._page.fill(selector, "", timeout=timeout_ms)
            
            await self._page.type(selector, text, timeout=timeout_ms)

            return {"ok": True, "selector": selector}

        except PlaywrightTimeout:
            return {
                "ok": False,
                "error": f"Type timeout after {timeout_ms}ms",
                "selector": selector,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Type failed: {e}",
                "selector": selector,
            }

    async def extract_dom(
        self,
        max_tokens: int = 1200,
        sanitize: bool = True,
    ) -> dict[str, Any]:
        """
        Extract page DOM as sanitized Markdown.

        Args:
            max_tokens: Token budget for extraction
            sanitize: Apply HTML sanitizer

        Returns:
            Dict with keys: ok, markdown, html, url, title, error
        """
        if not self._page:
            return {"ok": False, "error": "Browser not started"}

        try:
            # Get page HTML
            html = await self._page.content()
            url = self._page.url
            title = await self._page.title()

            # Apply sanitizer if requested
            if sanitize:
                html = sanitize_html(html)

            # Convert to Markdown with token budget
            markdown = html_to_markdown(html, max_tokens=max_tokens)

            return {
                "ok": True,
                "markdown": markdown,
                "html": html,
                "url": url,
                "title": title,
                "length": len(markdown),
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Extract failed: {e}",
            }

    async def screenshot(self, path: str, full_page: bool = False) -> dict[str, Any]:
        """
        Take screenshot.

        Args:
            path: Output file path
            full_page: Capture full scrollable page

        Returns:
            Dict with keys: ok, path, error
        """
        if not self._page:
            return {"ok": False, "error": "Browser not started"}

        try:
            await self._page.screenshot(path=path, full_page=full_page)
            
            return {"ok": True, "path": path}

        except Exception as e:
            return {
                "ok": False,
                "error": f"Screenshot failed: {e}",
                "path": path,
            }

    async def evaluate(self, script: str) -> dict[str, Any]:
        """
        Execute JavaScript in page context.

        Args:
            script: JavaScript code

        Returns:
            Dict with keys: ok, result, error
        """
        if not self._page:
            return {"ok": False, "error": "Browser not started"}

        try:
            result = await self._page.evaluate(script)
            
            return {"ok": True, "result": result}

        except Exception as e:
            return {
                "ok": False,
                "error": f"Evaluate failed: {e}",
            }

    def get_page(self) -> Page | None:
        """Get underlying Playwright page (for advanced usage)."""
        return self._page


# Convenience async context manager
class DOMSession:
    """Async context manager for DOMDriver sessions."""

    def __init__(self, **driver_kwargs):
        self.driver = DOMDriver(**driver_kwargs)

    async def __aenter__(self):
        await self.driver.start()
        return self.driver

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.driver.stop()


# Synchronous wrapper for convenience (uses asyncio.run)
def navigate_sync(url: str, **kwargs) -> dict[str, Any]:
    """Synchronous wrapper for navigate."""
    async def _run():
        async with DOMSession() as driver:
            return await driver.navigate(url, **kwargs)
    
    return asyncio.run(_run())


def extract_sync(url: str, max_tokens: int = 1200) -> dict[str, Any]:
    """Synchronous wrapper for navigate + extract."""
    async def _run():
        async with DOMSession() as driver:
            nav_result = await driver.navigate(url)
            if not nav_result["ok"]:
                return nav_result
            
            return await driver.extract_dom(max_tokens=max_tokens)
    
    return asyncio.run(_run())
