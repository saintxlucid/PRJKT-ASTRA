"""Pytest configuration for ASTRA tests."""

from __future__ import annotations

import os
import pathlib
import sys

import pytest
from prometheus_client import REGISTRY, CollectorRegistry

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def test_registry():
    """Create a test registry"""
    return CollectorRegistry()

@pytest.fixture(autouse=True, scope="session")
def metrics_manager(test_registry):
    """Create a MetricsManager with test registry"""
    from astra.core.metrics import MetricsManager
    return MetricsManager(registry=test_registry)

@pytest.fixture(autouse=True, scope="session")
def _relaxed_limits_for_tests(metrics_manager):
    """Relax rate limits and concurrency for test environment."""
    
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
    os.environ.setdefault("ASTRA_RATE_LIMIT_PER_MIN", "100000")
    os.environ.setdefault("ASTRA_CONCURRENCY_INFLIGHT", "999")
    os.environ.setdefault("ASTRA_CONCURRENCY_QUEUE", "999")


@pytest.fixture(autouse=True)
def _freeze_time():
    """Freeze time for consistent test results."""
    try:
        from freezegun import freeze_time
        with freeze_time("2025-10-16 12:00:00"):
            yield
    except ImportError:
        # freezegun not available, skip time freezing
        yield
