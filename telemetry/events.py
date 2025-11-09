# telemetry/events.py
"""
Event stream logger for ASTRA OS.
JSONL append-only logging with rotation for deterministic replay.
"""
import json
import time
from pathlib import Path
from typing import Any, TextIO


class EventLogger:
    """
    JSONL event logger with automatic rotation.
    Appends events to log file, rotates at max_size_mb.
    """

    def __init__(
        self,
        log_dir: str = "data/logs",
        log_name: str = "events",
        max_size_mb: int = 200,
    ):
        """
        Initialize event logger.

        Args:
            log_dir: Directory for log files
            log_name: Base name for log files
            max_size_mb: Max size before rotation (default 200MB)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_name = log_name
        self.max_size_bytes = max_size_mb * 1024 * 1024

        self.current_file: Path | None = None
        self.file_handle: TextIO | None = None

        self._open_current_log()

    def _open_current_log(self) -> None:
        """Open current log file for appending."""
        # Find existing log or create new one
        existing_logs = sorted(
            self.log_dir.glob(f"{self.log_name}_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if existing_logs:
            latest = existing_logs[0]
            # Check if we need to rotate
            if latest.stat().st_size < self.max_size_bytes:
                self.current_file = latest
            else:
                self._create_new_log()
        else:
            self._create_new_log()

        # Open for appending
        self.file_handle = open(str(self.current_file), "a", encoding="utf-8")

    def _create_new_log(self) -> None:
        """Create new log file with timestamp."""
        timestamp = int(time.time() * 1000)
        self.current_file = self.log_dir / f"{self.log_name}_{timestamp}.jsonl"

    def _check_rotation(self) -> None:
        """Check if rotation is needed and rotate if necessary."""
        if self.current_file and self.current_file.stat().st_size >= self.max_size_bytes:
            # Close current file
            if self.file_handle:
                self.file_handle.close()

            # Create new file
            self._create_new_log()
            self.file_handle = open(str(self.current_file), "a", encoding="utf-8")

    def log(self, event: dict[str, Any]) -> None:
        """
        Log an event as JSON line.

        Args:
            event: Event dictionary (must be JSON-serializable)
        """
        # Add timestamp if not present
        if "ts" not in event:
            event["ts"] = time.time()

        # Write JSON line
        if self.file_handle is None:
            raise RuntimeError("Log file not open")

        json_line = json.dumps(event, default=str) + "\n"
        self.file_handle.write(json_line)
        self.file_handle.flush()

        # Check if rotation needed
        self._check_rotation()

    def log_agent_start(self, task: str) -> None:
        """Log agent.start event."""
        self.log({"event": "agent.start", "task": task})

    def log_agent_plan(self, iteration: int) -> None:
        """Log agent.plan event."""
        self.log({"event": "agent.plan", "iteration": iteration})

    def log_agent_answer(self, answer: str) -> None:
        """Log agent.answer event."""
        self.log({"event": "agent.answer", "answer": answer})

    def log_tool_call(self, tool: str, args: dict[str, Any]) -> None:
        """Log tool.call event."""
        self.log({"event": "tool.call", "tool": tool, "args": args})

    def log_tool_result(
        self,
        tool: str,
        ok: bool,
        result: Any = None,
        error: str | None = None,
        latency_ms: int = 0,
    ) -> None:
        """Log tool.result event."""
        event = {
            "event": "tool.result",
            "tool": tool,
            "ok": ok,
            "latency_ms": latency_ms,
        }

        if result is not None:
            event["result"] = result
        if error is not None:
            event["error"] = error

        self.log(event)

    def log_memory_write(self, tier: str, key: str, ttl_s: int | None = None) -> None:
        """Log memory.write event."""
        event: dict[str, Any] = {"event": "memory.write", "tier": tier, "key": key}
        if ttl_s is not None:
            event["ttl_s"] = ttl_s
        self.log(event)

    def log_state_transition(self, from_state: str, to_state: str) -> None:
        """Log state.transition event."""
        self.log({
            "event": "state.transition",
            "from": from_state,
            "to": to_state,
        })

    def close(self) -> None:
        """Close log file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def __enter__(self) -> "EventLogger":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def read_events(
    log_file: str,
    event_type: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Read events from JSONL log file.

    Args:
        log_file: Path to .jsonl file
        event_type: Optional filter by event type
        limit: Optional max number of events to return

    Returns:
        List of event dictionaries
    """
    events = []

    try:
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())

                    # Filter by event type if specified
                    if event_type and event.get("event") != event_type:
                        continue

                    events.append(event)

                    # Check limit
                    if limit and len(events) >= limit:
                        break

                except json.JSONDecodeError:
                    continue  # Skip malformed lines

    except FileNotFoundError:
        pass

    return events


def replay_events(log_file: str) -> None:
    """
    Replay events from log file (print to stdout).

    Args:
        log_file: Path to .jsonl file
    """
    events = read_events(log_file)

    print(f"Replaying {len(events)} events from {log_file}\n")
    print("=" * 60)

    for i, event in enumerate(events, 1):
        event_type = event.get("event", "unknown")
        ts = event.get("ts", 0)

        print(f"\n[{i}] {event_type} @ {ts:.3f}s")
        print(json.dumps(event, indent=2, default=str))

    print("\n" + "=" * 60)
    print(f"Replay complete: {len(events)} events")
