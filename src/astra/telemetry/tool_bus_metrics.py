"""
Tool Bus metrics collection and export.

Collects Prometheus metrics for tool execution, consent decisions,
and API usage patterns.
"""

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

# Tool Execution Metrics
TOOL_EXECUTION_COUNTER = Counter(
    "astra_tool_executions_total",
    "Total number of tool executions",
    ["tool", "status"]  # status: success, error, blocked
)

TOOL_EXECUTION_DURATION = Histogram(
    "astra_tool_execution_duration_seconds",
    "Duration of tool executions in seconds",
    ["tool"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Consent Metrics
CONSENT_REQUESTS = Counter(
    "astra_consent_requests_total",
    "Total number of consent requests",
    ["tool"]
)

CONSENT_DECISIONS = Counter(
    "astra_consent_decisions_total",
    "Total number of consent decisions",
    ["tool", "decision"]  # decision: approved, denied
)

PENDING_CONSENT_REQUESTS = Gauge(
    "astra_pending_consent_requests",
    "Number of consent requests awaiting decision",
)

# Policy Metrics
POLICY_CHECKS = Counter(
    "astra_policy_checks_total",
    "Total number of policy checks",
    ["tool", "result"]  # result: allowed, blocked
)

# Token Metrics
TOKEN_VALIDATIONS = Counter(
    "astra_token_validations_total",
    "Total number of token validations",
    ["status"]  # status: valid, invalid
)

# API Usage Metrics
API_REQUESTS = Counter(
    "astra_api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status_code"]
)

API_REQUEST_DURATION = Histogram(
    "astra_api_request_duration_seconds",
    "Duration of API requests in seconds",
    ["endpoint", "method"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)


class ToolBusMetrics:
    """Metric collection for Tool Bus operations."""

    @staticmethod
    def record_tool_execution(tool_name: str, success: bool, duration: float) -> None:
        """Record tool execution metrics."""
        status = "success" if success else "error"
        TOOL_EXECUTION_COUNTER.labels(tool=tool_name, status=status).inc()
        TOOL_EXECUTION_DURATION.labels(tool=tool_name).observe(duration)

    @staticmethod
    def record_policy_check(tool_name: str, allowed: bool) -> None:
        """Record policy check result."""
        result = "allowed" if allowed else "blocked"
        POLICY_CHECKS.labels(tool=tool_name, result=result).inc()

    @staticmethod
    def record_consent_request(tool_name: str) -> None:
        """Record new consent request."""
        CONSENT_REQUESTS.labels(tool=tool_name).inc()
        PENDING_CONSENT_REQUESTS.inc()

    @staticmethod
    def record_consent_decision(tool_name: str, approved: bool) -> None:
        """Record consent decision."""
        decision = "approved" if approved else "denied"
        CONSENT_DECISIONS.labels(tool=tool_name, decision=decision).inc()
        PENDING_CONSENT_REQUESTS.dec()

    @staticmethod
    def record_token_validation(valid: bool) -> None:
        """Record token validation result."""
        status = "valid" if valid else "invalid"
        TOKEN_VALIDATIONS.labels(status=status).inc()

    @staticmethod
    def record_api_request(endpoint: str, method: str, status_code: int, duration: float) -> None:
        """Record API request metrics."""
        API_REQUESTS.labels(
            endpoint=endpoint,
            method=method,
            status_code=status_code
        ).inc()
        
        API_REQUEST_DURATION.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)

    @staticmethod
    def get_metrics_report() -> Dict[str, Any]:
        """Get current metrics as a dictionary for reporting."""
        from prometheus_client import REGISTRY
        
        def get_metrics_for_name(metric: Counter) -> dict:
            """Get all samples for a given metric."""
            samples = []
            print(f"Checking metric {metric._name}:")
            for sample in metric._metrics.values():
                value = sample._value.get()
                if value != 0:  # Only include non-zero samples
                    print(f"  Found sample with labels={sample._labelvalues} value={value}")
                    samples.append({
                        "labels": sample._labelvalues,
                        "value": value
                    })
            return {"samples": samples}
            
        # Get tool execution metrics
        success_total = 0
        error_total = 0
        tool_metrics = get_metrics_for_name(TOOL_EXECUTION_COUNTER)
        for sample in tool_metrics["samples"]:
            if "success" == sample["labels"][1]:  # status is second label
                success_total += sample["value"]
            elif "error" == sample["labels"][1]:  # status is second label
                error_total += sample["value"]
        
        # Get consent metrics
        approved_total = 0
        denied_total = 0
        consent_metrics = get_metrics_for_name(CONSENT_DECISIONS)
        for sample in consent_metrics["samples"]:
            if "approved" == sample["labels"][1]:  # decision is second label
                approved_total += sample["value"]
            elif "denied" == sample["labels"][1]:  # decision is second label
                denied_total += sample["value"]
        
        # Get policy check metrics        
        allowed_total = 0
        blocked_total = 0
        policy_metrics = get_metrics_for_name(POLICY_CHECKS)
        for sample in policy_metrics["samples"]:
            if "allowed" == sample["labels"][1]:  # result is second label
                allowed_total += sample["value"]
            elif "blocked" == sample["labels"][1]:  # result is second label
                blocked_total += sample["value"]
                    
        return {
            "tool_executions": {
                "success": success_total,
                "error": error_total
            },
            "consent": {
                "pending": PENDING_CONSENT_REQUESTS._value.get(),
                "approved": approved_total,
                "denied": denied_total
            },
            "policy": {
                "allowed": allowed_total,
                "blocked": blocked_total
            }
        }