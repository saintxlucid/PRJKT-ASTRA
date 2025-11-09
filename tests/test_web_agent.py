"""
Tests for web agent workflows.

Tests high-level web automation patterns.
"""

import pytest
from unittest.mock import Mock, patch
from chat_os.plan import PlanStep, Plan
from chat_os.executor import ExecutionContext

# Import web agent handlers
try:
    from chat_os.skills.web_agent import (
        handle_web_research,
        handle_extract_structured,
        handle_fill_form,
        handle_paginate,
        handle_monitor_page,
    )
    WEB_AGENT_AVAILABLE = True
except ImportError as e:
    WEB_AGENT_AVAILABLE = False
    SKIP_REASON = f"Web agent not available: {e}"


pytestmark = pytest.mark.skipif(
    not WEB_AGENT_AVAILABLE,
    reason=SKIP_REASON if not WEB_AGENT_AVAILABLE else "Web agent not available"
)


@pytest.fixture
def context():
    """Create execution context."""
    # ExecutionContext requires a Plan object with proper structure
    from chat_os.plan import PlanMeta
    
    meta = PlanMeta(
        id="test-web-agent",
        policy="test",
        max_time_ms=30000
    )
    plan = Plan(
        version="0.3",
        meta=meta,
        steps=[]
    )
    return ExecutionContext(plan=plan)


@pytest.fixture
def mock_browser_handlers():
    """Mock browser skill handlers."""
    with patch('chat_os.skills.web_agent.handle_navigate') as nav, \
         patch('chat_os.skills.web_agent.handle_extract_markdown') as extract:
        
        nav.return_value = {
            "ok": True,
            "url": "https://example.com",
            "title": "Example Page"
        }
        
        extract.return_value = {
            "ok": True,
            "markdown": "# Example Page\n\nThis is example content.",
            "tokens": 10
        }
        
        yield {"navigate": nav, "extract": extract}


def test_web_research_basic(context, mock_browser_handlers):
    """Test basic web research workflow."""
    step = PlanStep(
        intent="web_agent.research",
        args={
            "url": "https://example.com",
            "summarize": False
        }
    )
    
    result = handle_web_research(step, context)
    
    assert result["ok"] is True
    assert result["url"] == "https://example.com"
    assert "content" in result
    assert result["tokens_extracted"] > 0


def test_web_research_with_summary(context, mock_browser_handlers):
    """Test web research with LLM summary."""
    with patch('chat_os.skills.web_agent._call_llm') as mock_llm:
        mock_llm.return_value = "This is a summary of the webpage."
        
        step = PlanStep(
            intent="web_agent.research",
            args={
                "url": "https://example.com",
                "summarize": True
            }
        )
        
        result = handle_web_research(step, context)
        
        assert result["ok"] is True
        assert "summary" in result
        assert result["summary"] == "This is a summary of the webpage."


def test_web_research_store_results(context, mock_browser_handlers):
    """Test storing research results in context."""
    step = PlanStep(
        intent="web_agent.research",
        args={
            "url": "https://example.com",
            "store_as": "research_results"
        }
    )
    
    result = handle_web_research(step, context)
    
    assert result["ok"] is True
    assert "research_results" in context.variables
    assert context.variables["research_results"]["url"] == "https://example.com"


def test_web_research_missing_url(context):
    """Test research without URL."""
    step = PlanStep(
        intent="web_agent.research",
        args={}
    )
    
    result = handle_web_research(step, context)
    
    assert result["ok"] is False
    assert "error" in result


def test_extract_structured_basic(context, mock_browser_handlers):
    """Test structured data extraction."""
    with patch('chat_os.skills.web_agent._call_llm') as mock_llm:
        mock_llm.return_value = '{"title": "Example", "price": 19.99}'
        
        step = PlanStep(
            intent="web_agent.extract_structured",
            args={
                "url": "https://example.com",
                "schema": '{"title": "string", "price": "number"}'
            }
        )
        
        result = handle_extract_structured(step, context)
        
        assert result["ok"] is True
        assert "data" in result
        assert result["data"]["title"] == "Example"
        assert result["data"]["price"] == 19.99


