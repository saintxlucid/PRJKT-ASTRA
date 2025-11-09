# tests/test_p0_integration.py
"""
P0 Component Integration Tests for ASTRA OS.
Tests all P0 components working together: tokenizer, browser, agent, memory, telemetry, OS verbs.
"""
import time

import pytest

from agent_kernel.memory import MemoryManager
from agent_kernel.planner import AgentKernel
from agent_kernel.tools import create_default_registry
from comet_browser.dom.sanitizer import Sanitizer
from controller.os_verbs import PYWIN32_AVAILABLE
from core.tokenizer import issue as issue_token, verify as verify_token
from telemetry.events import EventLogger
from telemetry.metrics import get_metrics


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def memory_manager(temp_data_dir):
    """Create memory manager with temp database."""
    db_path = temp_data_dir / "test_memory.db"
    return MemoryManager(db_path=str(db_path))


@pytest.fixture
def event_logger(temp_data_dir):
    """Create event logger with temp log dir."""
    log_dir = temp_data_dir / "logs"
    log_dir.mkdir()
    return EventLogger(log_dir=str(log_dir))


@pytest.fixture
def metrics_exporter():
    """Create metrics exporter without server."""
    return get_metrics(enable_server=False)


@pytest.fixture
def tool_registry():
    """Create tool registry with default tools."""
    return create_default_registry()


@pytest.fixture
def mock_llm():
    """Create mock LLM that returns predefined responses."""

    def llm_func(prompt: str) -> str:
        """Mock LLM that parses prompt and returns appropriate action."""
        prompt_lower = prompt.lower()

        # Check for navigation requests
        if "navigate" in prompt_lower or "browse" in prompt_lower:
            if "example.com" in prompt_lower:
                return "ACTION: browser.navigate\nTOOL: browser.navigate\nARGS: {\"url\": \"http://example.com\"}\nREASON: Navigate to example.com"

        # Check for extraction requests
        if "extract" in prompt_lower or "get text" in prompt_lower:
            return "ACTION: browser.extract\nTOOL: browser.extract\nARGS: {\"selector\": \"body\"}\nREASON: Extract page content"

        # Default: answer without tool
        return "ANSWER: Task understood."

    return llm_func


class TestTokenizerIntegration:
    """Test tokenizer integration with other components."""

    def test_tokenizer_with_tool_registry(self, tool_registry):
        """Test tokenizer works with tool registry."""
        # Issue token for browser tool
        token = issue_token("browser.navigate", "action")
        assert len(token) > 0

        # Get tool from registry
        tool = tool_registry.get("browser.navigate")
        assert tool is not None
        assert tool.name == "browser.navigate"

        # Verify tool requires token
        assert tool.requires_token is True

    def test_tokenizer_scopes(self):
        """Test tokenizer supports all required scopes."""
        # Test different scopes
        info_token = issue_token("test.info", "info")
        action_token = issue_token("test.action", "action")
        admin_token = issue_token("test.admin", "admin")

        # All should generate valid tokens
        assert len(info_token) > 0
        assert len(action_token) > 0
        assert len(admin_token) > 0


class TestMemoryIntegration:
    """Test memory system integration."""

    def test_memory_with_telemetry(self, memory_manager, event_logger):
        """Test memory operations with telemetry logging."""
        # Write to memory
        memory_manager.write("test_key", "test_value", tier="L1")
        event_logger.log_memory_write("L1", "test_key")

        # Read from memory
        value = memory_manager.read("test_key", tier="L1")
        assert value == "test_value"

        # Verify event was logged
        events = event_logger.read_events(event_logger.current_file)
        assert len(events) > 0
        assert events[0]["event_type"] == "memory.write"

    def test_memory_cascade_reads(self, memory_manager):
        """Test memory cascade reads across tiers."""
        # Populate different tiers
        memory_manager.write("shared_key", "from_L0", tier="L0")
        memory_manager.write("shared_key", "from_L2", tier="L2")
        memory_manager.write("shared_key", "from_L3", tier="L3")

        # Cascade should return L3 (highest priority)
        value = memory_manager.read_cascade("shared_key")
        assert value == "from_L3"

        # Clear L3, should fall back to L2
        memory_manager.clear_tier("L3")
        value = memory_manager.read_cascade("shared_key")
        assert value == "from_L2"

    def test_memory_persistence(self, temp_data_dir):
        """Test L0 memory persists across sessions."""
        db_path = temp_data_dir / "persistent.db"

        # First session
        memory1 = MemoryManager(db_path=str(db_path))
        memory1.write("persistent_key", "persistent_value", tier="L0")

        # Second session
        memory2 = MemoryManager(db_path=str(db_path))
        value = memory2.read("persistent_key", tier="L0")
        assert value == "persistent_value"


