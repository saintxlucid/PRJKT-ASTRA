# comet_browser/dom/sanitizer.py
"""
DOM sanitizer to strip dangerous content before LLM consumption.
Critical security layer to prevent prompt injection and XSS.
"""
import re
from html.parser import HTMLParser
from typing import Any

# Dangerous tags that must be stripped
DANGEROUS_TAGS = {
    "script",
    "style",
    "noscript",
    "iframe",
    "object",
    "embed",
    "applet",
    "link",
    "meta",
}

# Attributes that hide content
HIDDEN_ATTRS = {"hidden", "aria-hidden"}

# CSS patterns that indicate invisible content
INVISIBLE_CSS = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0",
    re.IGNORECASE
)


class SafeHTMLParser(HTMLParser):
    """HTML parser that sanitizes dangerous content."""

    def __init__(self):
        super().__init__()
        self.output = []
        self.skip_until = None  # Tag to skip until closed

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Any]]) -> None:
        """Handle opening tag - check if it should be stripped."""
        if self.skip_until:
            return

        tag_lower = tag.lower()

        # Skip dangerous tags
        if tag_lower in DANGEROUS_TAGS:
            self.skip_until = tag_lower
            return

        # Check for hidden attributes
        attrs_dict = dict(attrs)
        if any(attr in attrs_dict for attr in HIDDEN_ATTRS):
            self.skip_until = tag_lower
            return

        # Check for invisible CSS
        style = attrs_dict.get("style", "")
        if INVISIBLE_CSS.search(style):
            self.skip_until = tag_lower
            return

        # Check for contenteditable (can inject prompts)
        if attrs_dict.get("contenteditable"):
            self.skip_until = tag_lower
            return

        # Check for password inputs
        if tag_lower == "input" and attrs_dict.get("type") == "password":
            self.skip_until = tag_lower
            return

        # Safe tag - keep it
        attr_str = " ".join(f'{k}="{v}"' for k, v in attrs if v is not None)
        self.output.append(f"<{tag} {attr_str}>" if attr_str else f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tag."""
        if self.skip_until == tag.lower():
            self.skip_until = None
            return

        if not self.skip_until:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        """Handle text content."""
        if not self.skip_until:
            # Normalize whitespace
            text = " ".join(data.split())
            if text:
                self.output.append(text)

    def handle_comment(self, data: str) -> None:
        """Strip all comments."""
        pass

    def get_sanitized(self) -> str:
        """Get sanitized HTML."""
        return "".join(self.output)


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML by removing dangerous content.

    Strips:
    - Scripts, styles, iframes
    - Hidden/invisible elements
    - Comments
    - Contenteditable regions
    - Password inputs
    - Zero-width characters

    Args:
        html: Raw HTML string

    Returns:
        Sanitized HTML string
    """
    if not html:
        return ""

    # Remove zero-width characters (common in prompt injection)
    html = re.sub(r"[\u200B-\u200D\uFEFF]", "", html)

    # Parse and sanitize
    parser = SafeHTMLParser()
    try:
        parser.feed(html)
    except Exception:
        # If parsing fails, return empty (safer than potentially dangerous HTML)
        return ""

    sanitized = parser.get_sanitized()

    # Collapse multiple whitespace
    sanitized = re.sub(r"\s{2,}", " ", sanitized)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)

    return sanitized.strip()


def html_to_markdown(html: str, max_tokens: int = 1200) -> str:
    """
    Convert sanitized HTML to Markdown with token budget.

    Args:
        html: HTML string (should be pre-sanitized)
        max_tokens: Maximum approximate tokens (words * 1.3)

    Returns:
        Markdown string bounded by token budget
    """
    # First sanitize
    safe_html = sanitize_html(html)

    # Simple HTML to Markdown conversion (basic tags)
    # For production, consider using html2text or similar

    # Headers
    safe_html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", safe_html)
    safe_html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", safe_html)
    safe_html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", safe_html)

    # Lists
    safe_html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", safe_html)

    # Links
    safe_html = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        safe_html
    )

    # Emphasis
    safe_html = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", safe_html)
    safe_html = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", safe_html)
    safe_html = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", safe_html)
    safe_html = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", safe_html)

    # Code
    safe_html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", safe_html)

    # Remove remaining HTML tags
    markdown = re.sub(r"<[^>]+>", "", safe_html)

    # Normalize whitespace again
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = markdown.strip()

    # Enforce token budget (rough approximation)
    words = markdown.split()
    approx_tokens = int(len(words) * 1.3)

    if approx_tokens > max_tokens:
        # Truncate to budget
        target_words = int(max_tokens / 1.3)
        markdown = " ".join(words[:target_words]) + "\n\n[Content truncated...]"

    return markdown


def extract_links(html: str) -> list[dict[str, str]]:
    """
    Extract links from HTML.

    Args:
        html: HTML string

    Returns:
        List of dicts with 'text' and 'href' keys
    """
    links = []
    pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'

    for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
        href = match.group(1)
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if href and text:
            links.append({"text": text, "href": href})

    return links
