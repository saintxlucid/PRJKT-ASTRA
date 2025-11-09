"""
Tests for DOM Driver (Playwright wrapper).

Tests browser automation with budget enforcement.
"""

import pytest
import asyncio
from pathlib import Path

# Check if playwright is available
try:
    from comet_browser.dom_driver import DOMDriver, PLAYWRIGHT_AVAILABLE, quick_navigate
    SKIP_REASON = None
except ImportError as e:
    PLAYWRIGHT_AVAILABLE = False
    SKIP_REASON = f"Playwright not installed: {e}"


pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason=SKIP_REASON or "Playwright not available"
)


@pytest.mark.asyncio
async def test_driver_launch():
    """Test browser launch."""
    driver = DOMDriver(budget_ms=5000)
    result = await driver.launch()
    
    assert result["ok"] is True
    assert result["browser_type"] == "chromium"
    
    await driver.close()


@pytest.mark.asyncio
async def test_driver_navigate():
    """Test navigation to URL."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    result = await driver.navigate("https://example.com")
    
    assert result["ok"] is True
    assert "example.com" in result["url"].lower()
    assert "title" in result
    assert "ms" in result
    
    await driver.close()


@pytest.mark.asyncio
async def test_driver_extract_element():
    """Test element extraction."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    await driver.navigate("https://example.com")
    result = await driver.extract_element("h1", extract_type="text")
    
    assert result["ok"] is True
    assert "content" in result
    assert result["selector"] == "h1"
    
    await driver.close()


@pytest.mark.asyncio
async def test_driver_extract_multiple():
    """Test multiple element extraction."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    await driver.navigate("https://example.com")
    result = await driver.extract_multiple("p", extract_type="text", limit=5)
    
    assert result["ok"] is True
    assert "elements" in result
    assert isinstance(result["elements"], list)
    
    await driver.close()


@pytest.mark.asyncio
async def test_driver_get_html():
    """Test HTML retrieval."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    await driver.navigate("https://example.com")
    result = await driver.get_html()
    
    assert result["ok"] is True
    assert "html" in result
    assert len(result["html"]) > 0
    
    await driver.close()


@pytest.mark.asyncio
async def test_driver_context_manager():
    """Test async context manager usage."""
    async with DOMDriver(budget_ms=10000) as driver:
        result = await driver.navigate("https://example.com")
        assert result["ok"] is True


@pytest.mark.asyncio
async def test_driver_navigate_before_launch():
    """Test error when navigating before launch."""
    driver = DOMDriver(budget_ms=5000)
    result = await driver.navigate("https://example.com")
    
    assert result["ok"] is False
    assert result["error"] == "browser_not_launched"


@pytest.mark.asyncio
async def test_driver_extract_nonexistent_element():
    """Test extraction of non-existent element."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    await driver.navigate("https://example.com")
    result = await driver.extract_element("#nonexistent-id-12345")
    
    assert result["ok"] is False
    assert result["error"] == "element_not_found"
    
    await driver.close()


@pytest.mark.asyncio
async def test_quick_navigate_helper():
    """Test quick navigate helper function."""
    result = await quick_navigate("https://example.com", budget_ms=10000)
    
    assert result["ok"] is True
    assert "title" in result


@pytest.mark.asyncio
async def test_driver_wait_for_selector():
    """Test waiting for selector to appear."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    await driver.navigate("https://example.com")
    result = await driver.wait_for_selector("h1", timeout_ms=5000)
    
    assert result["ok"] is True
    assert result["selector"] == "h1"
    assert "ms" in result
    
    await driver.close()


@pytest.mark.asyncio
async def test_driver_execute_script():
    """Test JavaScript execution."""
    driver = DOMDriver(budget_ms=10000)
    await driver.launch()
    
    await driver.navigate("https://example.com")
    result = await driver.execute_script("document.title")
    
    assert result["ok"] is True
    assert "result" in result
    
    await driver.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
