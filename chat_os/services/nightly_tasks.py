"""
Nightly Tasks Service — Background automation for macro learning and refinement.

This module provides scheduled tasks that run during off-peak hours (3:00 AM)
to analyze execution history, learn new macros, and propose system optimizations.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from chat_os.cognitive.macro_mining import ExecutionTrace, MacroMiner, generate_macro_dsl
from chat_os.cognitive.refinement import RefinementEngine, TelemetrySnapshot as RefinementTelemetrySnapshot
from chat_os.telemetry import TelemetrySnapshot


def run_nightly_macro_learning(
    trace_history_path: Path,
    proposals_dir: Path,
    min_confidence: float = 0.85,
    min_occurrences: int = 3,
) -> dict[str, Any]:
    """
    Analyze execution traces and generate macro proposals.

    Args:
        trace_history_path: Path to JSON file with historical traces
        proposals_dir: Directory to save macro proposals
        min_confidence: Minimum confidence threshold for macros
        min_occurrences: Minimum occurrences needed to learn pattern

    Returns:
        Report dict with counts and generated proposals
    """
    # Load historical traces
    if not trace_history_path.exists():
        return {
            "status": "no_history",
            "message": "No trace history found",
            "timestamp": datetime.now().isoformat(),
        }

    with open(trace_history_path) as f:
        trace_data = json.load(f)

    traces = [ExecutionTrace(**t) for t in trace_data.get("traces", [])]

    if len(traces) == 0:
        return {
            "status": "no_traces",
            "message": "No traces to analyze",
            "timestamp": datetime.now().isoformat(),
        }

    # Initialize miner and process traces
    miner = MacroMiner(min_confidence=min_confidence, min_occurrences=min_occurrences)

    for trace in traces:
        miner.ingest_trace(trace)

    learned_macros = miner.mine_macros()

    # Generate proposals
    proposals_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    proposals: list[dict[str, Any]] = []
    for macro in learned_macros:
        proposal = {
            "macro_name": macro.name,
            "pattern": macro.pattern,
            "confidence": macro.confidence,
            "success_count": macro.success_count,
            "failure_count": macro.failure_count,
            "budget_ms": macro.budget_ms,
            "dsl": generate_macro_dsl(macro),
            "status": "pending_approval",
            "generated_at": timestamp,
        }
        proposals.append(proposal)

        # Save individual proposal file
        proposal_file = proposals_dir / f"{macro.name}_{timestamp}.json"
        with open(proposal_file, "w") as f:
            json.dump(proposal, f, indent=2)

    # Save summary report
    report = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "traces_analyzed": len(traces),
        "macros_learned": len(learned_macros),
        "proposals_generated": len(proposals),
        "proposals": proposals,
    }

    report_file = proposals_dir / f"nightly_report_{timestamp}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    return report


def schedule_nightly_tasks(
    trace_history_path: str | Path = "./astra_data/traces/history.json",
    proposals_dir: str | Path = "./astra_data/macros/proposals",
    telemetry_dir: str | Path = "./astra_data/telemetry",
    refinement_dir: str | Path = "./astra_data/refinement",
) -> None:
    """
    Schedule nightly tasks for 3:00 AM and 3:15 AM execution.

    This is a placeholder for actual scheduling logic. In production, use:
    - Windows Task Scheduler (Windows)
    - cron (Linux/macOS)
    - APScheduler (Python-based)
    - systemd timers (Linux)

    Args:
        trace_history_path: Path to historical traces
        proposals_dir: Directory for macro proposals
        telemetry_dir: Directory for telemetry snapshots
        refinement_dir: Directory for refinement reports
    """
    trace_path = Path(trace_history_path)
    proposals_path = Path(proposals_dir)
    telemetry_path = Path(telemetry_dir)
    refinement_path = Path(refinement_dir)

    print("📅 Nightly Task Scheduler")
    print("=" * 60)
    print(f"Trace history:    {trace_path.absolute()}")
    print(f"Macro proposals:  {proposals_path.absolute()}")
    print(f"Telemetry:        {telemetry_path.absolute()}")
    print(f"Refinement:       {refinement_path.absolute()}")
    print()
    print("⏰ Scheduled tasks:")
    print("  - 03:00 AM: Macro learning (run_nightly_macro_learning)")
    print("  - 03:15 AM: Nightly refinement (run_nightly_refinement)")
    print("  - 03:30 AM: Memory compression (TBD Phase 3)")
    print()
    print("💡 To enable scheduling:")
    print("  Windows: Use Task Scheduler GUI or schtasks.exe")
    print("  Linux/macOS: Add to crontab:")
    print("    0 3 * * * cd /path/to/astra && python -m chat_os.services.nightly_tasks macro")
    print("    15 3 * * * cd /path/to/astra && python -m chat_os.services.nightly_tasks refinement")
    print()
    print("🔧 For development testing, run manually:")
    print("  Macro learning:")
    print(f'    python -c "from chat_os.services.nightly_tasks import run_nightly_macro_learning; '
          f'from pathlib import Path; print(run_nightly_macro_learning(Path(\'{trace_path}\'), Path(\'{proposals_path}\')))"')
    print()
    print("  Refinement:")
    print(f'    python -c "from chat_os.services.nightly_tasks import run_nightly_refinement; '
          f'from pathlib import Path; print(run_nightly_refinement(Path(\'{telemetry_path}\'), Path(\'{refinement_path}\')))"')


def save_execution_trace(trace: ExecutionTrace, history_path: Path) -> None:
    """
    Append an execution trace to historical log.

    Args:
        trace: ExecutionTrace to save
        history_path: Path to JSON history file
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing history
    if history_path.exists():
        with open(history_path) as f:
            data = json.load(f)
    else:
        data = {"traces": [], "created_at": datetime.now().isoformat()}

    # Append new trace
    trace_dict = {
        "task_name": trace.task_name,
        "steps": trace.steps,
        "duration_ms": trace.duration_ms,
        "mode": trace.mode,
        "success": trace.success,
        "metadata": trace.metadata,
        "timestamp": datetime.now().isoformat(),
    }
    data["traces"].append(trace_dict)
    data["updated_at"] = datetime.now().isoformat()

    # Save with rotation (keep last 1000 traces)
    if len(data["traces"]) > 1000:
        data["traces"] = data["traces"][-1000:]

    with open(history_path, "w") as f:
        json.dump(data, f, indent=2)