def test_extract_structured_missing_schema(context):
    """Test structured extraction without schema."""
    step = PlanStep(
        intent="web_agent.extract_structured",
        args={"url": "https://example.com"}
    )
    
    result = handle_extract_structured(step, context)
    
    assert result["ok"] is False
    assert "error" in result


def test_fill_form_basic(context):
    """Test basic form filling."""
    with patch('chat_os.skills.browser.handle_navigate') as nav, \
         patch('chat_os.skills.browser.handle_type') as type_fn:
        
        nav.return_value = {"ok": True, "url": "https://example.com/form"}
        type_fn.return_value = {"ok": True}
        
        step = PlanStep(
            intent="web_agent.fill_form",
            args={
                "url": "https://example.com/form",
                "fields": {
                    "#name": "John Doe",
                    "#email": "john@example.com"
                },
                "validate": False
            }
        )
        
        result = handle_fill_form(step, context)
        
        assert result["ok"] is True
        assert result["filled_count"] == 2
        assert result["total_fields"] == 2


def test_fill_form_missing_fields(context):
    """Test form filling without fields."""
    step = PlanStep(
        intent="web_agent.fill_form",
        args={"url": "https://example.com/form"}
    )
    
    result = handle_fill_form(step, context)
    
    assert result["ok"] is False
    assert "error" in result


def test_paginate_basic(context):
    """Test pagination workflow."""
    # Mock the imported functions in the web_agent module namespace
    with patch('chat_os.skills.web_agent.handle_extract_markdown') as extract, \
         patch('chat_os.skills.web_agent.handle_click') as click:
        
        # Mock 3 pages of content
        extract.side_effect = [
            {"ok": True, "markdown": "Page 1 content"},
            {"ok": True, "markdown": "Page 2 content"},
            {"ok": True, "markdown": "Page 3 content"},
        ]
        
        # First two clicks succeed, third fails (no more pages)
        click.side_effect = [
            {"ok": True},
            {"ok": True},
            {"ok": False},
        ]
        
        step = PlanStep(
            intent="web_agent.paginate",
            args={
                "next_selector": ".next-button",
                "max_pages": 5,
                "combine_strategy": "list"
            }
        )
        
        result = handle_paginate(step, context)
        
        assert result["ok"] is True
        assert result["pages_visited"] == 3
        assert len(result["combined_content"]) == 3


def test_paginate_missing_selector(context):
    """Test pagination without next selector."""
    step = PlanStep(
        intent="web_agent.paginate",
        args={"max_pages": 5}
    )
    
    result = handle_paginate(step, context)
    
    assert result["ok"] is False
    assert "error" in result


def test_monitor_page_no_changes(context):
    """Test page monitoring with no changes."""
    with patch('chat_os.skills.web_agent.handle_navigate') as nav, \
         patch('chat_os.skills.web_agent.handle_extract_markdown') as extract, \
         patch('time.sleep'):  # Mock sleep to speed up test
        
        nav.return_value = {"ok": True, "url": "https://example.com"}
        extract.return_value = {"ok": True, "markdown": "Same content"}
        
        step = PlanStep(
            intent="web_agent.monitor",
            args={
                "url": "https://example.com",
                "interval_seconds": 1,
                "max_checks": 3
            }
        )
        
        result = handle_monitor_page(step, context)
        
        assert result["ok"] is True
        assert result["checks_performed"] == 3
        assert result["changes_detected"] == 0


def test_monitor_page_with_changes(context):
    """Test page monitoring with content changes."""
    with patch('chat_os.skills.web_agent.handle_navigate') as nav, \
         patch('chat_os.skills.web_agent.handle_extract_markdown') as extract, \
         patch('time.sleep'):
        
        nav.return_value = {"ok": True, "url": "https://example.com"}
        
        # Mock changing content
        extract.side_effect = [
            {"ok": True, "markdown": "Content v1"},
            {"ok": True, "markdown": "Content v2"},
            {"ok": True, "markdown": "Content v2"},
        ]
        
        step = PlanStep(
            intent="web_agent.monitor",
            args={
                "url": "https://example.com",
                "interval_seconds": 1,
                "max_checks": 3
            }
        )
        
        result = handle_monitor_page(step, context)
        
        assert result["ok"] is True
        assert result["checks_performed"] == 3
        assert result["changes_detected"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
