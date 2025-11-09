"""Tests for compose skill."""
from __future__ import annotations

from chat_os.executor import execute_plan
from chat_os.plan import Plan, PlanMeta, PlanStep


def test_compose_document() -> None:
    """Test compose.document intent."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_compose", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="compose.document",
                args={
                    "source": "AI research papers from arXiv.\n- Paper 1: Deep learning\n- Paper 2: Reinforcement learning",
                    "format": "markdown",
                    "style": "brief",
                    "max_tokens": 500,
                },
            )
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    result = ctx.results[0]
    assert result.success
    assert result.output["ok"]
    assert "document" in result.output
    assert result.output["format"] == "markdown"
    assert result.output["style"] == "brief"


def test_compose_summarize() -> None:
    """Test compose.summarize intent."""
    long_content = """
    Machine learning is a subset of artificial intelligence that focuses on
    the development of algorithms that can learn from and make predictions on data.
    It has applications in various fields including computer vision, natural language
    processing, and robotics. Deep learning, a specialized form of machine learning,
    uses neural networks with multiple layers to extract high-level features from raw data.
    """

    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_summarize", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="compose.summarize",
                args={
                    "content": long_content,
                    "max_length": "short",
                    "focus": "key_points",
                },
            )
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    result = ctx.results[0]
    assert result.success
    assert result.output["ok"]
    assert "summary" in result.output
    assert result.output["original_length"] > result.output["summary_length"]


def test_compose_rewrite() -> None:
    """Test compose.rewrite intent."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_rewrite", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="compose.rewrite",
                args={
                    "content": "Hey dude, this AI stuff is pretty cool!",
                    "target_tone": "formal",
                    "preserve_facts": True,
                },
            )
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    result = ctx.results[0]
    assert result.success
    assert result.output["ok"]
    assert "rewritten" in result.output
    assert result.output["target_tone"] == "formal"


def test_compose_pipeline() -> None:
    """Test multi-step compose workflow."""
    raw_content = "Long technical document about quantum computing and its applications."

    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_pipeline", policy="info", max_time_ms=10000),
        steps=[
            # Step 0: Summarize raw content
            PlanStep(
                intent="compose.summarize",
                args={
                    "content": raw_content,
                    "max_length": "medium",
                },
            ),
            # Step 1: Save summary to memory
            PlanStep(
                intent="memory.save",
                args={
                    "path": "/temp/summary",
                    "content": "Summary generated",
                },
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 2
    assert all(r.success for r in ctx.results)

    # Verify pipeline flow
    assert ctx.results[0].intent == "compose.summarize"
    assert ctx.results[1].intent == "memory.save"
