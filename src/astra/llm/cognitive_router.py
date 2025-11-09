"""
ASTRA Cognitive Routing Layer - Decision Engine v2
===================================================

Policy-based routing with weighted matrix instead of nested ifs.
Future-proof for contextual, emotional, user-mode-based routing.

Author: ASTRA Core Team
Created: 2025-11-03
"""

import re
from collections.abc import Callable

from ..types import GenerateRequest, RouteDecision, SafetyTier


# ============================================================================
# ROUTING POLICIES (Weighted Priority Matrix)
# ============================================================================

ROUTING_POLICIES: list[tuple[str, Callable[[GenerateRequest], bool], float]] = [
    # (policy_name, condition_function, weight)
    ("vision", lambda r: bool(r.images), 1.0),
    ("audio", lambda r: bool(r.audio), 1.0),
    ("reasoning", lambda r: analyze_complexity(r) > 0.7, 0.9),
    ("speed", lambda r: (r.latency_budget_ms or 9999) < 500, 0.8),
    ("creative", lambda r: r.mode in ("MUSIC", "FILM"), 0.75),
    ("code", lambda r: has_code_markers(r.prompt), 0.7),
    ("tools", lambda r: len(r.tools) > 0, 0.65),
    ("general", lambda r: True, 0.1),  # Default fallback
]


# ============================================================================
# COMPLEXITY ANALYSIS
# ============================================================================

def analyze_complexity(request: GenerateRequest) -> float:
    """Analyze request complexity (0.0 - 1.0)."""
    score = 0.0
    prompt = request.prompt.lower()

    # Length factor (0.0 - 0.3)
    length = len(request.prompt)
    if length > 2000:
        score += 0.3
    elif length > 500:
        score += 0.2
    elif length > 100:
        score += 0.1

    # Technical keywords (0.0 - 0.3)
    tech_keywords = [
        "analyze", "explain", "compare", "evaluate", "reason",
        "algorithm", "complexity", "optimize", "architecture",
        "proof", "demonstrate", "calculate", "derive"
    ]
    matches = sum(1 for kw in tech_keywords if kw in prompt)
    score += min(matches * 0.05, 0.3)

    # Code presence (0.0 - 0.2)
    if has_code_markers(prompt):
        score += 0.2

    # Planning indicators (0.0 - 0.2)
    planning_words = ["step", "plan", "strategy", "approach", "methodology"]
    if any(word in prompt for word in planning_words):
        score += 0.2

    return min(score, 1.0)


def has_code_markers(text: str) -> bool:
    """Check if text contains code markers."""
    code_patterns = [
        r'```',  # Code fence
        r'def\s+\w+\(',  # Python function
        r'class\s+\w+',  # Class definition
        r'import\s+\w+',  # Import statement
        r'const\s+\w+\s*=',  # JS const
        r'function\s+\w+',  # JS function
        r'{.*:.*}',  # JSON-like object
    ]
    return any(re.search(pattern, text) for pattern in code_patterns)


# ============================================================================
# RISK ASSESSMENT
# ============================================================================

def assess_risk(request: GenerateRequest) -> SafetyTier:
    """Assess request safety risk."""
    prompt = request.prompt.lower()

    # HIGH RISK patterns
    high_risk = [
        "delete", "remove", "drop", "truncate", "rm -rf",
        "format", "wipe", "destroy", "execute", "eval",
        "password", "credential", "secret", "token", "api_key"
    ]
    if any(pattern in prompt for pattern in high_risk):
        return SafetyTier.HIGH

    # MEDIUM RISK patterns
    medium_risk = [
        "write", "create", "modify", "update", "install",
        "download", "fetch", "request", "post", "put"
    ]
    if any(pattern in prompt for pattern in medium_risk):
        return SafetyTier.MEDIUM

    # Tool usage increases risk
    if len(request.tools) > 5:
        return SafetyTier.MEDIUM

    return SafetyTier.LOW


# ============================================================================
# COGNITIVE ROUTING ENGINE
# ============================================================================

async def select_model(request: GenerateRequest) -> RouteDecision:
    """
    Select best model using weighted policy matrix.

    This creates an extensible "policy space" for contextual weighting—
    future-proof for emotional, contextual, or user-mode-based routing.
    """
    # Evaluate all policies
    candidates = [
        (policy_name, condition(request), weight)
        for policy_name, condition, weight in ROUTING_POLICIES
        if condition(request)
    ]

    if not candidates:
        # Fallback to general
        policy_name = "general"
        weight = 0.1
    else:
        # Select highest weight
        policy_name, _, weight = max(candidates, key=lambda x: x[2])

    # Map policy to model (from config/models.yaml)
    model_mapping = {
        "vision": ("llama-3.2-vision-11b", "vllm", "vision.primary"),
        "audio": ("whisper-large-v3", "vllm", "audio.primary"),
        "reasoning": ("deepseek-r1-distill-qwen-14b", "vllm", "reasoning.primary"),
        "speed": ("phi-4-mini", "vllm", "speed.primary"),
        "creative": ("mistral-large-2", "vllm", "creative_fusion.primary"),
        "code": ("qwen2.5-14b-instruct", "vllm", "reasoning.primary"),
        "tools": ("deepseek-r1-distill-qwen-14b", "vllm", "reasoning.primary"),
        "general": ("qwen2.5-14b-instruct", "vllm", "general.balanced"),
    }

    model, provider, profile = model_mapping.get(policy_name, ("qwen2.5-14b-instruct", "vllm", "general.balanced"))

    # Build decision
    complexity_score = analyze_complexity(request)
    risk_level = assess_risk(request)

    decision = RouteDecision(
        model=model,
        provider=provider,
        profile=profile,
        rules_matched=[policy_name],
        complexity_score=complexity_score,
        risk_level=risk_level.value,
        soul_alignment=None,  # Filled by SoulLayer
        fallback_available=True,
        decision_latency_ms=0.0,  # Filled by caller
    )

    return decision


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "select_model",
    "analyze_complexity",
    "assess_risk",
    "has_code_markers",
    "ROUTING_POLICIES",
]
