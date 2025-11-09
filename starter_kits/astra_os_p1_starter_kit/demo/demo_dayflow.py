from __future__ import annotations

import json
import os
import time

from astra_core.emotion.context_engine import EmotionalContextEngine
from astra_core.lucid_protocol import LucidWeights, prioritize, steer_tone
from astra_core.memory.semantic_compression import Event, SemanticCompressor
from astra_core.meta_controller import (
    CognitiveGovernor,
    MetaController,
    ProceduralEngine,
    RiskLevel,
    StatisticalEngine,
    SymbolicEngine,
    Task,
)
from astra_core.security.pq_token import PQToken, TokenClaims


def main() -> None:
    weights = LucidWeights(
        truth_compassion=0.55,
        logic_intuition=0.60,
        order_freedom=0.45,
        efficiency_safety=0.55,
    )
    governor = CognitiveGovernor({"logic_intuition": weights.logic_intuition})
    controller = MetaController(SymbolicEngine(), StatisticalEngine(governor), ProceduralEngine(), governor)
    controller.learn_macro("daily_standup")

    emotion = EmotionalContextEngine()
    ambience = emotion.infer()
    print("[AMBIENCE]", json.dumps(ambience, indent=2))

    token_service = PQToken()
    claims = TokenClaims(
        sub="operator:saint_lucid",
        exp=int(time.time()) + 300,
        scope="ui+process",
        pid=os.getpid(),
    )
    token = token_service.issue(claims)
    print("[TOKEN]", "ok" if token_service.verify(token) else "bad")

    tasks = [
        Task("daily_standup", deterministic=True, risk=RiskLevel.LOW, kind="automation", payload={}),
        Task("reply_email", deterministic=False, risk=RiskLevel.LOW, kind="dialogue", payload={"thread": 3}),
        Task("delete_files", deterministic=True, risk=RiskLevel.HIGH, kind="file_op", payload={"path": "C:/tmp"}),
    ]
    for task in tasks:
        result = controller.run(task)
        print(f"[RUN] {task.name} -> {result['mode']} :: {result.get('notes', '')}")

    compressor = SemanticCompressor()
    for index in range(20):
        compressor.ingest(
            Event(kind="web", text=f"Visited URL #{index} about ASTRA OS Phase {index % 3} improvements")
        )
    compressed = compressor.compress()
    print("[COMPRESS]", len(compressed["concepts"]), "concepts,", compressed["count_events"], "events")

    actions = [
        {"name": "notify_team", "sequence": 1, "preference": 0.8},
        {"name": "write_report", "sequence": 2, "preference": 0.9},
        {"name": "start_break", "sequence": 3, "preference": 0.4},
    ]
    prioritized = prioritize(actions, weights)
    print("[PRIORITY]", prioritized)

    tone = steer_tone(error=True, weights=weights)
    print("[TONE]", tone)


if __name__ == "__main__":
    main()
