"""Unit and integration tests for Operator Console CLI.

Validates command dispatch, status rendering, metrics display, and error handling.
"""
import time
from unittest.mock import patch

import pytest

from astra.phase3.ui.console_cli import (
    ComponentState,
    ComponentStatus,
    OperatorConsole,
    SystemMetrics,
)


class TestSystemMetrics:
    """Test SystemMetrics data class."""

    def test_creation(self) -> None:
        """Test metrics object creation."""
        metrics = SystemMetrics(uptime_seconds=100.0, memory_mb=256.0)
        assert metrics.uptime_seconds == 100.0
        assert metrics.memory_mb == 256.0

    def test_is_stale_false(self) -> None:
        """Test is_stale returns false for fresh metrics."""
        metrics = SystemMetrics(uptime_seconds=100.0)
        assert not metrics.is_stale(threshold_sec=5.0)

    def test_is_stale_true(self) -> None:
        """Test is_stale returns true for old metrics."""
        metrics = SystemMetrics(uptime_seconds=100.0)
        metrics.last_update = time.time() - 10.0
        assert metrics.is_stale(threshold_sec=5.0)


class TestComponentState:
    """Test ComponentState data class."""

    def test_creation(self) -> None:
        """Test component state creation."""
        comp = ComponentState(name="Test Component", status=ComponentStatus.HEALTHY)
        assert comp.name == "Test Component"
        assert comp.status == ComponentStatus.HEALTHY


class TestOperatorConsole:
    """Test OperatorConsole class."""

    @pytest.fixture
    def console(self) -> OperatorConsole:
        """Fixture for OperatorConsole instance."""
        return OperatorConsole()

    def test_initialization(self, console: OperatorConsole) -> None:
        """Test console initializes correctly."""
        assert console.running
        assert len(console.components) == 4
        assert "GPT-OOS Engine" in console.components
        assert len(console.command_map) == 6

    def test_update_metrics(self, console: OperatorConsole) -> None:
        """Test metrics update."""
        console._update_metrics()
        assert console.metrics.uptime_seconds > 0
        assert console.metrics.active_tasks >= 0
        assert console.metrics.memory_mb > 0

    def test_build_status_panel(self, console: OperatorConsole) -> None:
        """Test status panel building."""
        panel = console._build_status_panel()
        assert panel is not None

    def test_build_components_table(self, console: OperatorConsole) -> None:
        """Test components table building."""
        table = console._build_components_table()
        assert table is not None
        assert table.title == "Component Health"

    def test_cmd_status(self, console: OperatorConsole) -> None:
        """Test status command execution."""
        with patch.object(console.console, "print") as mock_print:
            console._cmd_status()
            assert mock_print.called

    def test_cmd_components(self, console: OperatorConsole) -> None:
        """Test components command execution."""
        with patch.object(console.console, "print") as mock_print:
            console._cmd_components()
            assert mock_print.called

    def test_cmd_metrics(self, console: OperatorConsole) -> None:
        """Test metrics command execution."""
        with patch.object(console.console, "print") as mock_print:
            console._cmd_metrics()
            assert mock_print.called

    def test_cmd_tasks(self, console: OperatorConsole) -> None:
        """Test tasks command execution."""
        with patch.object(console.console, "print") as mock_print:
            console._cmd_tasks()
            assert mock_print.called

    def test_cmd_help(self, console: OperatorConsole) -> None:
        """Test help command execution."""
        with patch.object(console.console, "print") as mock_print:
            console._cmd_help()
            assert mock_print.called

    def test_cmd_exit(self, console: OperatorConsole) -> None:
        """Test exit command execution."""
        assert console.running
        with patch.object(console.console, "print") as mock_print:
            console._cmd_exit()
            assert not console.running
            assert mock_print.called

    def test_process_command_valid(self, console: OperatorConsole) -> None:
        """Test processing a valid command."""
        with patch.object(console, "_cmd_help") as mock_help:
            console.process_command("help")
            mock_help.assert_called_once()

    def test_process_command_invalid(self, console: OperatorConsole) -> None:
        """Test processing an invalid command."""
        with patch.object(console.console, "print") as mock_print:
            console.process_command("invalid_cmd")
            assert mock_print.called
            call_args = mock_print.call_args[0][0]
            assert "Unknown command" in str(call_args)

    def test_process_command_case_insensitive(self, console: OperatorConsole) -> None:
        """Test command processing is case-insensitive."""
        with patch.object(console, "_cmd_status") as mock_status:
            console.process_command("STATUS")
            mock_status.assert_called_once()

    def test_process_command_empty(self, console: OperatorConsole) -> None:
        """Test processing an empty command."""
        with patch.object(console.console, "print") as mock_print:
            console.process_command("")
            # Should not print anything for empty command
            assert not mock_print.called

    def test_process_command_whitespace(self, console: OperatorConsole) -> None:
        """Test processing whitespace-only command."""
        with patch.object(console.console, "print") as mock_print:
            console.process_command("   ")
            # Should not print anything for whitespace-only command
            assert not mock_print.called

    def test_metrics_latency_range(self, console: OperatorConsole) -> None:
        """Test metrics latency is within realistic range."""
        console._update_metrics()
        assert 0 < console.metrics.inference_latency_ms < 5000

    def test_metrics_cpu_range(self, console: OperatorConsole) -> None:
        """Test metrics CPU percentage is valid."""
        console._update_metrics()
        assert 0 <= console.metrics.cpu_percent <= 100

    def test_all_commands_in_map(self, console: OperatorConsole) -> None:
        """Test all expected commands are in the command map."""
        expected_commands = {"status", "components", "metrics", "tasks", "help", "exit"}
        assert set(console.command_map.keys()) == expected_commands

    def test_component_states_initialized(self, console: OperatorConsole) -> None:
        """Test all component states are properly initialized."""
        for comp in console.components.values():
            assert comp.name is not None
            assert comp.status in ComponentStatus


class TestConsoleIntegration:
    """Integration tests for Console CLI."""

    def test_console_command_sequence(self) -> None:
        """Test running a sequence of commands."""
        console = OperatorConsole()

        # Mock the input to prevent blocking
        with patch("builtins.input", side_effect=["status", "help", "exit"]):
            with patch.object(console.console, "print"):
                # Simulate partial execution without full loop
                console.process_command("status")
                console.process_command("help")
                console.process_command("exit")

                assert not console.running

    def test_metrics_consistency(self) -> None:
        """Test that metrics remain consistent across updates."""
        console = OperatorConsole()

        console._update_metrics()
        uptime1 = console.metrics.uptime_seconds

        time.sleep(0.1)
        console._update_metrics()
        uptime2 = console.metrics.uptime_seconds

        # Uptime should increase
        assert uptime2 >= uptime1

    def test_component_status_display(self) -> None:
        """Test component status is properly rendered."""
        console = OperatorConsole()
        table = console._build_components_table()

        # Verify table has expected columns
        assert table is not None
        assert any("Component" in str(col) for col in table.columns)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
