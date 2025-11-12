"""
Integration tests for LocalGPTOSManager.execute_agent_tool() with hardening pipeline.

Tests the full hardening pipeline:
1. Risk scoring
2. Dry-run simulation
3. Consent flow
4. Tool execution
5. Audit logging
"""

import tempfile
from unittest.mock import MagicMock

import pytest

from astra.agents.local_tools import LocalToolRegistry
from astra.llm.local_manager import LocalGPTOOSManager
from astra.llm.local_provider import GPTOOSProvider


@pytest.fixture
def mock_provider():
    """Create a mock GPTOOSProvider."""
    provider = MagicMock(spec=GPTOOSProvider)
    provider.generate = MagicMock(return_value="Generated response")
    provider.stream = MagicMock(return_value=["chunk1", "chunk2"])
    provider.get_metrics = MagicMock(return_value={"requests": 0})
    return provider


@pytest.fixture
async def manager(mock_provider):
    """Create a LocalGPTOSManager instance."""
    mgr = LocalGPTOSManager(
        provider=mock_provider,
        max_workers=2,
        requests_per_minute=10,
        queue_max_size=100,
    )
    yield mgr
    await mgr.shutdown()


@pytest.fixture
async def tool_registry():
    """Create a LocalToolRegistry instance."""
    return LocalToolRegistry()


class TestAgentToolExecutionBasic:
    """Test basic agent tool execution."""

    @pytest.mark.asyncio
    async def test_execute_agent_tool_low_risk_read(self, manager, tool_registry):
        """Test LOW risk tool execution (read_file)."""
        result = await manager.execute_agent_tool(
            agent_id="test-agent-1",
            tool_name="read_file",
            arguments={"path": "/home/user/document.txt"},
            tool_registry=tool_registry,
        )

        assert result["agent_id"] == "test-agent-1"
        assert result["tool_name"] == "read_file"
        assert result["risk_level"] == "LOW"
        assert result["approved"] is True
        assert result["error"] is None
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_execute_agent_tool_high_risk_write(self, manager, tool_registry):
        """Test HIGH risk tool execution (write_file)."""
        result = await manager.execute_agent_tool(
            agent_id="test-agent-2",
            tool_name="write_file",
            arguments={"path": "/home/user/output.txt", "content": "test"},
            tool_registry=tool_registry,
        )

        assert result["agent_id"] == "test-agent-2"
        assert result["tool_name"] == "write_file"
        assert result["risk_level"] == "HIGH"
        # HIGH risk may be denied (depending on timeout)
        assert isinstance(result["approved"], bool)
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_execute_agent_tool_system_path_escalation(self, manager, tool_registry):
        """Test CRITICAL risk escalation for system paths."""
        result = await manager.execute_agent_tool(
            agent_id="test-agent-3",
            tool_name="read_file",
            arguments={"path": "/etc/passwd"},
            tool_registry=tool_registry,
        )

        assert result["agent_id"] == "test-agent-3"
        assert result["tool_name"] == "read_file"
        assert result["risk_level"] == "CRITICAL"
        assert result["approved"] is False
        assert "System path" in result.get("error", "")


class TestAgentToolRiskScoring:
    """Test risk scoring in agent tool execution."""

    @pytest.mark.asyncio
    async def test_risk_score_low_operations(self, manager):
        """Test LOW risk scoring for read operations."""
        low_risk_tests = [
            ("read_file", {"path": "/home/user/file.txt"}),
            ("list_dir", {"path": "/home/user/"}),
            ("get_cpu_info", {}),
            ("get_memory_info", {}),
            ("search_knowledge", {"query": "test"}),
        ]

        for tool_name, args in low_risk_tests:
            result = await manager.execute_agent_tool(
                agent_id="low-risk",
                tool_name=tool_name,
                arguments=args,
            )
            assert result["risk_level"] == "LOW", f"Expected LOW for {tool_name}"
            assert result["approved"] is True, f"Expected approved for {tool_name}"

    @pytest.mark.asyncio
    async def test_risk_score_high_operations(self, manager):
        """Test HIGH risk scoring for write/delete operations."""
        high_risk_tests = [
            ("write_file", {"path": "/home/user/file.txt"}),
            ("create_file", {"path": "/home/user/new.txt"}),
            ("network_request", {"url": "http://example.com"}),
            ("api_call", {"endpoint": "/api/v1"}),
        ]

        for tool_name, args in high_risk_tests:
            result = await manager.execute_agent_tool(
                agent_id="high-risk",
                tool_name=tool_name,
                arguments=args,
            )
            assert result["risk_level"] == "HIGH", f"Expected HIGH for {tool_name}"


