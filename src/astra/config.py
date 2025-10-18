"""Convenience accessors for global ASTRA configuration."""

from __future__ import annotations

from .models.config import Settings, get_settings, reload_settings

# Expose a module-level settings instance to mirror existing usage expectations.
settings: Settings = get_settings()

__all__ = ["Settings", "get_settings", "reload_settings", "settings"]
