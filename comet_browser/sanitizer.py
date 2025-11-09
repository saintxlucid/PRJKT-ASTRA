"""
HTML Sanitizer - Strip unsafe/irrelevant content for LLM consumption.

Provides safe HTML cleaning by removing:
- Scripts, styles, iframes (security)
- Hidden/invisible elements (irrelevant)
- Navigation/footer/ads (noise)

Converts clean HTML to Markdown for LLM-friendly text.

Architecture:
- Strip dangerous tags (<script>, <style>, <iframe>)
- Remove hidden elements (display:none, visibility:hidden, opacity:0)
- Remove semantic noise (nav, footer, aside, ads)
- Convert to Markdown for structured text

Example:
    sanitizer = HTMLSanitizer()
    clean_html = sanitizer.sanitize_html(dirty_html)
    markdown = sanitizer.html_to_markdown(clean_html)
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


# Tags to remove completely (security + noise)
DANGEROUS_TAGS = ['script', 'style', 'iframe', 'object', 'embed', 'applet']
NOISE_TAGS = ['nav', 'footer', 'aside', 'header', 'advertisement', 'ad']
FORM_TAGS = ['form', 'input', 'button', 'select', 'textarea']

# Attributes that indicate hidden elements
HIDDEN_ATTRIBUTES = {
    'style': [
        r'display:\s*none',
        r'visibility:\s*hidden',
        r'opacity:\s*0',
        r'position:\s*absolute.*left:\s*-\d+',
    ],
    'class': ['hidden', 'invisible', 'sr-only', 'screen-reader-only', 'visually-hidden'],
    'aria-hidden': ['true'],
}


class HTMLSanitizer:
    """
    HTML sanitizer for LLM consumption.
    
    Strips scripts, styles, hidden elements, and navigation noise.
    """
    
    def __init__(
        self,
        remove_dangerous: bool = True,
        remove_noise: bool = True,
        remove_hidden: bool = True,
        remove_forms: bool = True,
    ):
        """
        Initialize HTML sanitizer.
        
        Args:
            remove_dangerous: Remove <script>, <style>, <iframe>, etc.
            remove_noise: Remove <nav>, <footer>, <aside>, etc.
            remove_hidden: Remove elements with display:none, visibility:hidden, etc.
            remove_forms: Remove form elements
        """
        if not BS4_AVAILABLE:
            raise ImportError("BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
        
        self.remove_dangerous = remove_dangerous
        self.remove_noise = remove_noise
        self.remove_hidden = remove_hidden
        self.remove_forms = remove_forms
        
        logger.info(
            f"HTMLSanitizer initialized: "
            f"dangerous={remove_dangerous}, noise={remove_noise}, "
            f"hidden={remove_hidden}, forms={remove_forms}"
        )
    
    def sanitize_html(self, html: str) -> dict[str, Any]:
        """
        Sanitize HTML by removing dangerous and irrelevant content.
        
        Args:
            html: Raw HTML string
        
        Returns:
            Result dict with {"ok": bool, "html": str, "removed": dict}
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            removed = {
                "dangerous": 0,
                "noise": 0,
                "hidden": 0,
                "forms": 0,
            }
            
            # Remove dangerous tags
            if self.remove_dangerous:
                for tag_name in DANGEROUS_TAGS:
                    for tag in soup.find_all(tag_name):
                        tag.decompose()
                        removed["dangerous"] += 1
            
            # Remove noise tags
            if self.remove_noise:
                for tag_name in NOISE_TAGS:
                    for tag in soup.find_all(tag_name):
                        tag.decompose()
                        removed["noise"] += 1
            
            # Remove form elements
            if self.remove_forms:
                for tag_name in FORM_TAGS:
                    for tag in soup.find_all(tag_name):
                        tag.decompose()
                        removed["forms"] += 1
            
            # Remove hidden elements
            if self.remove_hidden:
                removed["hidden"] = self._remove_hidden_elements(soup)
            
            clean_html = str(soup)
            logger.info(f"Sanitized HTML: removed {sum(removed.values())} elements")
            
            return {
                "ok": True,
                "html": clean_html,
                "removed": removed,
                "length": len(clean_html)
            }
        
        except Exception as e:
            logger.error(f"HTML sanitization failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def _remove_hidden_elements(self, soup: BeautifulSoup) -> int:
        """
        Remove hidden elements based on style and class attributes.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Count of removed elements
        """
        removed_count = 0
        
        # Check style attribute for display:none, visibility:hidden, etc.
        for tag in soup.find_all(style=True):
            style = tag.get('style', '').lower()
            for pattern in HIDDEN_ATTRIBUTES['style']:
                if re.search(pattern, style):
                    tag.decompose()
                    removed_count += 1
                    break
        
        # Check class attribute for hidden, invisible, etc.
        for tag in soup.find_all(class_=True):
            classes = tag.get('class', [])
            if isinstance(classes, list):
                class_str = ' '.join(classes).lower()
            else:
                class_str = str(classes).lower()
            
            for hidden_class in HIDDEN_ATTRIBUTES['class']:
                if hidden_class in class_str:
                    tag.decompose()
                    removed_count += 1
                    break
        
        # Check aria-hidden attribute
        for tag in soup.find_all(attrs={"aria-hidden": "true"}):
            tag.decompose()
            removed_count += 1
        
        return removed_count
    
    def html_to_markdown(self, html: str, body_width: int = 0) -> dict[str, Any]:
        """
        Convert HTML to Markdown for LLM-friendly text.
        
        Args:
            html: HTML string (preferably sanitized first)
            body_width: Text wrap width (0 = no wrap)
        
        Returns:
            Result dict with {"ok": bool, "markdown": str, "length": int}
        """
        if not HTML2TEXT_AVAILABLE:
            # Fallback: extract text only
            try:
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)
                logger.info(f"Converted HTML to text (fallback): {len(text)} chars")
                return {"ok": True, "markdown": text, "length": len(text), "method": "fallback"}
            except Exception as e:
                logger.error(f"HTML text extraction failed: {e}")
                return {"ok": False, "error": str(e)}
        
        try:
            h = html2text.HTML2Text()
            h.body_width = body_width
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_emphasis = False
            
            markdown = h.handle(html)
            logger.info(f"Converted HTML to Markdown: {len(markdown)} chars")
            
            return {
                "ok": True,
                "markdown": markdown,
                "length": len(markdown),
                "method": "html2text"
            }
        
        except Exception as e:
            logger.error(f"HTML to Markdown conversion failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def sanitize_and_convert(self, html: str, body_width: int = 0) -> dict[str, Any]:
        """
        One-shot: Sanitize HTML then convert to Markdown.
        
        Args:
            html: Raw HTML string
            body_width: Markdown text wrap width
        
        Returns:
            Result dict with {"ok": bool, "markdown": str, "removed": dict}
        """
        # Step 1: Sanitize
        sanitize_result = self.sanitize_html(html)
        if not sanitize_result["ok"]:
            return sanitize_result
        
        clean_html = sanitize_result["html"]
        
        # Step 2: Convert to Markdown
        markdown_result = self.html_to_markdown(clean_html, body_width)
        if not markdown_result["ok"]:
            return markdown_result
        
        # Combine results
        return {
            "ok": True,
            "markdown": markdown_result["markdown"],
            "removed": sanitize_result["removed"],
            "length": markdown_result["length"],
            "method": markdown_result.get("method", "unknown")
        }


def quick_sanitize(html: str) -> str:
    """
    Quick helper to sanitize HTML.
    
    Args:
        html: Raw HTML string
    
    Returns:
        Sanitized HTML string
    """
    sanitizer = HTMLSanitizer()
    result = sanitizer.sanitize_html(html)
    return result.get("html", "") if result["ok"] else ""


def quick_markdown(html: str) -> str:
    """
    Quick helper to convert HTML to Markdown.
    
    Args:
        html: HTML string
    
    Returns:
        Markdown string
    """
    sanitizer = HTMLSanitizer()
    result = sanitizer.sanitize_and_convert(html)
    return result.get("markdown", "") if result["ok"] else ""