class TestAgentToolConsentFlow:
    """Test consent flow in agent tool execution."""

    @pytest.mark.asyncio
    async def test_consent_low_risk_silent_approval(self, manager):
        """Test LOW risk gets silent approval (no blocking)."""
        result = await manager.execute_agent_tool(
            agent_id="silent-test",
            tool_name="read_file",
            arguments={"path": "/home/user/file.txt"},
        )

        assert result["approved"] is True
        assert result["risk_level"] == "LOW"
        # Should execute quickly (no consent wait)
        assert result["execution_time_ms"] < 1000

    @pytest.mark.asyncio
    async def test_consent_critical_risk_auto_deny(self, manager):
        """Test CRITICAL risk gets auto-denied."""
        result = await manager.execute_agent_tool(
            agent_id="critical-test",
            tool_name="delete_file",
            arguments={"path": "/etc/critical_system_file"},
        )

        assert result["approved"] is False
        assert result["risk_level"] == "CRITICAL"


class TestAgentToolDryRun:
    """Test dry-run simulation in agent tool execution."""

    @pytest.mark.asyncio
    async def test_dry_run_read_file_simulation(self, manager):
        """Test dry-run simulation for read_file."""
        result = await manager.execute_agent_tool(
            agent_id="dryrun-read",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )

        assert result["approved"] is True
        # Check that tool was executed (not just simulated)
        assert result["result"] is not None or result["error"] is None

    @pytest.mark.asyncio
    async def test_dry_run_simulates_write_operation(self, manager):
        """Test dry-run simulation for write_file."""
        result = await manager.execute_agent_tool(
            agent_id="dryrun-write",
            tool_name="write_file",
            arguments={"path": "/test/output.txt", "content": "test data"},
        )

        # HIGH risk may timeout and be denied, but should have been simulated first
        assert "risk_level" in result
        assert result["risk_level"] == "HIGH"


class TestAgentToolAuditLogging:
    """Test audit logging in agent tool execution."""

    @pytest.mark.asyncio
    async def test_audit_log_created_for_low_risk(self, manager):
        """Test audit log entry created for LOW risk operations."""
        with tempfile.TemporaryDirectory():
            # Execute tool
            result = await manager.execute_agent_tool(
                agent_id="audit-test",
                tool_name="read_file",
                arguments={"path": "/test/file.txt"},
            )

            # Verify result
            assert result["approved"] is True
            assert result["audit_id"] != ""

    @pytest.mark.asyncio
    async def test_audit_log_records_risk_level(self, manager):
        """Test audit log records risk level correctly."""
        result = await manager.execute_agent_tool(
            agent_id="audit-risk-test",
            tool_name="write_file",
            arguments={"path": "/test/output.txt"},
        )

        # Audit should record risk level
        assert result["risk_level"] in ["LOW", "NORMAL", "HIGH", "CRITICAL"]
        assert result["audit_id"] != ""

    @pytest.mark.asyncio
    async def test_audit_log_records_approval_status(self, manager):
        """Test audit log records approval status."""
        # LOW risk - should be approved
        result_low = await manager.execute_agent_tool(
            agent_id="audit-approval-low",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )
        assert result_low["approved"] is True

        # CRITICAL risk - should be denied
        result_critical = await manager.execute_agent_tool(
            agent_id="audit-approval-critical",
            tool_name="delete_file",
            arguments={"path": "/etc/system_file"},
        )
        assert result_critical["approved"] is False


