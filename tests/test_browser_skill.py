"""
Tests for browser skill integration.

Tests the unified browser interface that bridges both DOM driver implementations.
"""

import pytest
from chat_os.plan import PlanStep
from chat_os.executor import ExecutionContext

# Import browser skill handlers
try:
    from chat_os.skills.browser import (
        handle_browser_navigate,
        handle_browser_extract,
        handle_browser_click,
        handle_browser_type,
        handle_browser_screenshot,
        handle_browser_close,
    )
    BROWSER_AVAILABLE = True
except ImportError as e:
    BROWSER_AVAILABLE = False
    SKIP_REASON = f"Browser skill not available: {e}"


pytestmark = pytest.mark.skipif(
    not BROWSER_AVAILABLE,
    reason=SKIP_REASON if not BROWSER_AVAILABLE else "Browser not available"
)


@pytest.fixture
def context():
    """Create execution context."""
    return ExecutionContext(state={}, variables={})


def test_browser_navigate_basic(context):
    """Test basic navigation."""
    step = PlanStep(
        intent="browser.navigate",
        args={"url": "https://example.com", "extract_content": False},
        rationale="Test navigation"
    )
    
    result = handle_browser_navigate(step, context)
    
    assert result["ok"] is True
    assert "url" in result
    assert "title" in result


def test_browser_navigate_with_content_extraction(context):
    """Test navigation with content extraction."""
    step = PlanStep(
        intent="browser.navigate",
        args={
            "url": "https://example.com",
            "extract_content": True,
            "max_tokens": 500
        },
        rationale="Test navigation with extraction"
    )
    
    result = handle_browser_navigate(step, context)
    
    assert result["ok"] is True
    assert "content" in result
    assert len(result["content"]) > 0


def test_browser_navigate_missing_url(context):
    """Test navigation without URL."""
    step = PlanStep(
        intent="browser.navigate",
        args={},
        rationale="Test missing URL"
    )
    
    result = handle_browser_navigate(step, context)
    
    assert result["ok"] is False
    assert "error" in result


def test_browser_extract_full_page(context):
    """Test extracting full page content."""
    # First navigate
    nav_step = PlanStep(
        intent="browser.navigate",
        args={"url": "https://example.com"},
        rationale="Navigate first"
    )
    handle_browser_navigate(nav_step, context)
    
    # Then extract
    extract_step = PlanStep(
        intent="browser.extract",
        args={"max_tokens": 500},
        rationale="Extract content"
    )
    
    result = handle_browser_extract(extract_step, context)
    
    assert result["ok"] is True
    assert "content" in result


def test_browser_extract_element(context):
    """Test extracting specific element."""
    # First navigate
    nav_step = PlanStep(
        intent="browser.navigate",
        args={"url": "https://example.com"},
        rationale="Navigate first"
    )
    handle_browser_navigate(nav_step, context)
    
    # Extract h1
    extract_step = PlanStep(
        intent="browser.extract",
        args={"selector": "h1", "extract_type": "text"},
        rationale="Extract heading"
    )
    
    result = handle_browser_extract(extract_step, context)
    
    assert result["ok"] is True
    assert "content" in result
    assert result["selector"] == "h1"


def test_browser_click(context):
    """Test clicking element."""
    # First navigate
    nav_step = PlanStep(
        intent="browser.navigate",
        args={"url": "https://example.com"},
        rationale="Navigate first"
    )
    handle_browser_navigate(nav_step, context)
    
    # Click link (may not exist, but tests the API)
    click_step = PlanStep(
        intent="browser.click",
        args={"selector": "a"},
        rationale="Click first link"
    )
    
    result = handle_browser_click(click_step, context)
    
    # Should either succeed or fail gracefully
    assert "ok" in result


def test_browser_type(context):
    """Test typing into input."""
    # First navigate to page with input
    nav_step = PlanStep(
        intent="browser.navigate",
        args={"url": "https://example.com"},
        rationale="Navigate first"
    )
    handle_browser_navigate(nav_step, context)
    
    # Type into input (may not exist, but tests the API)
    type_step = PlanStep(
        intent="browser.type",
        args={"selector": "input", "text": "test"},
        rationale="Type text"
    )
    
    result = handle_browser_type(type_step, context)
    
    # Should either succeed or fail gracefully
    assert "ok" in result


def test_browser_screenshot(context, tmp_path):
    """Test taking screenshot."""
    # First navigate
    nav_step = PlanStep(
        intent="browser.navigate",
        args={"url": "https://example.com"},
        rationale="Navigate first"
    )
    handle_browser_navigate(nav_step, context)
    
    # Take screenshot
    screenshot_path = str(tmp_path / "test.png")
    screenshot_step = PlanStep(
        intent="browser.screenshot",
        args={"path": screenshot_path, "full_page": False},
        rationale="Capture screenshot"
    )
    
    result = handle_browser_screenshot(screenshot_step, context)
    
    assert result["ok"] is True
    assert result["path"] == screenshot_path


def test_browser_close(context):
    """Test closing browser."""
    step = PlanStep(
        intent="browser.close",
        args={},
        rationale="Close browser"
    )
    
    result = handle_browser_close(step, context)
    
    assert result["ok"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