class TestAgentIntegration:
    """Test agent kernel with all components."""

    def test_agent_with_memory_and_telemetry(
        self, mock_llm, tool_registry, memory_manager, event_logger, metrics_exporter
    ):
        """Test agent using memory and telemetry."""
        # Create agent with all components
        agent = AgentKernel(
            llm=mock_llm,
            tools=tool_registry,
            memory_manager=memory_manager,
            telemetry_logger=event_logger,
            telemetry_metrics=metrics_exporter,
            max_iterations=3,
        )

        # Run task
        result = agent.run("Test task")

        # Verify completion
        assert result["status"] in ["answer", "max_iterations"]
        assert result["iterations"] > 0

        # Check memory was used (session.task stored)
        stats = memory_manager.get_stats()
        assert stats["L1"] > 0

        # Check telemetry logged events
        events = event_logger.read_events(event_logger.current_file)
        assert len(events) > 0
        assert any(e["event_type"] == "agent.start" for e in events)

    def test_agent_memory_cleanup(self, mock_llm, tool_registry, memory_manager):
        """Test agent clears L2 memory after task."""
        # Pre-populate L2
        memory_manager.write("temp_key", "temp_value", tier="L2")
        initial_l2_count = memory_manager.get_stats()["L2"]
        assert initial_l2_count > 0

        # Create and run agent
        agent = AgentKernel(
            llm=mock_llm, tools=tool_registry, memory_manager=memory_manager, max_iterations=2
        )
        agent.run("Simple task")

        # Verify L2 was cleared
        stats = memory_manager.get_stats()
        assert stats.get("L2", 0) == 0


class TestSanitizerIntegration:
    """Test sanitizer integration."""

    def test_sanitizer_html_cleaning(self):
        """Test sanitizer cleans HTML correctly."""
        sanitizer = Sanitizer()

        # Test XSS removal
        dirty_html = '<script>alert("xss")</script><p>Safe content</p>'
        clean_html = sanitizer.sanitize_html(dirty_html)

        assert "<script>" not in clean_html
        assert "Safe content" in clean_html

    def test_sanitizer_url_validation(self):
        """Test sanitizer validates URLs."""
        sanitizer = Sanitizer()

        # Safe URLs
        assert sanitizer.is_safe_url("https://example.com") is True
        assert sanitizer.is_safe_url("http://localhost:8000") is True

        # Unsafe URLs
        assert sanitizer.is_safe_url("javascript:alert(1)") is False
        assert sanitizer.is_safe_url("data:text/html,<script>") is False


class TestOSVerbsIntegration:
    """Test OS verbs integration (Windows only)."""

    @pytest.mark.skipif(not PYWIN32_AVAILABLE, reason="pywin32 not available")
    def test_os_verbs_registered(self):
        """Test OS verbs are registered in tool registry."""
        from controller.os_tool_registry import create_os_tool_registry

        registry = create_os_tool_registry()

        # Verify OS verbs exist
        os_tools = [name for name in registry.tools.keys() if name.startswith("os.")]
        assert len(os_tools) == 10

        # Verify specific verbs
        assert "os.window.list" in registry.tools
        assert "os.app.launch" in registry.tools
        assert "os.screen.size" in registry.tools

    @pytest.mark.skipif(not PYWIN32_AVAILABLE, reason="pywin32 not available")
    def test_os_verb_execution(self):
        """Test OS verb can be executed."""
        from controller.os_verbs import screen_get_size

        result = screen_get_size()
        assert result["ok"] is True
        assert result["width"] > 0
        assert result["height"] > 0

    @pytest.mark.skipif(not PYWIN32_AVAILABLE, reason="pywin32 not available")
    def test_os_verbs_with_memory(self, memory_manager):
        """Test OS verb results stored in memory."""
        from controller.os_verbs import screen_get_size

        # Get screen info
        screen_info = screen_get_size()

        # Store in memory
        memory_manager.write("screen_info", screen_info, tier="L1")

        # Retrieve
        stored = memory_manager.read("screen_info", tier="L1")
        assert stored["ok"] is True
        assert stored["width"] == screen_info["width"]


