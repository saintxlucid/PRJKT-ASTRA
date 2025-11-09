"""
ASTRA OS ETW Telemetry — System-level event capture and audit pipeline.

ETW (Event Tracing for Windows) provides kernel-level visibility into:
- Filesystem operations (create, delete, modify, move)
- Network operations (connect, send, receive, DNS)
- Process lifecycle (spawn, kill, suspend, resume)

This module captures ETW events and routes them through the Gate for
token verification, scope validation, and audit logging.

Phase A Week 1: ETW capture + SQLite audit + Prometheus metrics
Phase A Week 2: WFP integration (network policy enforcement)
Phase A Week 3: Minifilter integration (filesystem policy enforcement)

Architecture:
    ETW Provider → Event Parser → Gate Verifier → Audit Log + Metrics
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from astra_os.gate import Action, Decision, Scope, Token, get_gate


@dataclass
class ETWEvent:
    """
    Parsed ETW event with normalized fields.

    Attributes:
        event_id: ETW event ID
        timestamp: Event timestamp (Unix epoch)
        provider: ETW provider name
        pid: Process ID that generated the event
        category: Event category (fs/net/proc)
        operation: Operation name (e.g., "create", "delete", "connect")
        details: Event-specific details (paths, addresses, etc.)
    """

    event_id: int
    timestamp: float
    provider: str
    pid: int
    category: str
    operation: str
    details: dict[str, Any]

    def to_gate_action(self) -> Action:
        """
        Convert ETW event to Gate Action for verification.

        Returns:
            Gate Action with appropriate scope and operation
        """
        # Map ETW category to Gate scope
        scope_map = {
            "fs": Scope.FS,
            "net": Scope.NET,
            "proc": Scope.PROC,
        }

        scope = scope_map.get(self.category, Scope.FS)

        # Construct operation name (e.g., "fs.delete")
        op = f"{self.category}.{self.operation}"

        return Action(
            scope=scope,
            op=op,
            args=self.details,
            pid=self.pid,
            timestamp=self.timestamp,
            context={"etw_event_id": self.event_id, "provider": self.provider},
        )


class ETWCollector:
    """
    ETW event collector and gate router.

    Captures system-level events from ETW providers and routes them
    through the Gate for verification and audit.
    """

    def __init__(self, metrics_db_path: Path):
        """
        Initialize ETW collector.

        Args:
            metrics_db_path: Path to Prometheus metrics database
        """
        self.metrics_db_path = metrics_db_path
        self.gate = get_gate()
        self._init_metrics_db()

        # Performance counters
        self.events_captured = 0
        self.events_allowed = 0
        self.events_denied = 0
        self.events_consent_required = 0

    def _init_metrics_db(self) -> None:
        """Initialize Prometheus-compatible metrics database."""
        conn = sqlite3.connect(self.metrics_db_path)
        cursor = conn.cursor()

        # Metrics table (time-series counter format)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS etw_metrics (
                timestamp REAL NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                labels_json TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_etw_metrics_timestamp
            ON etw_metrics(timestamp)
        """
        )

        conn.commit()
        conn.close()

    def capture_event(self, event: ETWEvent) -> Decision:
        """
        Capture ETW event and route through Gate.

        Args:
            event: Parsed ETW event

        Returns:
            Gate decision (ALLOW/DENY/CONSENT_REQUIRED)
        """
        self.events_captured += 1

        # Convert ETW event to Gate action
        action = event.to_gate_action()

        # TODO: Get operator's current token (from session context)
        # For Phase A Week 1, use stub token
        stub_token = Token(
            kid="dev_key_001",
            exp=int(time.time()) + 3600,  # 1 hour expiry
            iat=int(time.time()),
            sig="dev_signature_placeholder",
            scopes=[Scope.FS, Scope.NET, Scope.PROC],
            operator_id="operator_001",
        )

        # Verify through Gate
        decision = self.gate.verify_and_log(stub_token, action)

        # Update metrics
        if decision == Decision.ALLOW:
            self.events_allowed += 1
        elif decision == Decision.DENY:
            self.events_denied += 1
        elif decision == Decision.CONSENT_REQUIRED:
            self.events_consent_required += 1

        # Record metric
        self._record_metric(
            "etw_events_total",
            1.0,
            {"category": event.category, "operation": event.operation, "decision": decision.value},
        )

        return decision

    def _record_metric(self, name: str, value: float, labels: dict[str, str]) -> None:
        """
        Record Prometheus-style metric.

        Args:
            name: Metric name
            value: Metric value
            labels: Metric labels (for grouping/filtering)
        """
        conn = sqlite3.connect(self.metrics_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO etw_metrics (timestamp, metric_name, metric_value, labels_json)
            VALUES (?, ?, ?, ?)
        """,
            (time.time(), name, value, json.dumps(labels)),
        )

        conn.commit()
        conn.close()

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get current metrics summary (for Prometheus scraping).

        Returns:
            Dictionary with current counter values
        """
        return {
            "etw_events_captured_total": self.events_captured,
            "etw_events_allowed_total": self.events_allowed,
            "etw_events_denied_total": self.events_denied,
            "etw_events_consent_required_total": self.events_consent_required,
        }


# Global ETW collector instance
_etw_collector: ETWCollector | None = None


def get_etw_collector() -> ETWCollector:
    """Get global ETW collector instance (singleton)."""
    global _etw_collector
    if _etw_collector is None:
        metrics_db_path = Path(__file__).parent / "audit" / "etw_metrics.db"
        metrics_db_path.parent.mkdir(parents=True, exist_ok=True)
        _etw_collector = ETWCollector(metrics_db_path)
    return _etw_collector


def parse_fs_event(raw_event: dict[str, Any]) -> ETWEvent:
    """
    Parse filesystem ETW event.

    Args:
        raw_event: Raw ETW event dictionary

    Returns:
        Parsed ETW event
    """
    # Example ETW filesystem event structure:
    # {
    #   "EventID": 10,  # FileCreate
    #   "TimeStamp": 132842840320000000,  # FILETIME
    #   "ProcessId": 1234,
    #   "FileName": "C:\\Users\\Operator\\test.txt",
    #   "CreateOptions": 0x00000040  # FILE_NON_DIRECTORY_FILE
    # }

    event_id = raw_event.get("EventID", 0)
    timestamp = raw_event.get("TimeStamp", time.time())
    pid = raw_event.get("ProcessId", 0)
    file_name = raw_event.get("FileName", "")

    # Map event ID to operation
    operation_map = {
        10: "create",
        12: "delete",
        14: "rename",
        16: "modify",
    }
    operation = operation_map.get(event_id, "unknown")

    return ETWEvent(
        event_id=event_id,
        timestamp=timestamp,
        provider="Microsoft-Windows-Kernel-File",
        pid=pid,
        category="fs",
        operation=operation,
        details={"path": file_name},
    )


def parse_net_event(raw_event: dict[str, Any]) -> ETWEvent:
    """
    Parse network ETW event.

    Args:
        raw_event: Raw ETW event dictionary

    Returns:
        Parsed ETW event
    """
    # Example ETW network event structure:
    # {
    #   "EventID": 10,  # TCP connect
    #   "TimeStamp": 132842840320000000,
    #   "ProcessId": 1234,
    #   "SourceAddr": "192.168.1.100",
    #   "DestAddr": "93.184.216.34",
    #   "DestPort": 443
    # }

    event_id = raw_event.get("EventID", 0)
    timestamp = raw_event.get("TimeStamp", time.time())
    pid = raw_event.get("ProcessId", 0)
    dest_addr = raw_event.get("DestAddr", "")
    dest_port = raw_event.get("DestPort", 0)

    # Map event ID to operation
    operation_map = {
        10: "connect",
        11: "disconnect",
        12: "send",
        13: "receive",
    }
    operation = operation_map.get(event_id, "unknown")

    return ETWEvent(
        event_id=event_id,
        timestamp=timestamp,
        provider="Microsoft-Windows-Kernel-Network",
        pid=pid,
        category="net",
        operation=operation,
        details={"dest_addr": dest_addr, "dest_port": dest_port},
    )


def parse_proc_event(raw_event: dict[str, Any]) -> ETWEvent:
    """
    Parse process lifecycle ETW event.

    Args:
        raw_event: Raw ETW event dictionary

    Returns:
        Parsed ETW event
    """
    # Example ETW process event structure:
    # {
    #   "EventID": 1,  # ProcessStart
    #   "TimeStamp": 132842840320000000,
    #   "ProcessId": 1234,
    #   "ParentProcessId": 5678,
    #   "ImageFileName": "C:\\Windows\\System32\\cmd.exe",
    #   "CommandLine": "cmd.exe /c dir"
    # }

    event_id = raw_event.get("EventID", 0)
    timestamp = raw_event.get("TimeStamp", time.time())
    pid = raw_event.get("ProcessId", 0)
    parent_pid = raw_event.get("ParentProcessId", 0)
    image_name = raw_event.get("ImageFileName", "")
    command_line = raw_event.get("CommandLine", "")

    # Map event ID to operation
    operation_map = {
        1: "spawn",
        2: "terminate",
        3: "suspend",
        4: "resume",
    }
    operation = operation_map.get(event_id, "unknown")

    return ETWEvent(
        event_id=event_id,
        timestamp=timestamp,
        provider="Microsoft-Windows-Kernel-Process",
        pid=pid,
        category="proc",
        operation=operation,
        details={
            "parent_pid": parent_pid,
            "image_name": image_name,
            "command_line": command_line,
        },
    )


# Phase A Week 1 Demo: Simulate ETW event capture
def demo_etw_capture():
    """
    Demo: Simulate ETW event capture and gate routing.

    This will be replaced with real ETW provider hooks in Phase A Week 2.
    """
    collector = get_etw_collector()

    # Simulate filesystem events
    print("\n=== ASTRA OS Gate — ETW Telemetry Demo ===\n")

    print("📁 Simulating filesystem events...")
    fs_events = [
        {"EventID": 10, "ProcessId": 1234, "FileName": "C:\\Users\\Operator\\test.txt"},
        {"EventID": 12, "ProcessId": 1234, "FileName": "C:\\Windows\\System32\\important.dll"},
        {"EventID": 14, "ProcessId": 1234, "FileName": "C:\\Users\\Operator\\rename_me.txt"},
    ]

    for raw_event in fs_events:
        event = parse_fs_event(raw_event)
        decision = collector.capture_event(event)
        print(f"  {event.operation:8s} {event.details['path']:50s} → {decision.value}")

    # Simulate network events
    print("\n🌐 Simulating network events...")
    net_events = [
        {"EventID": 10, "ProcessId": 1234, "DestAddr": "93.184.216.34", "DestPort": 443},
        {"EventID": 10, "ProcessId": 1234, "DestAddr": "192.168.1.1", "DestPort": 8080},
    ]

    for raw_event in net_events:
        event = parse_net_event(raw_event)
        decision = collector.capture_event(event)
        print(f"  {event.operation:8s} {event.details['dest_addr']:20s}:{event.details['dest_port']} → {decision.value}")

    # Simulate process events
    print("\n⚙️  Simulating process events...")
    proc_events = [
        {"EventID": 1, "ProcessId": 5678, "ParentProcessId": 1234, "ImageFileName": "C:\\Windows\\System32\\cmd.exe", "CommandLine": "cmd.exe /c dir"},
        {"EventID": 2, "ProcessId": 5678, "ParentProcessId": 1234, "ImageFileName": "C:\\Windows\\System32\\cmd.exe", "CommandLine": ""},
    ]

    for raw_event in proc_events:
        event = parse_proc_event(raw_event)
        decision = collector.capture_event(event)
        print(f"  {event.operation:8s} PID {event.pid} ({event.details['image_name']}) → {decision.value}")

    # Print metrics summary
    print("\n📊 Metrics Summary:")
    metrics = collector.get_metrics_summary()
    for metric_name, metric_value in metrics.items():
        print(f"  {metric_name:40s} = {metric_value}")

    print("\n✅ ETW Telemetry Demo Complete\n")


if __name__ == "__main__":
    demo_etw_capture()
