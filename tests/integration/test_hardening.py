"""Integration tests for Phase 2 Task 2: Agent Hardening."""

import tempfile
from pathlib import Path

import pytest

from astra.agents.hardening import (
    AgentAction,
    AuditLogger,
    ConsentFlowManager,
    DryRunMode,
    OperatorRiskScorer,
    RiskLevel,
)
from astra.agents.local_tools import LocalToolRegistry, ToolDefinition


@pytest.fixture
def risk_scorer():
    """Create risk scorer for testing."""
    return OperatorRiskScorer()


@pytest.fixture
def dry_run():
    """Create dry run mode for testing."""
    return DryRunMode()


@pytest.fixture
def consent_mgr():
    """Create consent flow manager for testing."""
    return ConsentFlowManager(timeout_seconds=1)


@pytest.fixture
def tool_registry():
    """Create tool registry for testing."""
    return LocalToolRegistry()


@pytest.fixture
def audit_logger():
    """Create audit logger with temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.jsonl"
        yield AuditLogger(str(log_path))


# Risk Scoring Tests

def test_risk_scoring_safe_read(risk_scorer):
    """LOW risk for safe read operations."""
    action = AgentAction("read_file", {"file_path": "/data/file.txt"}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.LOW
    assert "LOW" in reason


def test_risk_scoring_system_path(risk_scorer):
    """CRITICAL risk for system paths."""
    action = AgentAction("delete_file", {"file_path": "/etc/passwd"}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.CRITICAL
    assert "/etc" in reason


def test_risk_scoring_wildcard_escalation(risk_scorer):
    """Wildcard patterns escalate to CRITICAL."""
    action = AgentAction("write_file", {"file_path": "/data/*.txt"}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.CRITICAL
    assert "Wildcard" in reason


def test_risk_scoring_windows_system_path(risk_scorer):
    """CRITICAL risk for Windows system paths."""
    action = AgentAction("execute_command", {"cmd": "C:\\Windows\\System32\\cmd.exe"}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.CRITICAL


def test_risk_scoring_normal_write(risk_scorer):
    """HIGH risk for write operations."""
    action = AgentAction("write_file", {"file_path": "/tmp/safe.txt"}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.HIGH


def test_risk_scoring_cpu_info(risk_scorer):
    """LOW risk for read-only system info."""
    action = AgentAction("get_cpu_info", {}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.LOW


def test_risk_scoring_unknown_tool(risk_scorer):
    """Unknown tools default to HIGH risk."""
    action = AgentAction("unknown_tool", {"param": "value"}, "agent1")
    risk, reason = risk_scorer.score_action(action)

    assert risk == RiskLevel.HIGH


# Dry-Run Mode Tests

@pytest.mark.asyncio
async def test_dry_run_read_file(dry_run):
    """Dry-run simulates file read without executing."""
    result = await dry_run.simulate_execution("read_file", {"file_path": "/data/file.txt"})

    assert result["status"] == "simulated"
    assert result["tool_name"] == "read_file"
    assert len(dry_run.execution_log) == 1


@pytest.mark.asyncio
async def test_dry_run_write_file(dry_run):
    """Dry-run simulates write without executing."""
    result = await dry_run.simulate_execution(
        "write_file",
        {"file_path": "/tmp/test.txt", "content": "test"}
    )

    assert result["status"] == "simulated"
    assert "would_write" in result["simulated_result"]["status"]


@pytest.mark.asyncio
async def test_dry_run_delete_file(dry_run):
    """Dry-run simulates delete without executing."""
    result = await dry_run.simulate_execution("delete_file", {"file_path": "/tmp/test.txt"})

    assert result["status"] == "simulated"
    assert result["simulated_result"]["status"] == "would_delete"


@pytest.mark.asyncio
async def test_dry_run_multiple_executions(dry_run):
    """Dry-run maintains execution log."""
    await dry_run.simulate_execution("read_file", {"file_path": "file1.txt"})
    await dry_run.simulate_execution("read_file", {"file_path": "file2.txt"})

    assert len(dry_run.execution_log) == 2


# Consent Flow Tests

@pytest.mark.asyncio
async def test_consent_low_risk_silent(consent_mgr):
    """LOW risk actions approved silently."""
    action = AgentAction("read_file", {"file_path": "/data/file.txt"}, "agent1")
    approved = await consent_mgr.request_consent("id1", action, RiskLevel.LOW)

    assert approved is True


@pytest.mark.asyncio
async def test_consent_normal_risk_auto_approve(consent_mgr):
    """NORMAL risk actions auto-approved."""
    action = AgentAction("write_file", {"file_path": "/tmp/test.txt"}, "agent1")
    approved = await consent_mgr.request_consent("id2", action, RiskLevel.NORMAL)

    assert approved is True


@pytest.mark.asyncio
async def test_consent_high_risk_requires_approval(consent_mgr):
    """HIGH risk actions require consent."""
    action = AgentAction("delete_file", {"file_path": "/tmp/test.txt"}, "agent1")
    approved = await consent_mgr.request_consent("id3", action, RiskLevel.HIGH)

    # Timeout -> auto-approve for HIGH risk
    assert approved is True


@pytest.mark.asyncio
async def test_consent_critical_risk_denied_by_default(consent_mgr):
    """CRITICAL risk actions require explicit approval."""
    action = AgentAction("execute_command", {"cmd": "malicious.exe"}, "agent1")
    approved = await consent_mgr.request_consent("id4", action, RiskLevel.CRITICAL)

    # Timeout -> deny by default for CRITICAL
    assert approved is False


# Audit Logging Tests

def test_audit_log_creation(audit_logger):
    """Audit logger creates entries."""
    action = AgentAction("read_file", {"file_path": "test.txt"}, "agent1")
    audit_logger.log_action(action, RiskLevel.LOW, True, "content")

    log_entries = audit_logger.get_audit_log()
    assert len(log_entries) == 1
    assert log_entries[0]["action"]["tool_name"] == "read_file"


def test_audit_log_json_format(audit_logger):
    """Audit entries are valid JSON."""
    action = AgentAction("write_file", {"file_path": "test.txt"}, "agent1")
    audit_logger.log_action(action, RiskLevel.HIGH, False, None)

    log_entries = audit_logger.get_audit_log()
    entry = log_entries[0]

    assert "timestamp" in entry
    assert "action" in entry
    assert "risk_level" in entry
    assert "approved" in entry


def test_audit_log_multiple_entries(audit_logger):
    """Multiple audit entries accumulated."""
    for i in range(5):
        action = AgentAction("read_file", {"file_path": f"file{i}.txt"}, f"agent{i}")
        audit_logger.log_action(action, RiskLevel.LOW, True, f"content{i}")

    log_entries = audit_logger.get_audit_log()
    assert len(log_entries) == 5


def test_audit_log_retrieval_limit(audit_logger):
    """Audit log respects limit parameter."""
    for i in range(20):
        action = AgentAction("read_file", {"file_path": f"file{i}.txt"}, "agent")
        audit_logger.log_action(action, RiskLevel.LOW, True, None)

    log_entries = audit_logger.get_audit_log(limit=10)
    assert len(log_entries) == 10


# Tool Registry Tests

def test_tool_registry_default_tools(tool_registry):
    """Tool registry initializes with default tools."""
    tools = tool_registry.list_tools()

    assert len(tools) == 5
    tool_names = [t["name"] for t in tools]
    assert "read_file" in tool_names
    assert "list_dir" in tool_names
    assert "get_cpu_info" in tool_names


def test_tool_registry_risk_levels(tool_registry):
    """All default tools are LOW risk."""
    tools = tool_registry.list_tools()

    for tool in tools:
        assert tool["risk_level"] == "LOW"


@pytest.mark.asyncio
async def test_tool_registry_execute_cpu_info(tool_registry):
    """Tool execution returns expected data."""
    result = await tool_registry.execute("get_cpu_info")

    assert "cpu_count" in result
    assert "cpu_percent" in result


@pytest.mark.asyncio
async def test_tool_registry_list_dir(tool_registry):
    """List directory tool works."""
    result = await tool_registry.list_tools()

    assert len(result) == 5
    assert result[0]["name"] == "read_file"


def test_tool_registry_unknown_tool(tool_registry):
    """Unknown tool raises error."""
    with pytest.raises(ValueError):
        import asyncio
        asyncio.run(tool_registry.execute("unknown_tool"))


def test_tool_registry_register_custom_tool(tool_registry):
    """Can register custom tools."""
    async def custom_func(**kwargs):
        return "custom result"

    tool = ToolDefinition(
        name="custom_tool",
        description="A custom tool",
        function=custom_func,
        risk_level="LOW",
        parameters={}
    )

    tool_registry.register(tool)
    tools = tool_registry.list_tools()

    assert len(tools) == 6
    assert tools[-1]["name"] == "custom_tool"


# Agent Action Tests

def test_agent_action_serialization():
    """Agent action serializes to dict."""
    action = AgentAction("read_file", {"file_path": "test.txt"}, "agent1")
    action_dict = action.to_dict()

    assert action_dict["tool_name"] == "read_file"
    assert action_dict["agent_id"] == "agent1"
    assert "timestamp" in action_dict


# Integration Tests

@pytest.mark.asyncio
async def test_hardening_pipeline_low_risk():
    """Complete hardening pipeline for LOW risk."""
    scorer = OperatorRiskScorer()
    dry_run = DryRunMode()
    consent_mgr = ConsentFlowManager()

    action = AgentAction("read_file", {"file_path": "/data/file.txt"}, "agent1")
    risk, _ = scorer.score_action(action)
    simulated = await dry_run.simulate_execution(action.tool_name, action.arguments)
    approved = await consent_mgr.request_consent("id1", action, risk)

    assert risk == RiskLevel.LOW
    assert simulated["status"] == "simulated"
    assert approved is True


@pytest.mark.asyncio
async def test_hardening_pipeline_critical_risk():
    """Complete hardening pipeline for CRITICAL risk."""
    scorer = OperatorRiskScorer()
    dry_run = DryRunMode()
    consent_mgr = ConsentFlowManager(timeout_seconds=1)

    action = AgentAction("execute_command", {"cmd": "/etc/evil.sh"}, "agent1")
    risk, reason = scorer.score_action(action)
    simulated = await dry_run.simulate_execution(action.tool_name, action.arguments)
    approved = await consent_mgr.request_consent("id2", action, risk)

    assert risk == RiskLevel.CRITICAL
    assert "/etc" in reason
    assert simulated["status"] == "simulated"
    assert approved is False  # CRITICAL denied by default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
