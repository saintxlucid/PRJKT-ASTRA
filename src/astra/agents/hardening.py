"""
Agent hardening with risk scoring, dry-run mode, and consent flows.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk classification for agent actions."""
    LOW = 0        # Safe read operations
    NORMAL = 1     # Safe local operations
    HIGH = 2       # Write/delete operations
    CRITICAL = 3   # Dangerous system operations


@dataclass
class AgentAction:
    """Single agent action for risk assessment."""
    tool_name: str
    arguments: dict[str, Any]
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
        }


class OperatorRiskScorer:
    """Score risk level for agent actions (0-10 scale)."""

    # Tool baseline risks
    TOOL_RISKS = {
        "read_file": RiskLevel.LOW,
        "list_dir": RiskLevel.LOW,
        "search_knowledge": RiskLevel.LOW,
        "get_cpu_info": RiskLevel.LOW,
        "get_memory_info": RiskLevel.LOW,
        "write_file": RiskLevel.HIGH,
        "create_file": RiskLevel.HIGH,
        "delete_file": RiskLevel.CRITICAL,
        "execute_command": RiskLevel.CRITICAL,
        "run_subprocess": RiskLevel.CRITICAL,
        "network_request": RiskLevel.HIGH,
        "api_call": RiskLevel.HIGH,
    }

    # Argument patterns that escalate risk
    ESCALATION_PATTERNS = {
        "system_path": ["/etc", "/sys", "/proc", "C:\\Windows", "C:\\System"],
        "wildcard": ["*", "**"],
        "recursive": ["recursive", "-r", "--recursive"],
    }

    def score_action(self, action: AgentAction) -> tuple[RiskLevel, str]:
        """Score risk of action. Returns (RiskLevel, reason)."""

        # 1. Base tool risk
        base_risk = self.TOOL_RISKS.get(action.tool_name, RiskLevel.HIGH)

        # 2. Check argument patterns for escalation
        reason = f"Base tool risk: {base_risk.name}"

        for _arg_key, arg_value in action.arguments.items():
            if isinstance(arg_value, str):
                # Check system paths
                for sys_path in self.ESCALATION_PATTERNS["system_path"]:
                    if sys_path.lower() in arg_value.lower():
                        return RiskLevel.CRITICAL, f"System path detected: {sys_path}"

                # Check wildcards
                if "*" in arg_value or "**" in arg_value:
                    base_risk = RiskLevel.CRITICAL
                    reason += " | Wildcard pattern detected"

        return base_risk, reason


class DryRunMode:
    """Simulate tool execution without side effects."""

    def __init__(self):
        self.execution_log = []

    async def simulate_execution(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate tool execution and return simulated result."""

        simulated_result = {
            "status": "simulated",
            "tool_name": tool_name,
            "arguments": arguments,
            "simulated_result": self._simulate_output(tool_name, arguments),
            "timestamp": datetime.now().isoformat(),
        }

        self.execution_log.append(simulated_result)
        logger.info(f"[DRY-RUN] {tool_name}({arguments}) → simulated")

        return simulated_result

    def _simulate_output(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> Any:
        """Generate simulated output based on tool."""

        if tool_name.startswith("read"):
            return "Simulated file content (12 lines)"
        elif tool_name.startswith("list"):
            return ["file1.txt", "file2.txt", "subdir/"]
        elif tool_name.startswith("write"):
            return {"status": "would_write", "bytes": 256}
        elif tool_name.startswith("delete"):
            return {"status": "would_delete", "files": 1}
        else:
            return {"status": "simulated", "result": "N/A"}


class ConsentFlowManager:
    """Operator approval workflow for agent actions."""

    # Consent policies per risk level
    CONSENT_POLICY = {
        RiskLevel.LOW: "silent",          # No approval needed
        RiskLevel.NORMAL: "auto_approve", # Auto-approve + log
        RiskLevel.HIGH: "require_consent",# Require operator approval
        RiskLevel.CRITICAL: "always",     # Always require explicit approval
    }

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds
        self.pending_approvals: dict[str, asyncio.Event] = {}
        self.approvals: dict[str, bool] = {}

    async def request_consent(
        self,
        action_id: str,
        action: AgentAction,
        risk_level: RiskLevel
    ) -> bool:
        """Request operator consent for action."""

        policy = self.CONSENT_POLICY.get(risk_level, "require_consent")

        if policy == "silent":
            logger.info(f"[CONSENT] {action_id}: Silent approval (LOW risk)")
            return True

        elif policy == "auto_approve":
            logger.info(f"[CONSENT] {action_id}: Auto-approved (NORMAL risk) | {action.tool_name}")
            return True

        elif policy == "require_consent":
            logger.warning(f"[CONSENT] {action_id}: Requires approval (HIGH risk) | {action.tool_name}")
            return await self._wait_for_approval(action_id)

        elif policy == "always":
            logger.critical(f"[CONSENT] {action_id}: CRITICAL - Always requires explicit approval")
            return await self._wait_for_approval(action_id, require_explicit=True)

        return False

    async def _wait_for_approval(
        self,
        action_id: str,
        require_explicit: bool = False
    ) -> bool:
        """Wait for operator approval (with timeout)."""

        logger.warning(f"Waiting for operator approval: {action_id}")

        # In production, this would integrate with operator console
        # For now, log and auto-approve after timeout for testing
        await asyncio.sleep(min(5, self.timeout_seconds))

        # Timeout reached - deny by default for CRITICAL, approve for HIGH
        approved = not require_explicit
        self.approvals[action_id] = approved

        logger.info(f"Approval for {action_id}: {'APPROVED' if approved else 'DENIED'}")
        return approved


class AuditLogger:
    """JSON audit trail for all agent actions."""

    def __init__(self, log_path: str = "./logs/agent_audit.jsonl"):
        self.log_path = log_path
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Create log file if it doesn't exist."""
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def log_action(
        self,
        action: AgentAction,
        risk_level: RiskLevel,
        approved: bool,
        result: Any | None = None
    ) -> None:
        """Log action to JSON audit trail."""

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action.to_dict(),
            "risk_level": risk_level.name,
            "approved": approved,
            "result": str(result)[:200] if result else None,
        }

        # Append to JSONL file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')

        logger.debug(f"Audit logged: {action.tool_name} → {risk_level.name}")

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve recent audit entries."""

        entries = []
        try:
            with open(self.log_path) as f:
                for line in f.readlines()[-limit:]:
                    entries.append(json.loads(line))
        except FileNotFoundError:
            pass

        return entries
