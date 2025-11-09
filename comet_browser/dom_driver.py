"""
DOM Driver - Playwright/Chromium wrapper with budget enforcement.

Provides safe browser automation with timeout enforcement from token budgets.
All operations respect budget_ms limits to prevent runaway browser sessions.

Architecture:
- Wraps Playwright async API with timeout enforcement
- Enforces budget limits on navigate(), extract_element(), screenshot()
- Returns structured data for LLM consumption
- Handles browser lifecycle (launch, close, cleanup)

Example:
    driver = DOMDriver(budget_ms=5000)
    await driver.launch()
    result = await driver.navigate("https://example.com")
    element = await driver.extract_element("h1")
    await driver.close()
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = Any
    Page = Any
    PlaywrightTimeout = TimeoutError


class DOMDriver:
    """
    Browser automation driver with budget enforcement.
    
    All operations respect budget_ms timeout limits.
    """
    
    def __init__(self, budget_ms: int = 30000, headless: bool = True):
        """
        Initialize DOM driver.
        
        Args:
            budget_ms: Maximum time budget for browser operations (default 30s)
            headless: Run browser in headless mode (default True)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            )
        
        self.budget_ms = budget_ms
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None
        self._launched = False
        
        logger.info(f"DOMDriver initialized with budget={budget_ms}ms, headless={headless}")
    
    async def launch(self) -> dict[str, Any]:
        """
        Launch browser instance.
        
        Returns:
            Result dict with {"ok": bool, "browser_type": str}
        """
        if self._launched:
            return {"ok": True, "browser_type": "chromium", "note": "already_launched"}
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            self._launched = True
            
            logger.info("Browser launched successfully")
            return {"ok": True, "browser_type": "chromium"}
        
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return {"ok": False, "error": str(e)}
    
    async def navigate(self, url: str) -> dict[str, Any]:
        """
        Navigate to URL with budget timeout enforcement.
        
        Args:
            url: URL to navigate to
        
        Returns:
            Result dict with {"ok": bool, "url": str, "title": str, "ms": int}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        t0 = time.time()
        
        try:
            # Navigate with timeout from budget
            await self.page.goto(url, timeout=self.budget_ms, wait_until="domcontentloaded")
            
            # Get page metadata
            title = await self.page.title()
            final_url = self.page.url
            
            elapsed = int((time.time() - t0) * 1000)
            logger.info(f"Navigated to {url} in {elapsed}ms")
            
            return {
                "ok": True,
                "url": final_url,
                "title": title,
                "ms": elapsed
            }
        
        except PlaywrightTimeout:
            elapsed = int((time.time() - t0) * 1000)
            logger.error(f"Navigation timeout after {elapsed}ms")
            return {"ok": False, "error": "timeout", "ms": elapsed}
        
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            logger.error(f"Navigation failed: {e}")
            return {"ok": False, "error": str(e), "ms": elapsed}
    
    async def extract_element(self, selector: str, extract_type: str = "text") -> dict[str, Any]:
        """
        Extract element content by CSS selector.
        
        Args:
            selector: CSS selector (e.g., "h1", "#main", ".article")
            extract_type: What to extract ("text", "html", "attributes")
        
        Returns:
            Result dict with {"ok": bool, "content": str/dict, "selector": str}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        try:
            element = await self.page.query_selector(selector)
            
            if not element:
                return {"ok": False, "error": "element_not_found", "selector": selector}
            
            if extract_type == "text":
                content = await element.inner_text()
            elif extract_type == "html":
                content = await element.inner_html()
            elif extract_type == "attributes":
                # Get all attributes
                content = await element.evaluate("el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))")
            else:
                return {"ok": False, "error": "invalid_extract_type", "valid": ["text", "html", "attributes"]}
            
            logger.info(f"Extracted {extract_type} from {selector}")
            return {"ok": True, "content": content, "selector": selector, "type": extract_type}
        
        except Exception as e:
            logger.error(f"Element extraction failed: {e}")
            return {"ok": False, "error": str(e), "selector": selector}
    
    async def extract_multiple(self, selector: str, extract_type: str = "text", limit: int = 10) -> dict[str, Any]:
        """
        Extract multiple elements matching selector.
        
        Args:
            selector: CSS selector
            extract_type: What to extract ("text", "html")
            limit: Maximum number of elements to extract
        
        Returns:
            Result dict with {"ok": bool, "elements": list, "count": int}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        try:
            elements = await self.page.query_selector_all(selector)
            
            if not elements:
                return {"ok": True, "elements": [], "count": 0, "selector": selector}
            
            results = []
            for elem in elements[:limit]:
                if extract_type == "text":
                    content = await elem.inner_text()
                elif extract_type == "html":
                    content = await elem.inner_html()
                else:
                    content = await elem.evaluate("el => el.outerHTML")
                
                results.append(content)
            
            logger.info(f"Extracted {len(results)} elements from {selector}")
            return {"ok": True, "elements": results, "count": len(results), "selector": selector}
        
        except Exception as e:
            logger.error(f"Multiple element extraction failed: {e}")
            return {"ok": False, "error": str(e), "selector": selector}
    
    async def screenshot(self, path: str | None = None, full_page: bool = False) -> dict[str, Any]:
        """
        Take screenshot with budget timeout enforcement.
        
        Args:
            path: Optional path to save screenshot (PNG format)
            full_page: Capture full scrollable page (default: viewport only)
        
        Returns:
            Result dict with {"ok": bool, "path": str, "bytes": bytes (if no path)}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        try:
            # Screenshot with timeout
            screenshot_bytes = await self.page.screenshot(
                path=path,
                full_page=full_page,
                timeout=min(self.budget_ms, 10000)  # Cap at 10s for screenshots
            )
            
            if path:
                logger.info(f"Screenshot saved to {path}")
                return {"ok": True, "path": path, "full_page": full_page}
            else:
                logger.info(f"Screenshot captured ({len(screenshot_bytes)} bytes)")
                return {"ok": True, "bytes": screenshot_bytes, "full_page": full_page}
        
        except PlaywrightTimeout:
            logger.error("Screenshot timeout")
            return {"ok": False, "error": "timeout"}
        
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"ok": False, "error": str(e)}
    
    async def get_html(self) -> dict[str, Any]:
        """
        Get full page HTML.
        
        Returns:
            Result dict with {"ok": bool, "html": str, "length": int}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        try:
            html = await self.page.content()
            logger.info(f"Retrieved page HTML ({len(html)} bytes)")
            return {"ok": True, "html": html, "length": len(html)}
        
        except Exception as e:
            logger.error(f"HTML retrieval failed: {e}")
            return {"ok": False, "error": str(e)}
    
    async def execute_script(self, script: str) -> dict[str, Any]:
        """
        Execute JavaScript in page context.
        
        Args:
            script: JavaScript code to execute
        
        Returns:
            Result dict with {"ok": bool, "result": Any}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        try:
            result = await self.page.evaluate(script)
            logger.info("Script executed successfully")
            return {"ok": True, "result": result}
        
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return {"ok": False, "error": str(e)}
    
    async def wait_for_selector(self, selector: str, timeout_ms: int | None = None) -> dict[str, Any]:
        """
        Wait for element to appear with timeout.
        
        Args:
            selector: CSS selector to wait for
            timeout_ms: Optional timeout (default: use budget_ms)
        
        Returns:
            Result dict with {"ok": bool, "selector": str, "ms": int}
        """
        if not self._launched or not self.page:
            return {"ok": False, "error": "browser_not_launched"}
        
        timeout = timeout_ms or self.budget_ms
        t0 = time.time()
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            elapsed = int((time.time() - t0) * 1000)
            logger.info(f"Selector {selector} appeared in {elapsed}ms")
            return {"ok": True, "selector": selector, "ms": elapsed}
        
        except PlaywrightTimeout:
            elapsed = int((time.time() - t0) * 1000)
            logger.error(f"Wait timeout for {selector} after {elapsed}ms")
            return {"ok": False, "error": "timeout", "selector": selector, "ms": elapsed}
        
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            logger.error(f"Wait failed: {e}")
            return {"ok": False, "error": str(e), "selector": selector, "ms": elapsed}
    
    async def close(self) -> dict[str, Any]:
        """
        Close browser and cleanup resources.
        
        Returns:
            Result dict with {"ok": bool}
        """
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self._launched = False
            self.browser = None
            self.page = None
            self.playwright = None
            
            logger.info("Browser closed successfully")
            return {"ok": True}
        
        except Exception as e:
            logger.error(f"Browser close failed: {e}")
            return {"ok": False, "error": str(e)}
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


async def quick_navigate(url: str, budget_ms: int = 10000) -> dict[str, Any]:
    """
    Quick helper to navigate and get page title.
    
    Args:
        url: URL to visit
        budget_ms: Time budget in milliseconds
    
    Returns:
        Result dict with page metadata
    """
    async with DOMDriver(budget_ms=budget_ms) as driver:
        return await driver.navigate(url)