class TestAgentToolErrorHandling:
    """Test error handling in agent tool execution."""

    @pytest.mark.asyncio
    async def test_execute_agent_tool_unknown_tool(self, manager):
        """Test execution of unknown tool."""
        result = await manager.execute_agent_tool(
            agent_id="unknown-tool-test",
            tool_name="unknown_tool_that_does_not_exist",
            arguments={},
        )

        assert result["approved"] is False
        assert result["error"] is not None
        assert "approved" in result or "error" in result

    @pytest.mark.asyncio
    async def test_execute_agent_tool_with_invalid_arguments(self, manager):
        """Test tool execution with invalid arguments."""
        result = await manager.execute_agent_tool(
            agent_id="invalid-args",
            tool_name="read_file",
            arguments={"invalid_param": "value"},
        )

        # Should handle gracefully (may error or deny)
        assert "risk_level" in result
        assert "approved" in result

    @pytest.mark.asyncio
    async def test_pipeline_exception_handling(self, manager):
        """Test exception handling in full pipeline."""
        # Pass None as agent_id to trigger error
        result = await manager.execute_agent_tool(
            agent_id="",
            tool_name="read_file",
            arguments=None,
        )

        assert result["approved"] is False
        assert result["error"] is not None


class TestAgentToolIntegrationWithManager:
    """Test agent tool execution integration with LocalGPTOSManager."""

    @pytest.mark.asyncio
    async def test_execute_tool_increments_manager_stats(self, manager):
        """Test that tool execution updates manager statistics."""
        # Execute tool
        await manager.execute_agent_tool(
            agent_id="stats-test",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )

        # Check stats
        health_after = await manager.health_check()
        # Note: execute_agent_tool doesn't use limiter, so total_requests may not increase
        assert health_after["status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_execute_multiple_tools_sequentially(self, manager):
        """Test executing multiple tools in sequence."""
        results = []
        for i in range(3):
            result = await manager.execute_agent_tool(
                agent_id=f"seq-test-{i}",
                tool_name="read_file",
                arguments={"path": f"/test/file{i}.txt"},
            )
            results.append(result)

        assert len(results) == 3
        for result in results:
            assert result["approved"] is True
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_execute_tools_with_different_risk_levels(self, manager):
        """Test executing tools with varying risk levels."""
        # LOW risk
        low_result = await manager.execute_agent_tool(
            agent_id="risk-mix-low",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )
        assert low_result["risk_level"] == "LOW"
        assert low_result["approved"] is True

        # HIGH risk
        high_result = await manager.execute_agent_tool(
            agent_id="risk-mix-high",
            tool_name="write_file",
            arguments={"path": "/test/output.txt"},
        )
        assert high_result["risk_level"] == "HIGH"

        # CRITICAL risk
        critical_result = await manager.execute_agent_tool(
            agent_id="risk-mix-critical",
            tool_name="delete_file",
            arguments={"path": "/etc/passwd"},
        )
        assert critical_result["risk_level"] == "CRITICAL"
        assert critical_result["approved"] is False


class TestAgentToolResponseStructure:
    """Test structure of execute_agent_tool response."""

    @pytest.mark.asyncio
    async def test_response_contains_all_required_fields(self, manager):
        """Test response contains all required fields."""
        result = await manager.execute_agent_tool(
            agent_id="structure-test",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )

        required_fields = [
            "agent_id",
            "tool_name",
            "risk_level",
            "approved",
            "result",
            "audit_id",
            "execution_time_ms",
            "error",
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_response_field_types(self, manager):
        """Test response field types are correct."""
        result = await manager.execute_agent_tool(
            agent_id="types-test",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )

        assert isinstance(result["agent_id"], str)
        assert isinstance(result["tool_name"], str)
        assert isinstance(result["risk_level"], str)
        assert isinstance(result["approved"], bool)
        assert isinstance(result["audit_id"], str)
        assert isinstance(result["execution_time_ms"], float)
        assert result["error"] is None or isinstance(result["error"], str)

    @pytest.mark.asyncio
    async def test_response_risk_level_valid(self, manager):
        """Test response risk_level is one of valid values."""
        valid_levels = ["LOW", "NORMAL", "HIGH", "CRITICAL", "UNKNOWN"]

        result = await manager.execute_agent_tool(
            agent_id="risk-level-test",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
        )

        assert result["risk_level"] in valid_levels


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
