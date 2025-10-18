"""
ASTRA Router - Pre-tokenization Multimodal Dispatcher
======================================================
Sacred Code: 333

Routes VISION/AUDIO/CODE blocks to specialized tools before tokenization,
augments text with memory context, and applies consent gates to side-effect
operations. Falls back to core LLM for pure text after memory retrieval.

Author: ASTRA Fusion System
Date: October 18, 2025
"""

from __future__ import annotations
import re
import time
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()

# Pre-tokenization block markers
MODE_RX = re.compile(r"<\|mode_start\|>(.*?)<\|mode_end\|>", re.S)

try:
    from prometheus_client import Counter, Histogram

    ROUTE_HITS = Counter(
        "astra_route_hits",
        "Routed requests by type",
        ["route"],
    )
    ROUTE_LAT = Histogram(
        "astra_route_latency_seconds",
        "Route latency distribution",
        ["route"],
    )
except Exception:  # pragma: no cover - Prometheus may be unavailable in tests
    class _NoOpMetric:
        """Fallback metric when prometheus_client isn't installed."""

        def labels(self, *_args, **_kwargs):
            return self

        def inc(self, *_args, **_kwargs) -> None:
            return None

        def observe(self, *_args, **_kwargs) -> None:
            return None

    ROUTE_HITS = _NoOpMetric()
    ROUTE_LAT = _NoOpMetric()


def _slice_block(text: str, tag: str) -> Optional[str]:
    """
    Extract content between <|tag_start|> and <|tag_end|> markers.
    Returns None if markers not found.
    """
    try:
        start_marker = f"<|{tag}_start|>"
        end_marker = f"<|{tag}_end|>"
        s = text.index(start_marker) + len(start_marker)
        e = text.index(end_marker)
        return text[s:e].strip()
    except ValueError:
        return None


# Evolution phase markers (Phase-C)
PHASE_TAGS = ["sense", "plan", "act", "learn", "reflect"]


def split_phases(prompt: str) -> Dict[str, str]:
    """
    Parse evolution phases from prompt.
    
    Evolution phases enable structured AI reasoning workflow:
    - SENSE: Observation and data gathering
    - PLAN: Strategy formulation
    - ACT: Execution (consent-gated)
    - LEARN: Knowledge integration
    - REFLECT: Meta-cognition
    
    Example:
        <|sense|>User wants to analyze system logs</|sense|>
        <|plan|>Steps: 1. Read logs, 2. Parse errors, 3. Summarize</|plan|>
        <|act|>Execute log analysis</|act|>
        <|learn|>Discovered 3 critical errors</|learn|>
        <|reflect|>Need better error detection</|reflect|>
    
    Args:
        prompt: User input with evolution phase markers
        
    Returns:
        Dict mapping phase names to content
        
    Sacred Code: 333
    """
    phases = {}
    for tag in PHASE_TAGS:
        open_tag = f"<|{tag}|>"
        close_tag = f"</|{tag}|>"
        if open_tag in prompt and close_tag in prompt:
            try:
                start = prompt.index(open_tag) + len(open_tag)
                end = prompt.index(close_tag)
                phases[tag] = prompt[start:end].strip()
            except ValueError:
                continue
    return phases