def save_telemetry_snapshot(snapshot: TelemetrySnapshot, telemetry_dir: Path) -> None:
    """
    Persist a telemetry snapshot for historical analysis.

    Args:
        snapshot: TelemetrySnapshot to save
        telemetry_dir: Directory to store telemetry snapshots
    """
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    # Load existing snapshots
    snapshots_file = telemetry_dir / "snapshots.json"
    if snapshots_file.exists():
        with open(snapshots_file) as f:
            data = json.load(f)
    else:
        data = {"snapshots": [], "created_at": datetime.now().isoformat()}

    # Append new snapshot
    snapshot_dict = {
        "total_tasks": snapshot.total_tasks,
        "mode_distribution": snapshot.mode_distribution,
        "p95_latency_ms": snapshot.p95_latency_ms,
        "rollback_count": snapshot.rollback_count,
        "macro_success_rate": snapshot.macro_success_rate,
        "emotional_states": snapshot.emotional_states,
        "metadata": snapshot.metadata,
        "timestamp": datetime.now().isoformat(),
    }
    data["snapshots"].append(snapshot_dict)
    data["updated_at"] = datetime.now().isoformat()

    # Save with rotation (keep last 1000 snapshots)
    if len(data["snapshots"]) > 1000:
        data["snapshots"] = data["snapshots"][-1000:]

    with open(snapshots_file, "w") as f:
        json.dump(data, f, indent=2)


def run_nightly_refinement(
    telemetry_dir: Path,
    refinement_dir: Path,
    analysis_window_days: int = 7,
) -> dict[str, Any]:
    """
    Analyze telemetry history and generate policy optimization proposals.

    Args:
        telemetry_dir: Directory with historical telemetry snapshots
        refinement_dir: Directory to save refinement reports
        analysis_window_days: Number of days to analyze (default: 7)

    Returns:
        Report dict with analysis results and policy proposals
    """
    # Load telemetry snapshots
    snapshots_file = telemetry_dir / "snapshots.json"
    if not snapshots_file.exists():
        return {
            "status": "no_telemetry",
            "message": "No telemetry snapshots found",
            "timestamp": datetime.now().isoformat(),
        }

    with open(snapshots_file) as f:
        data = json.load(f)

    snapshots_data = data.get("snapshots", [])
    if len(snapshots_data) == 0:
        return {
            "status": "no_snapshots",
            "message": "No snapshots to analyze",
            "timestamp": datetime.now().isoformat(),
        }

    # Convert to RefinementEngine's TelemetrySnapshot format
    refinement_snapshots = []
    for snap in snapshots_data:
        # Convert telemetry.TelemetrySnapshot to cognitive.refinement.TelemetrySnapshot
        refinement_snap = RefinementTelemetrySnapshot(
            total_tasks=snap.get("total_tasks", 0),
            mode_distribution=snap.get("mode_distribution", {}),
            p95_latency_ms=snap.get("p95_latency_ms", 0.0),
            token_denials=0,  # Not tracked yet in current telemetry
            rollback_count=snap.get("rollback_count", 0),
            macro_success_rate=snap.get("macro_success_rate", 0.0),
            emotional_states=snap.get("emotional_states", {}),
            metadata=snap.get("metadata", {}),
        )
        refinement_snapshots.append(refinement_snap)

    # Run refinement analysis
    engine = RefinementEngine()
    
    # Ingest recent snapshots (limit to analysis window)
    for snap in refinement_snapshots[-analysis_window_days:]:
        engine.ingest_telemetry(snap)
    
    report = engine.analyze()

    # Save refinement report
    refinement_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    report_dict = {
        "status": "success",
        "timestamp": report.timestamp,
        "snapshots_analyzed": len(refinement_snapshots[-analysis_window_days:]),
        "analysis_window_days": analysis_window_days,
        "metrics_summary": report.metrics_summary,
        "policy_changes": [
            {
                "category": pc.category,
                "parameter": pc.parameter,
                "old_value": pc.old_value,
                "new_value": pc.new_value,
                "reason": pc.reason,
                "impact": pc.impact,
            }
            for pc in report.changes
        ],
    }

    report_file = refinement_dir / f"refinement_report_{timestamp}.json"
    with open(report_file, "w") as f:
        json.dump(report_dict, f, indent=2)

    return report_dict


if __name__ == "__main__":
    # Demo: print scheduling instructions
    schedule_nightly_tasks()
