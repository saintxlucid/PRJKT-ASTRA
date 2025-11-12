"""Rich TUI for operator console.

Provides real-time status display, command routing, and metrics for the operator.
"""
import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ComponentStatus(Enum):
    """Component health status."""

    HEALTHY = "✅ Healthy"
    WARNING = "⚠️  Warning"
    ERROR = "❌ Error"
    IDLE = "⏸️  Idle"


@dataclass
class SystemMetrics:
    """Current system metrics snapshot."""

    uptime_seconds: float = 0.0
    active_tasks: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    vector_store_size: int = 0
    inference_latency_ms: float = 0.0
    last_update: float = field(default_factory=time.time)

    def is_stale(self, threshold_sec: float = 5.0) -> bool:
        """Check if metrics are older than threshold."""
        return (time.time() - self.last_update) > threshold_sec


@dataclass
class ComponentState:
    """Component runtime state."""

    name: str
    status: ComponentStatus = ComponentStatus.IDLE
    uptime_sec: float = 0.0
    last_error: str | None = None
    message: str = ""


class OperatorConsole:
    """Rich TUI for ASTRA operator commands."""

    def __init__(self) -> None:
        """Initialize the console."""
        self.console = Console()
        self.running = True
        self.components: dict[str, ComponentState] = {
            "GPT-OOS Engine": ComponentState("GPT-OOS Engine"),
            "Vector Store": ComponentState("Vector Store"),
            "Agent Manager": ComponentState("Agent Manager"),
            "Observability": ComponentState("Observability"),
        }
        self.metrics = SystemMetrics()
        self.command_map: dict[str, Callable[[], None]] = {
            "status": self._cmd_status,
            "components": self._cmd_components,
            "metrics": self._cmd_metrics,
            "tasks": self._cmd_tasks,
            "help": self._cmd_help,
            "exit": self._cmd_exit,
        }

    def _update_metrics(self) -> None:
        """Refresh system metrics from manager."""
        # Simulated update; in production, fetch from LocalGPTOSManager
        self.metrics.uptime_seconds = time.time() % 10000
        self.metrics.active_tasks = 3
        self.metrics.memory_mb = 512.5
        self.metrics.cpu_percent = 45.2
        self.metrics.vector_store_size = 15000
        self.metrics.inference_latency_ms = 245.3
        self.metrics.last_update = time.time()

    def _build_status_panel(self) -> Panel:
        """Build the main status panel."""
        self._update_metrics()

        table = Table.grid(padding=1)
        table.add_row(
            "🚀 ASTRA Status",
            Text(f"Uptime: {self.metrics.uptime_seconds:.0f}s", style="bold green"),
        )
        table.add_row(
            "Tasks",
            Text(f"{self.metrics.active_tasks} active", style="cyan"),
        )
        table.add_row(
            "Memory",
            Text(f"{self.metrics.memory_mb:.1f} MB", style="yellow"),
        )
        table.add_row(
            "CPU",
            Text(f"{self.metrics.cpu_percent:.1f}%", style="magenta"),
        )
        table.add_row(
            "Inference P50",
            Text(f"{self.metrics.inference_latency_ms:.1f} ms", style="blue"),
        )

        return Panel(table, title="[bold]System Dashboard[/bold]", expand=False)

    def _build_components_table(self) -> Table:
        """Build component health table."""
        table = Table(title="Component Health", show_header=True)
        table.add_column("Component", style="cyan", width=20)
        table.add_column("Status", style="bold")
        table.add_column("Uptime", style="green")

        for comp in self.components.values():
            status_style = {
                ComponentStatus.HEALTHY: "green",
                ComponentStatus.WARNING: "yellow",
                ComponentStatus.ERROR: "red",
                ComponentStatus.IDLE: "dim",
            }.get(comp.status, "white")

            table.add_row(
                comp.name,
                Text(comp.status.value, style=status_style),
                f"{comp.uptime_sec:.0f}s",
            )

        return table

    def _cmd_status(self) -> None:
        """Show system status."""
        self.console.clear()
        self.console.print(self._build_status_panel())
        self.console.print()
        self.console.print(self._build_components_table())

    def _cmd_components(self) -> None:
        """Show detailed component info."""
        self.console.clear()
        self.console.print(self._build_components_table())

    def _cmd_metrics(self) -> None:
        """Show detailed metrics."""
        self.console.clear()
        self._update_metrics()

        table = Table(title="System Metrics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Uptime (s)", f"{self.metrics.uptime_seconds:.1f}")
        table.add_row("Active Tasks", str(self.metrics.active_tasks))
        table.add_row("Memory (MB)", f"{self.metrics.memory_mb:.1f}")
        table.add_row("CPU (%)", f"{self.metrics.cpu_percent:.1f}")
        table.add_row("Vector Store Size", str(self.metrics.vector_store_size))
        table.add_row(
            "Inference Latency P50 (ms)", f"{self.metrics.inference_latency_ms:.1f}"
        )

        self.console.print(table)

    def _cmd_tasks(self) -> None:
        """Show active tasks."""
        self.console.clear()
        self.console.print(
            Panel(
                Text(
                    "Task Queue: 3 tasks pending\n"
                    "1. [yellow]Vector store rebuild (72%)[/yellow]\n"
                    "2. [cyan]Agent memory consolidation[/cyan]\n"
                    "3. [blue]Observability checkpoint[/blue]",
                    justify="left",
                ),
                title="[bold]Active Tasks[/bold]",
            )
        )

    def _cmd_help(self) -> None:
        """Show help."""
        self.console.clear()
        help_text = (
            "[bold cyan]ASTRA Operator Console[/bold cyan]\n\n"
            "[bold]Commands:[/bold]\n"
            "  [green]status[/green]     — Show system status and metrics\n"
            "  [green]components[/green] — Show component health details\n"
            "  [green]metrics[/green]    — Show detailed metrics\n"
            "  [green]tasks[/green]      — Show active background tasks\n"
            "  [green]help[/green]       — Show this help message\n"
            "  [green]exit[/green]       — Exit the console\n"
        )
        self.console.print(Panel(help_text, title="[bold]Help[/bold]"))

    def _cmd_exit(self) -> None:
        """Exit the console."""
        self.console.print("[yellow]Shutting down...[/yellow]")
        self.running = False

    def process_command(self, cmd: str) -> None:
        """Process and execute a command."""
        cmd_lower = cmd.strip().lower()

        if not cmd_lower:
            return

        handler = self.command_map.get(cmd_lower)
        if handler:
            handler()
        else:
            self.console.print(
                f"[red]Unknown command: {cmd_lower}[/red] "
                f"(Type 'help' for available commands)"
            )

    def run(self) -> None:
        """Start the REPL loop."""
        self.console.print(
            Panel(
                "[bold green]ASTRA Operator Console v3.0[/bold green]\n"
                "Type 'help' for available commands.",
                title="[bold]Welcome[/bold]",
            )
        )

        while self.running:
            try:
                cmd = input("\n[cyan]astra>[/cyan] ")
                self.process_command(cmd)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted.[/yellow]")
                self.running = False
            except EOFError:
                self.console.print("\n[yellow]EOF detected.[/yellow]")
                self.running = False

        self.console.print("[bold green]Console closed.[/bold green]")


async def main() -> None:
    """Main entry point."""
    console = OperatorConsole()
    console.run()


if __name__ == "__main__":
    asyncio.run(main())
