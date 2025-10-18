"""
ASTRA Browser Automation Tools
Safe browser automation with domain checks and timeouts.
Created: October 16, 2025
"""
import asyncio
from typing import Optional, Dict, Any, List
import structlog
from urllib.parse import urlparse
from pathlib import Path
import json
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page
from src.astra.core.tool_bus import tool

logger = structlog.get_logger()

class BrowserSession:
    """Manages browser lifecycle and provides automation helpers"""
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        """Start browser session"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-gpu']
        )
        self.page = await self.browser.new_page()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up browser session"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()

def validate_domain(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
    """
    Validate if domain is allowed.
    Args:
        url: URL to check
        allowed_domains: List of allowed domains/patterns
    Returns:
        True if domain is allowed
    """
    if not allowed_domains:
        return True
        
    domain = urlparse(url).netloc
    return any(
        domain.endswith(pattern.lstrip("*."))
        for pattern in allowed_domains
    )

@tool(
    name="browser_open",
    description="Open URL in browser",
    schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "wait_for": {"type": "string", "optional": True},
            "timeout": {"type": "number", "default": 30},
            "allowed_domains": {
                "type": "array",
                "items": {"type": "string"},
                "optional": True
            }
        },
        "required": ["url"]
    },
    timeout=60,
    isolated=True
)
async def open_url(
    url: str,
    wait_for: Optional[str] = None,
    timeout: float = 30,
    allowed_domains: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Open URL in browser with safety checks.
    Args:
        url: URL to open
        wait_for: Selector to wait for
        timeout: Page load timeout
        allowed_domains: List of allowed domains
    Returns:
        Dict with page info and screenshot
    """
    # Validate domain
    if not validate_domain(url, allowed_domains):
        raise ValueError(f"Domain not allowed: {urlparse(url).netloc}")
        
    async with BrowserSession() as session:
        try:
            await session.page.goto(url, timeout=timeout * 1000)
            
            if wait_for:
                await session.page.wait_for_selector(
                    wait_for,
                    timeout=timeout * 1000
                )
                
            # Take screenshot
            screenshot_path = Path("screenshots")
            screenshot_path.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_file = screenshot_path / f"screenshot_{timestamp}.png"
            await session.page.screenshot(path=screenshot_file)
            
            return {
                "success": True,
                "url": url,
                "title": await session.page.title(),
                "screenshot": str(screenshot_file)
            }
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

@tool(
    name="browser_click",
    description="Click element in browser",
    schema={
        "type": "object",
        "properties": {
            "selector": {"type": "string"},
            "timeout": {"type": "number", "default": 30},
            "wait_for": {"type": "string", "optional": True}
        },
        "required": ["selector"]
    },
    timeout=60
)
async def click_element(
    selector: str,
    timeout: float = 30,
    wait_for: Optional[str] = None
) -> Dict[str, Any]:
    """Click an element and optionally wait for response"""
    async with BrowserSession() as session:
        try:
            # Wait for and click element
            element = await session.page.wait_for_selector(
                selector,
                timeout=timeout * 1000
            )
            await element.click()
            
            # Wait for response if specified
            if wait_for:
                await session.page.wait_for_selector(
                    wait_for,
                    timeout=timeout * 1000
                )
                
            return {
                "success": True,
                "selector": selector,
                "url": session.page.url
            }
            
        except Exception as e:
            return {
                "success": False,
                "selector": selector,
                "error": str(e)
            }

@tool(
    name="browser_type",
    description="Type text in browser element",
    schema={
        "type": "object",
        "properties": {
            "selector": {"type": "string"},
            "text": {"type": "string"},
            "timeout": {"type": "number", "default": 30},
            "delay": {"type": "number", "default": 50}
        },
        "required": ["selector", "text"]
    },
    timeout=60
)
async def type_text(
    selector: str,
    text: str,
    timeout: float = 30,
    delay: float = 50
) -> Dict[str, Any]:
    """Type text into an element"""
    async with BrowserSession() as session:
        try:
            # Wait for element
            element = await session.page.wait_for_selector(
                selector,
                timeout=timeout * 1000
            )
            
            # Clear existing text
            await element.evaluate('el => el.value = ""')
            
            # Type text with delay
            await element.type(text, delay=delay)
            
            return {
                "success": True,
                "selector": selector,
                "text": text
            }
            
        except Exception as e:
            return {
                "success": False,
                "selector": selector,
                "error": str(e)
            }

@tool(
    name="browser_eval",
    description="Evaluate JavaScript in browser",
    schema={
        "type": "object",
        "properties": {
            "script": {"type": "string"},
            "timeout": {"type": "number", "default": 30}
        },
        "required": ["script"]
    },
    timeout=60
)
async def evaluate_script(
    script: str,
    timeout: float = 30
) -> Dict[str, Any]:
    """Evaluate JavaScript in the page context"""
    async with BrowserSession() as session:
        try:
            result = await session.page.evaluate(
                script,
                timeout=timeout * 1000
            )
            
            return {
                "success": True,
                "result": json.dumps(result) if result else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }