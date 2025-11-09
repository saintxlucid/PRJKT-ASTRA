"""
ASTRA Policy Engine - Mission Alignment & Governance
=====================================================

Validates routing and tool execution against mission alignment.
Emits audit logs for compliance and observability.

Author: ASTRA Governance Team
Created: 2025-11-03
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from ..llm.types import AuditLogEntry, GenerateRequest, RouteDecision


logger = logging.getLogger(__name__)


# ============================================================================
# POLICY RULES
# ============================================================================

class PolicyRule:
    """Base class for policy rules."""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    def evaluate(self, request: GenerateRequest, decision: RouteDecision) -> tuple[bool, str]:
        """
        Evaluate policy rule.

        Returns:
            (allowed, reason)
        """
        raise NotImplementedError


class MaxLatencyPolicy(PolicyRule):
    """Enforce maximum latency budget."""

    def __init__(self, max_latency_ms: int = 30000):
        super().__init__("max_latency")
        self.max_latency_ms = max_latency_ms

    def evaluate(self, request: GenerateRequest, decision: RouteDecision) -> tuple[bool, str]:
        if request.latency_budget_ms and request.latency_budget_ms > self.max_latency_ms:
            return False, f"Latency budget {request.latency_budget_ms}ms exceeds max {self.max_latency_ms}ms"
        return True, "OK"


class ModelAvailabilityPolicy(PolicyRule):
    """Check if selected model is available."""

    def __init__(self, available_models: list[str]):
        super().__init__("model_availability")
        self.available_models = available_models

    def evaluate(self, request: GenerateRequest, decision: RouteDecision) -> tuple[bool, str]:
        if decision.model not in self.available_models:
            return False, f"Model {decision.model} not available"
        return True, "OK"


class ComplexityThresholdPolicy(PolicyRule):
    """Block requests below minimum complexity threshold."""

    def __init__(self, min_complexity: float = 0.0):
        super().__init__("complexity_threshold")
        self.min_complexity = min_complexity

    def evaluate(self, request: GenerateRequest, decision: RouteDecision) -> tuple[bool, str]:
        if decision.complexity_score < self.min_complexity:
            return False, f"Complexity {decision.complexity_score} below threshold {self.min_complexity}"
        return True, "OK"


class SoulAlignmentPolicy(PolicyRule):
    """Enforce soul alignment requirements."""

    def __init__(self, require_alignment: bool = True):
        super().__init__("soul_alignment")
        self.require_alignment = require_alignment

    def evaluate(self, request: GenerateRequest, decision: RouteDecision) -> tuple[bool, str]:
        if not self.require_alignment:
            return True, "OK"

        if decision.soul_alignment == "misaligned":
            return False, "Request misaligned with mission values"
        elif decision.soul_alignment == "grey":
            return True, "Grey zone - proceeding with caution"
        return True, "OK"


# ============================================================================
# POLICY ENGINE
# ============================================================================

class AstraPolicyEngine:
    """Central policy enforcement and audit logging."""

    def __init__(self, audit_log_path: Path | None = None):
        """
        Initialize policy engine.

        Args:
            audit_log_path: Path to audit log file (default: logs/audit.jsonl)
        """
        if audit_log_path is None:
            audit_log_path = Path("logs/audit.jsonl")

        self.audit_log_path = audit_log_path
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Default policies
        self.policies: list[PolicyRule] = [
            MaxLatencyPolicy(max_latency_ms=30000),
            ModelAvailabilityPolicy(available_models=[
                "deepseek-r1-distill-qwen-14b",
                "qwen2.5-14b-instruct",
                "phi-4-mini",
                "mistral-large-2",
                "llama-3.2-vision-11b",
                "qwen2-vl-7b",
                "whisper-large-v3",
            ]),
            SoulAlignmentPolicy(require_alignment=True),
        ]

    def add_policy(self, policy: PolicyRule):
        """Add custom policy rule."""
        self.policies.append(policy)

    def validate_request(
        self,
        request: GenerateRequest,
        decision: RouteDecision
    ) -> tuple[bool, list[str]]:
        """
        Validate request against all policies.

        Returns:
            (allowed, reasons)
        """
        reasons = []

        for policy in self.policies:
            if not policy.enabled:
                continue

            allowed, reason = policy.evaluate(request, decision)
            if not allowed:
                reasons.append(f"{policy.name}: {reason}")

        return (len(reasons) == 0, reasons)

    def emit_audit_log(
        self,
        request_id: str,
        user_id: str | None,
        decision: RouteDecision,
        result: str,
        reason: str | None = None,
        latency_ms: float = 0.0,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ):
        """
        Emit structured audit log entry.

        Args:
            request_id: Unique request ID
            user_id: User identifier (if available)
            decision: Routing decision
            result: success/blocked/grey
            reason: Optional reason for block/grey
            latency_ms: Request latency
            tokens: Total tokens processed
            cost_usd: Cost in USD
        """
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            request_id=request_id,
            user_id=user_id,
            model_selected=decision.model,
            policy_rules_triggered=decision.rules_matched,
            soul_alignment=decision.soul_alignment or "unknown",
            result=result,
            reason=reason,
            latency_ms=latency_ms,
            tokens=tokens,
            cost_usd=cost_usd,
        )

        # Write to JSONL file
        with open(self.audit_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp.isoformat(),
                "request_id": entry.request_id,
                "user_id": entry.user_id,
                "model_selected": entry.model_selected,
                "policy_rules_triggered": entry.policy_rules_triggered,
                "soul_alignment": entry.soul_alignment,
                "result": entry.result,
                "reason": entry.reason,
                "latency_ms": entry.latency_ms,
                "tokens": entry.tokens,
                "cost_usd": entry.cost_usd,
            }) + '\n')

        logger.info(f"Audit log emitted: {result} | {decision.model} | {request_id}")

    def query_audit_logs(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        result_filter: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Query audit logs.

        Args:
            start_time: Filter logs after this time
            end_time: Filter logs before this time
            result_filter: Filter by result (success/blocked/grey)
            limit: Maximum number of results

        Returns:
            List of audit log entries
        """
        if not self.audit_log_path.exists():
            return []

        results = []
        with open(self.audit_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if len(results) >= limit:
                    break

                entry = json.loads(line.strip())

                # Apply filters
                timestamp = datetime.fromisoformat(entry['timestamp'])
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                if result_filter and entry['result'] != result_filter:
                    continue

                results.append(entry)

        return results


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "PolicyRule",
    "MaxLatencyPolicy",
    "ModelAvailabilityPolicy",
    "ComplexityThresholdPolicy",
    "SoulAlignmentPolicy",
    "AstraPolicyEngine",
]
