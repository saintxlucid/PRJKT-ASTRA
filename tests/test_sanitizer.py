# tests/test_sanitizer.py
"""Unit tests for DOM sanitizer."""
import pytest
from comet_browser.dom.sanitizer import (
    sanitize_html,
    html_to_markdown,
    extract_links,
)


def test_sanitize_removes_scripts():
    """Ensure script tags are completely removed."""
    html = """
    <div>
        <p>Safe content</p>
        <script>alert('XSS')</script>
        <p>More safe content</p>
    </div>
    """
    result = sanitize_html(html)
    
    assert "script" not in result.lower()
    assert "XSS" not in result
    assert "Safe content" in result
    assert "More safe content" in result


def test_sanitize_removes_styles():
    """Ensure style tags are removed."""
    html = """
    <div>
        <style>body { display: none; }</style>
        <p>Content</p>
    </div>
    """
    result = sanitize_html(html)
    
    assert "style" not in result.lower()
    assert "display: none" not in result
    assert "Content" in result


def test_sanitize_removes_hidden_elements():
    """Ensure hidden elements are stripped."""
    html = """
    <div>
        <p>Visible</p>
        <p hidden>Hidden attribute</p>
        <p style="display:none">Display none</p>
        <p style="visibility: hidden">Visibility hidden</p>
        <p style="opacity:0">Opacity zero</p>
        <p>Visible again</p>
    </div>
    """
    result = sanitize_html(html)
    
    assert "Visible" in result
    assert "Visible again" in result
    assert "Hidden attribute" not in result
    assert "Display none" not in result
    assert "Visibility hidden" not in result
    assert "Opacity zero" not in result


def test_sanitize_removes_dangerous_tags():
    """Ensure dangerous tags are stripped."""
    html = """
    <div>
        <p>Safe</p>
        <iframe src="evil.com"></iframe>
        <object data="malware.exe"></object>
        <embed src="bad.swf">
        <link rel="stylesheet" href="evil.css">
    </div>
    """
    result = sanitize_html(html)
    
    assert "Safe" in result
    assert "iframe" not in result.lower()
    assert "object" not in result.lower()
    assert "embed" not in result.lower()
    assert "link" not in result.lower()


def test_sanitize_removes_password_inputs():
    """Ensure password inputs are removed."""
    html = """
    <form>
        <input type="text" value="username">
        <input type="password" value="secret">
    </form>
    """
    result = sanitize_html(html)
    
    assert "username" in result
    assert "secret" not in result
    assert 'type="password"' not in result


def test_sanitize_removes_contenteditable():
    """Ensure contenteditable elements are removed (prompt injection risk)."""
    html = """
    <div>
        <p>Normal</p>
        <div contenteditable="true">Editable prompt injection</div>
    </div>
    """
    result = sanitize_html(html)
    
    assert "Normal" in result
    assert "Editable prompt injection" not in result


def test_sanitize_normalizes_whitespace():
    """Ensure excessive whitespace is normalized."""
    html = """
    <p>Text    with    many    spaces</p>
    <p>


        Line breaks


    </p>
    """
    result = sanitize_html(html)
    
    assert "Text with many spaces" in result
    # Should not have more than 2 consecutive newlines
    assert "\n\n\n" not in result


def test_html_to_markdown_basic():
    """Test basic HTML to Markdown conversion."""
    html = """
    <h1>Main Title</h1>
    <p>Some <strong>bold</strong> and <em>italic</em> text.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    <a href="https://example.com">Link</a>
    """
    result = html_to_markdown(html)
    
    assert "# Main Title" in result
    assert "**bold**" in result
    assert "*italic*" in result
    assert "- Item 1" in result
    assert "- Item 2" in result
    assert "[Link](https://example.com)" in result


def test_html_to_markdown_enforces_token_budget():
    """Ensure token budget is enforced."""
    # Generate large HTML
    html = "<p>" + (" ".join(["word"] * 2000)) + "</p>"
    
    result = html_to_markdown(html, max_tokens=100)
    
    # Should be truncated
    assert "[Content truncated...]" in result
    # Should be much shorter than original
    assert len(result) < len(html) / 5


def test_html_to_markdown_sanitizes():
    """Ensure html_to_markdown sanitizes dangerous content."""
    html = """
    <h1>Title</h1>
    <script>alert('XSS')</script>
    <p>Content</p>
    """
    result = html_to_markdown(html)
    
    assert "# Title" in result
    assert "Content" in result
    assert "script" not in result.lower()
    assert "XSS" not in result


def test_extract_links():
    """Test link extraction."""
    html = """
    <div>
        <a href="https://example.com">Example</a>
        <a href="/relative">Relative Link</a>
        <a href="https://test.com"><strong>Bold Link</strong></a>
    </div>
    """
    links = extract_links(html)
    
    assert len(links) == 3
    assert links[0] == {"text": "Example", "href": "https://example.com"}
    assert links[1] == {"text": "Relative Link", "href": "/relative"}
    assert links[2] == {"text": "Bold Link", "href": "https://test.com"}


def test_sanitize_empty_input():
    """Handle empty input gracefully."""
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""


def test_sanitize_malformed_html():
    """Handle malformed HTML without crashing."""
    html = "<div><p>Unclosed tags"
    result = sanitize_html(html)
    
    # Should return something (even if empty is safer)
    assert isinstance(result, str)
