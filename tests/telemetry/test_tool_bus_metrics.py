"""
Test suite for Tool Bus metrics collection.

Tests the collection and reporting of metrics for tool execution,
consent decisions, and API usage.
"""

import pytest
from unittest.mock import MagicMock, patch
from prometheus_client import REGISTRY

from astra.telemetry.tool_bus_metrics import (
    ToolBusMetrics,
    TOOL_EXECUTION_COUNTER,
    CONSENT_REQUESTS,
    CONSENT_DECISIONS,
    POLICY_CHECKS
)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset all metrics between tests."""
    # Clear all metrics from default registry
    from prometheus_client import REGISTRY
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
    
    # Re-register our metrics
    for metric in [TOOL_EXECUTION_COUNTER, CONSENT_REQUESTS, POLICY_CHECKS,
                  CONSENT_DECISIONS]:  # Add CONSENT_DECISIONS
        # Reset values
        for sample in metric._metrics.values():
            sample._value.set(0)
        REGISTRY.register(metric)


def test_tool_execution_metrics(reset_metrics):
    """Test recording of tool execution metrics."""
    # Record successful execution
    ToolBusMetrics.record_tool_execution("test_tool", True, 1.5)
    
    # Record failed execution
    ToolBusMetrics.record_tool_execution("test_tool", False, 0.5)
    
    # Check counter values
    success_count = TOOL_EXECUTION_COUNTER.labels(
        tool="test_tool",
        status="success"
    )._value.get()
    
    error_count = TOOL_EXECUTION_COUNTER.labels(
        tool="test_tool",
        status="error"
    )._value.get()
    
    assert success_count == 1, "Expected 1 successful execution"
    assert error_count == 1, "Expected 1 failed execution"


def test_consent_metrics(reset_metrics):
    """Test recording of consent metrics."""
    # Record consent request
    ToolBusMetrics.record_consent_request("risky_tool")
    
    # Record approval
    ToolBusMetrics.record_consent_decision("risky_tool", True)
    
    # Record denial
    ToolBusMetrics.record_consent_decision("risky_tool", False)
    
    # Check metrics
    request_count = CONSENT_REQUESTS.labels(
        tool="risky_tool"
    )._value.get()
    
    assert request_count == 1, "Expected 1 consent request"
    
    report = ToolBusMetrics.get_metrics_report()
    assert report["consent"]["approved"] == 1, "Expected 1 approval"
    assert report["consent"]["denied"] == 1, "Expected 1 denial"


def test_policy_check_metrics(reset_metrics):
    """Test recording of policy check metrics."""
    # Record allowed check
    ToolBusMetrics.record_policy_check("safe_tool", True)
    
    # Record blocked check
    ToolBusMetrics.record_policy_check("unsafe_tool", False)
    
    # Get report
    report = ToolBusMetrics.get_metrics_report()
    
    assert report["policy"]["allowed"] == 1, "Expected 1 allowed check"
    assert report["policy"]["blocked"] == 1, "Expected 1 blocked check"


def test_metrics_report_generation(reset_metrics):
    """Test comprehensive metrics report generation."""
    # Record various metrics
    ToolBusMetrics.record_tool_execution("tool1", True, 1.0)
    ToolBusMetrics.record_tool_execution("tool2", False, 0.5)
    ToolBusMetrics.record_consent_request("tool1")
    ToolBusMetrics.record_consent_decision("tool1", True)
    ToolBusMetrics.record_policy_check("tool1", True)
    ToolBusMetrics.record_policy_check("tool2", False)
    
    # Get complete report
    report = ToolBusMetrics.get_metrics_report()
    
    # Verify all sections
    assert report["tool_executions"]["success"] == 1
    assert report["tool_executions"]["error"] == 1
    assert report["consent"]["approved"] == 1
    assert report["consent"]["denied"] == 0
    assert report["policy"]["allowed"] == 1
    assert report["policy"]["blocked"] == 1