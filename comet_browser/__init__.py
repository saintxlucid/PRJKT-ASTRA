# comet_browser/__init__.py
"""
COMET Browser - DOM/Visual/Hybrid browser automation for ASTRA.
"""

from comet_browser.dom.driver import DOMDriver
from comet_browser.dom.sanitizer import sanitize_html, html_to_markdown

__all__ = ["DOMDriver", "sanitize_html", "html_to_markdown"]
