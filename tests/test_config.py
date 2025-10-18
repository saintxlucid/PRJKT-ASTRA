"""Test configuration for ASTRA test suite."""
import os
import pytest
from pathlib import Path
from prometheus_client import REGISTRY, CollectorRegistry

# Add src directory to Python path
src_path = Path(__file__).resolve().parents[1] / "src"
if str(src_path) not in os.environ["PYTHONPATH"].split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join([str(src_path), os.environ.get("PYTHONPATH", "")])

@pytest.fixture(scope="session")
def test_workspace(tmp_path_factory):
    """Create a temporary workspace for tests."""
    path = tmp_path_factory.mktemp("astra_test_workspace")
    return path

@pytest.fixture(autouse=True)
def _reset_metrics_registry():
    """Reset Prometheus metrics registry before each test."""
    # Store old registry
    old_registry = REGISTRY
    # Create new registry
    new_registry = CollectorRegistry()
    # Update global registry
    REGISTRY = new_registry
    # Run test
    yield
    # Restore old registry
    REGISTRY = old_registry