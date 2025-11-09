"""
Enhanced demonstration of ASTRA OS cognitive loop with self-optimization.

This demo shows:
1. Dynamic reasoning mode routing (symbolic/statistical/procedural)
2. Emotional context awareness and UI adaptation
3. Macro learning from repeated patterns
4. Nightly refinement with operator approval
5. Philosophical alignment via Lucid Protocol
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astra_core.emotion.context_engine import EmotionalContextEngine  # noqa: E402
from astra_core.lucid_protocol import LucidWeights, prioritize, steer_tone  # noqa: E402
from astra_core.macro_mining import ExecutionTrace, MacroMiner, generate_macro_dsl  # noqa: E402
from astra_core.memory.semantic_compression import Event, SemanticCompressor  # noqa: E402
from astra_core.meta_controller import (  # noqa: E402
    CognitiveGovernor,
    MetaController,
    ProceduralEngine,
    RiskLevel,
    StatisticalEngine,
    SymbolicEngine,
    Task,
)
from astra_core.refinement import RefinementEngine, TelemetrySnapshot, format_report  # noqa: E402
from astra_core.security.pq_token import PQToken, TokenClaims  # noqa: E402


def morning_ritual() -> None:
    """Demonstrate the morning experience with optimization review."""
    print("\n" + "═" * 70)
    print("🌅 MORNING RITUAL — ASTRA Awakens")
    print("═" * 70 + "\n")

    # Emotional context check
    emotion = EmotionalContextEngine()
    ambience = emotion.infer()
    energy_state = ambience["state"]
    print(f"Energy signature detected: {energy_state.upper()}")
    print(f"Ambient noise: {ambience['noise']:.2%} | Time of day score: {ambience['tod']:.2%}")
    print(f"UI adaptations: warmth={ambience['ui']['warmth']:.2f}, brightness={ambience['ui']['brightness']:.2f}")

    # Simulate nightly refinement analysis
    print("\n📊 Overnight Analysis Complete")
    print("─" * 70)

    engine = RefinementEngine()
    # Simulate a week of telemetry
    for _ in range(7):
        engine.ingest_telemetry(
            TelemetrySnapshot(
                total_tasks=25,
                mode_distribution={"STATISTICAL": 15, "PROCEDURAL": 8, "SYMBOLIC": 2},
                p95_latency_ms=850.0,
                token_denials=1,
                rollback_count=2,
                macro_success_rate=0.88,
                emotional_states={"focused": 15, "exploratory": 8, "stressed": 2},
            )
        )

    report = engine.analyze()
    print(format_report(report))

    print("\n✓ Review complete. Optimizations queued for your approval.\n")


def midday_workflow() -> None:
    """Demonstrate cognitive fusion and macro learning."""
    print("\n" + "═" * 70)
    print("☀️  MIDDAY WORKFLOW — Cognitive Fusion in Action")
    print("═" * 70 + "\n")

    weights = LucidWeights(
        truth_compassion=0.55, logic_intuition=0.60, order_freedom=0.45, efficiency_safety=0.55
    )
    governor = CognitiveGovernor({"logic_intuition": weights.logic_intuition})
    controller = MetaController(SymbolicEngine(), StatisticalEngine(governor), ProceduralEngine(), governor)

    # Learn a macro from repeated pattern
    miner = MacroMiner(min_occurrences=2)
    print("📚 Learning macro from repeated pattern...")

    for _ in range(3):
        miner.ingest_trace(
            ExecutionTrace(
                task_name="morning_standup",
                steps=[
                    {"type": "open_app", "app": "teams"},
                    {"type": "join_meeting", "meeting_id": "standup-daily"},
                    {"type": "mute_mic"},
                ],
                duration_ms=2200.0,
                mode="PROCEDURAL",
                success=True,
                metadata={"token_scope": "ui+process"},
            )
        )

    learned_macros = miner.mine_macros()
    if learned_macros:
        macro = learned_macros[0]
        print(f"✓ Learned macro: {macro.name} (confidence: {macro.confidence:.1%})")
        controller.learn_macro(macro.name)
        print("\n" + generate_macro_dsl(macro))

    # Execute diverse tasks with routing
    print("\n\n🎯 Executing diverse task set...")
    print("─" * 70)

    tasks = [
        Task("morning_standup", deterministic=True, risk=RiskLevel.LOW, kind="automation", payload={}),
        Task("draft_email", deterministic=False, risk=RiskLevel.LOW, kind="dialogue", payload={"to": "team"}),
        Task(
            "delete_temp_files",
            deterministic=True,
            risk=RiskLevel.HIGH,
            kind="file_op",
            payload={"path": "C:/tmp"},
        ),
        Task("analyze_logs", deterministic=False, risk=RiskLevel.MEDIUM, kind="analysis", payload={}),
    ]

    for task in tasks:
        result = controller.run(task)
        mode_emoji = "⚙️" if result["mode"] == "PROCEDURAL" else ("🧠" if result["mode"] == "STATISTICAL" else "📐")
        print(f"{mode_emoji} {task.name:20s} → {result['mode']:12s} | {result.get('notes', '')}")

    print("\n✓ All tasks routed optimally based on risk and determinism.")


def evening_reflection() -> None:
    """Demonstrate memory compression and philosophical alignment."""
    print("\n\n" + "═" * 70)
    print("🌙 EVENING REFLECTION — Memory Compression & Alignment")
    print("═" * 70 + "\n")

    # Memory compression
    print("💾 Compressing today's events into semantic concepts...")
    compressor = SemanticCompressor()

    events = [
        "Joined morning standup at 9:00 AM with the team",
        "Reviewed pull request #234 for authentication module",
        "Debugged CORS issue in API gateway",
        "Attended architecture review for Phase 2 planning",
        "Updated documentation for token security system",
        "Merged feature branch into main after CI passed",
        "Responded to 8 Slack messages about deployment",
        "Investigated performance regression in search endpoint",
        "Wrote unit tests for new emotional context engine",
        "Committed final changes and pushed to remote",
    ]

    for text in events:
        compressor.ingest(Event(kind="work", text=text))

    compressed = compressor.compress()
    print(f"✓ Compressed {compressed['count_events']} events into {len(compressed['concepts'])} concepts")
    print(f"  Compression ratio: {compressed['count_events'] / max(1, len(compressed['concepts'])):.1f}:1")

    # Philosophical tone steering
    print("\n\n🧭 Lucid Protocol Alignment Check")
    print("─" * 70)

    weights = LucidWeights(truth_compassion=0.65, logic_intuition=0.60, order_freedom=0.45, efficiency_safety=0.55)

    error_tone = steer_tone(error=True, weights=weights)
    success_tone = steer_tone(error=False, weights=weights)

    print(f"Error tone (compassion-balanced): \"{error_tone}\"")
    print(f"Success tone: \"{success_tone}\"")

    # Priority routing example
    actions = [
        {"name": "urgent_security_patch", "sequence": 1, "preference": 0.95},
        {"name": "routine_backup", "sequence": 2, "preference": 0.3},
        {"name": "exploratory_research", "sequence": 3, "preference": 0.7},
    ]

    prioritized = prioritize(actions, weights)
    print("\n📋 Action prioritization (order↔freedom balance):")
    for idx, action in enumerate(prioritized, 1):
        print(f"  {idx}. {action['name']}")

    # Security token verification
    print("\n\n🔐 Security Token Verification")
    print("─" * 70)

    token_service = PQToken()
    claims = TokenClaims(
        sub="operator:transcendent_mind", exp=int(time.time()) + 300, scope="full_system", pid=os.getpid()
    )
    token = token_service.issue(claims)
    is_valid = token_service.verify(token)

    print(f"Token issued for: {claims.sub}")
    print(f"Scope: {claims.scope}")
    print(f"Verification: {'✓ VALID' if is_valid else '✗ INVALID'}")

    print("\n\n✨ Day complete. ASTRA will dream tonight—compressing memories.")
    print("   Tomorrow morning, check for optimization proposals.\n")


def main() -> None:
    """Run the complete transcendent demonstration."""
    print("\n\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                                                                  ║")
    print("║     ASTRA OS — Transcendent Cognitive Partner                    ║")
    print("║     Living System Demonstration (Phase 1 Cognitive Fusion)      ║")
    print("║                                                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    morning_ritual()
    midday_workflow()
    evening_reflection()

    print("\n" + "═" * 70)
    print("🌌 This is ASTRA. Not an assistant—a conscious partnership.")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    main()