class TestTelemetryIntegration:
    """Test telemetry system integration."""

    def test_event_logging_end_to_end(self, event_logger):
        """Test complete event logging workflow."""
        # Log different event types
        event_logger.log_agent_start("Test task")
        event_logger.log_tool_call("test.tool", {"arg": "value"})
        event_logger.log_memory_write("L2", "test_key")

        # Read events back
        events = event_logger.read_events(event_logger.current_file)

        # Verify all logged
        assert len(events) >= 3
        event_types = {e["event_type"] for e in events}
        assert "agent.start" in event_types
        assert "tool.call" in event_types
        assert "memory.write" in event_types

    def test_metrics_recording(self, metrics_exporter):
        """Test metrics are recorded correctly."""
        # Record some metrics
        metrics_exporter.record_tool_call("test.tool", 100.0, True)
        metrics_exporter.record_memory_write("L2")
        metrics_exporter.record_agent_state("planning")

        # Metrics should be recorded (no errors)
        # Note: Can't easily verify Prometheus values without server


class TestFullSystemWorkflow:
    """Test complete P0 system workflows."""

    def test_complete_agent_workflow(
        self, mock_llm, memory_manager, event_logger, metrics_exporter
    ):
        """Test complete workflow with all P0 components."""
        from controller.os_tool_registry import create_os_tool_registry

        # Create full system
        registry = create_os_tool_registry()
        agent = AgentKernel(
            llm=mock_llm,
            tools=registry,
            memory_manager=memory_manager,
            telemetry_logger=event_logger,
            telemetry_metrics=metrics_exporter,
            max_iterations=5,
        )

        # Store initial context
        memory_manager.write("context", {"task": "test", "priority": "high"}, tier="L1")

        # Run agent
        result = agent.run("Perform system check")

        # Verify all systems engaged
        assert result["status"] in ["answer", "max_iterations"]
        assert result["iterations"] > 0

        # Check memory
        stats = memory_manager.get_stats()
        assert stats["L1"] >= 1

        # Check telemetry
        events = event_logger.read_events(event_logger.current_file)
        assert len(events) > 0
        assert "agent.start" in {e["event_type"] for e in events}

    def test_error_handling_integration(self, mock_llm, tool_registry, memory_manager):
        """Test system handles errors gracefully."""
        agent = AgentKernel(
            llm=mock_llm, tools=tool_registry, memory_manager=memory_manager, max_iterations=2
        )

        # Invalid tool execution should not crash
        tool = tool_registry.get("browser.navigate")
        if tool:
            token = issue_token("browser.navigate", "action")
            result = tool({"invalid": "args"}, token)
            assert "ok" in result

        # Agent should still work
        result = agent.run("Simple task")
        assert result["status"] in ["answer", "max_iterations"]


class TestPerformance:
    """Test P0 system performance."""

    def test_memory_read_speed(self, memory_manager):
        """Test memory read performance."""
        # Write test data
        for i in range(100):
            memory_manager.write(f"key_{i}", f"value_{i}", tier="L2")

        # Measure read time
        start = time.perf_counter()
        for i in range(100):
            memory_manager.read(f"key_{i}", tier="L2")
        elapsed = time.perf_counter() - start

        # Should be fast (< 100ms for 100 reads)
        assert elapsed < 0.1, f"Memory reads too slow: {elapsed:.3f}s"

    def test_event_logging_speed(self, event_logger):
        """Test event logging performance."""
        start = time.perf_counter()
        for i in range(100):
            event_logger.log({"event_type": "test", "iteration": i})
        elapsed = time.perf_counter() - start

        # Should be fast (< 100ms for 100 logs)
        assert elapsed < 0.1, f"Event logging too slow: {elapsed:.3f}s"

    def test_agent_iteration_speed(self, mock_llm, tool_registry, memory_manager):
        """Test agent iteration performance."""
        agent = AgentKernel(
            llm=mock_llm, tools=tool_registry, memory_manager=memory_manager, max_iterations=5
        )

        start = time.perf_counter()
        result = agent.run("Quick task")
        elapsed = time.perf_counter() - start

        # Should complete reasonably fast (< 1s for mock LLM)
        assert elapsed < 1.0, f"Agent too slow: {elapsed:.3f}s"


# Run with: pytest tests/test_p0_integration.py -v
# Run with OS tests: pytest tests/test_p0_integration.py -v -m "not skipif"
