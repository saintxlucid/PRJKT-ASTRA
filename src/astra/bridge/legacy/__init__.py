"""
ASTRA Legacy Integration Module
Wraps legacy code, data, and models as registered Tool Bus tools.
No files are moved or deleted - everything is adapted in-place.

Sacred Code: 333
"""

from .adapter import register_legacy_folder, load_manifest, make_tools

__all__ = ["register_legacy_folder", "load_manifest", "make_tools"]