class AstraRouter:
    """
    Pre-tokenization dispatcher for multimodal prompts.
    
    Routes VISION/AUDIO/CODE blocks to specialized tools before tokenization,
    augments text with retrieved memory, and applies consent gates to operations
    with side effects.
    
    Sacred Code: 333 embedded in all tool payloads for audit chaining.
    """
    
    def __init__(self, llm, tool_bus, memory, consent, budget: Optional[Dict[str, int]] = None):
        """
        Initialize AstraRouter.
        
        Args:
            llm: LLM backend with generate(prompt, max_tokens) method
            tool_bus: Tool execution bus with execute(name, payload) method
            memory: Memory service with retrieve_relevant(prompt, top_k) method
            consent: Consent gate with allowed(operation_name) method
            budget: Optional budget constraints (steps, tool_calls, walltime_s)
                    Defaults to standard profile: {steps: 5, tool_calls: 3, walltime_s: 60}
        """
        self.llm = llm
        self.tool_bus = tool_bus
        self.memory = memory
        self.consent = consent
        
        # Budget enforcement (Phase-C)
        self.budget = budget or {
            "steps": 5,
            "tool_calls": 3,
            "walltime_s": 60
        }
        self.current_steps = 0
        self.current_tool_calls = 0
        self.session_start = time.perf_counter()
        
        logger.info(
            "astra_router_initialized",
            budget_steps=self.budget.get("steps"),
            budget_tool_calls=self.budget.get("tool_calls"),
            budget_walltime_s=self.budget.get("walltime_s"),
            sacred_code=333
        )
    
    def _mode(self, prompt: str) -> str:
        """
        Extract mode from prompt markers.
        
        Looks for <|mode_start|>MODE_NAME<|mode_end|> markers.
        Defaults to COGNITION if not found.
        """
        m = MODE_RX.search(prompt)
        return (m.group(1).strip().upper() if m else "COGNITION")
    
    def _check_budget(self) -> bool:
        """
        Check if budget constraints are satisfied (Phase-C).
        
        Budget enforcement prevents runaway execution:
        - Steps: Maximum reasoning cycles
        - Tool calls: Maximum external tool invocations
        - Walltime: Maximum elapsed time in seconds
        
        Returns:
            True if within budget, False if exceeded
            
        Sacred Code: 333
        """
        # Check steps limit (-1 means unlimited)
        if self.budget["steps"] > 0 and self.current_steps >= self.budget["steps"]:
            return False
        
        # Check tool calls limit (-1 means unlimited)
        if self.budget["tool_calls"] > 0 and self.current_tool_calls >= self.budget["tool_calls"]:
            return False
        
        # Check walltime limit (-1 means unlimited)
        elapsed = time.perf_counter() - self.session_start
        if self.budget["walltime_s"] > 0 and elapsed >= self.budget["walltime_s"]:
            return False
        
        return True
    
    def _handle_evolution_phases(self, phases: Dict[str, str], mode: str, start_ts: float) -> str:
        """
        Handle evolution phase routing (Phase-C).
        
        Evolution phases (SENSE→PLAN→ACT→LEARN→REFLECT):
        - SENSE: Observation and data gathering (safe)
        - PLAN: Strategy formulation (safe)
        - ACT: Execution (REQUIRES CONSENT GATE)
        - LEARN: Knowledge integration (safe)
        - REFLECT: Meta-cognition (safe)
        
        ACT phase requires explicit consent to prevent unauthorized actions.
        
        Args:
            phases: Parsed evolution phases
            mode: Current mode (COGNITION, CODE, etc.)
            start_ts: Start timestamp for latency tracking
            
        Returns:
            Evolution phase processing result
            
        Sacred Code: 333
        """
        route = "evolution"
        
        # Strict consent gate for ACT phase
        if "act" in phases:
            if not self.consent.allowed("phase.act"):
                denial = f"❌ ACT phase denied (consent required). Sacred Code: 333\n\nBlocked action:\n{phases['act']}"
                elapsed = time.perf_counter() - start_ts
                ROUTE_HITS.labels(route="act_denied").inc(1)
                ROUTE_LAT.labels(route="act_denied").observe(elapsed)
                logger.warning(
                    "astra_router_act_phase_denied",
                    mode=mode,
                    act_content_length=len(phases["act"]),
                    sacred_code=333,
                    latency_s=elapsed
                )
                return denial
            
            logger.info(
                "astra_router_act_phase_approved",
                mode=mode,
                act_content_length=len(phases["act"]),
                sacred_code=333
            )
        
        # Increment step counter
        self.current_steps += 1
        
        # Process evolution phases
        phase_results = []
        for phase_name in PHASE_TAGS:
            if phase_name in phases:
                phase_content = phases[phase_name]
                phase_results.append(f"**{phase_name.upper()}**: {phase_content}")
                
                logger.info(
                    "astra_router_phase_processed",
                    phase=phase_name,
                    content_length=len(phase_content),
                    sacred_code=333
                )
        
        # Combine phase results
        result = "\n\n".join(phase_results)
        
        elapsed = time.perf_counter() - start_ts
        ROUTE_HITS.labels(route=route).inc(1)
        ROUTE_LAT.labels(route=route).observe(elapsed)
        logger.info(
            "astra_router_evolution_completed",
            mode=mode,
            phases_processed=len(phases),
            latency_s=elapsed,
            sacred_code=333
        )
        
        return result
    
    def handle(self, prompt: str) -> str:
        """
        Route prompt to appropriate handler based on modality markers.
        
        Processing order (first match wins):
        1. Evolution phases (SENSE→PLAN→ACT→LEARN→REFLECT with consent gate)
        2. CODE block (requires consent gate)
        3. VISION block (no consent needed)
        4. AUDIO block (no consent needed)
        5. TEXT (augmented with memory, sent to LLM)
        
        All tool executions include Sacred Code 333 for audit trail.
        
        Args:
            prompt: User input, may contain modality block markers
            
        Returns:
            Tool output or LLM generation
        """
        mode = self._mode(prompt)
        start_ts = time.perf_counter()
        
        logger.info(
            "astra_router_dispatch_start",
            mode=mode,
            prompt_length=len(prompt)
        )
        
        # Check budget enforcement (Phase-C)
        if not self._check_budget():
            denial = f"Budget exceeded (Sacred Code: 333). Steps: {self.current_steps}/{self.budget['steps']}, Tool calls: {self.current_tool_calls}/{self.budget['tool_calls']}"
            logger.warning(
                "astra_router_budget_exceeded",
                mode=mode,
                steps=self.current_steps,
                tool_calls=self.current_tool_calls,
                sacred_code=333
            )
            return denial
        
        # Evolution phase routing (Phase-C)
        phases = split_phases(prompt)
        if phases:
            return self._handle_evolution_phases(phases, mode, start_ts)
        
        # Extract modality blocks (before tokenization)
        vision = _slice_block(prompt, "vision")
        audio = _slice_block(prompt, "audio")
        code = _slice_block(prompt, "code")
        
        # CODE PATH: Requires consent gate
        if code:
            route = "code"
            if not self.consent.allowed("code"):
                denial = "Consent required for code operations. (Sacred Code: 333)"
                elapsed = time.perf_counter() - start_ts
                ROUTE_HITS.labels(route=route).inc(1)
                ROUTE_LAT.labels(route=route).observe(elapsed)
                logger.info(
                    "astra_router_code_denied",
                    mode=mode,
                    sacred_code=333,
                    latency_s=elapsed
                )
                return denial
            
            logger.info(
                "astra_router_code_approved",
                mode=mode,
                sacred_code=333
            )
            
            # Track budget usage (Phase-C)
            self.current_tool_calls += 1
            self.current_steps += 1
            
            result = self.tool_bus.execute(
                "code.apply_plan_or_summarize",
                payload={
                    "code_block": code,
                    "mode": mode,
                    "sacred_code": "333"
                }
            )
            elapsed = time.perf_counter() - start_ts
            ROUTE_HITS.labels(route=route).inc(1)
            ROUTE_LAT.labels(route=route).observe(elapsed)
            logger.info("astra_router_code_executed", mode=mode, latency_s=elapsed)
            return result
        
        # VISION PATH: No consent needed, high priority
        if vision:
            route = "vision"
            logger.info(
                "astra_router_vision_dispatch",
                mode=mode,
                sacred_code=333
            )
            
            # Track budget usage (Phase-C)
            self.current_tool_calls += 1
            self.current_steps += 1
            
            result = self.tool_bus.execute(
                "vision.describe_or_answer",
                payload={
                    "vision_block": vision,
                    "mode": mode,
                    "sacred_code": "333"
                }
            )
            elapsed = time.perf_counter() - start_ts
            ROUTE_HITS.labels(route=route).inc(1)
            ROUTE_LAT.labels(route=route).observe(elapsed)
            logger.info("astra_router_vision_executed", mode=mode, latency_s=elapsed)
            return result
        
        # AUDIO PATH: No consent needed
        if audio:
            route = "audio"
            logger.info(
                "astra_router_audio_dispatch",
                mode=mode,
                sacred_code=333
            )
            
            # Track budget usage (Phase-C)
            self.current_tool_calls += 1
            self.current_steps += 1
            
            result = self.tool_bus.execute(
                "audio.transcribe_or_analyze",
                payload={
                    "audio_block": audio,
                    "mode": mode,
                    "sacred_code": "333"
                }
            )
            elapsed = time.perf_counter() - start_ts
            ROUTE_HITS.labels(route=route).inc(1)
            ROUTE_LAT.labels(route=route).observe(elapsed)
            logger.info("astra_router_audio_executed", mode=mode, latency_s=elapsed)
            return result
        
        # TEXT PATH: Augment with memory and send to LLM
        logger.info(
            "astra_router_text_path",
            mode=mode
        )
        
        # Retrieve relevant memory context
        mem = self.memory.retrieve_relevant(prompt, top_k=6)
        
        # Augment prompt with memory context
        augmented = f"{mem}\n\n{prompt}"
        
        logger.info(
            "astra_router_memory_augmented",
            mode=mode,
            memory_length=len(mem),
            augmented_length=len(augmented)
        )
        
        # Generate via LLM
        result = self.llm.generate(augmented, max_tokens=512)
        
        elapsed = time.perf_counter() - start_ts
        ROUTE_HITS.labels(route="text").inc(1)
        ROUTE_LAT.labels(route="text").observe(elapsed)
        logger.info(
            "astra_router_llm_generated",
            mode=mode,
            result_length=len(result),
            latency_s=elapsed
        )
        
        return result
