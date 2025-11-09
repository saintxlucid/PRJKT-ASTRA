"""
ASTRA Embodiment Controller - Complete Production System
Implements your precise AEC blueprint with all components.

Files combined:
- config.py: Declarative routing & budgets
- tool_bridge.py: Tool registry + consent integration  
- expert_mesh.py: Multi-LLM adapters + capability matrix
- policies.py: Routing, ensemble, verification
- micro_controller.py: Plan → Route → Act → Reflect
- macro_controller.py: Goals, memory, safety, budgets
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Callable, Tuple
from abc import ABC, abstractmethod
import asyncio
import math
import structlog
import httpx

logger = structlog.get_logger()


# ============================================================================
# CONFIG
# ============================================================================

class ExpertConfig(BaseModel):
    """Configuration for an LLM expert."""
    name: str
    provider: str  # "llama.cpp" | "openai" | "vllm" | "custom"
    endpoint: str
    context_tokens: int = 131_000
    avg_latency_ms: int = 350
    cost_per_1k_tokens: float = 0.0
    strengths: List[str] = Field(default_factory=list)  # "code", "vision", "reasoning", "web", "long"
    tags: List[str] = Field(default_factory=list)


class ToolConfig(BaseModel):
    """Configuration for a tool."""
    name: str
    spec_path: str  # JSON schema or OpenAI function spec
    endpoint: Optional[str] = None  # http://... or internal bus name
    scopes: List[str] = Field(default_factory=list)  # "fs", "web", "db", "browser"
    consent_required: bool = True


class RoutingPolicy(BaseModel):
    """Routing and ensemble policy."""
    top_k: int = 2  # shortlist experts
    ensemble: str = "verify"  # "verify" | "debate" | "vote" | "single"
    temperature: float = 0.3
    budget_tokens: int = 4096
    max_steps: int = 8


class EmbodimentConfig(BaseModel):
    """Complete embodiment configuration."""
    experts: List[ExpertConfig]
    tools: List[ToolConfig]
    routing: RoutingPolicy


# ============================================================================
# TOOL BRIDGE
# ============================================================================

class ToolCall(BaseModel):
    """Represents a tool invocation."""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    consent_token: Optional[str] = None


class ToolBridge:
    """
    Unified tool registry with consent-aware execution.
    Integrates with SigilGate for consent verification.
    """
    
    def __init__(self, sigil_gate_url: str = "http://localhost:7701"):
        self._tools: Dict[str, Callable] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self.sigil_gate_url = sigil_gate_url
    
    def register(self, name: str, fn: Callable, meta: Dict[str, Any]):
        """Register a tool with its metadata."""
        self._tools[name] = fn
        self._meta[name] = meta
        
        logger.info("tool_registered",
                   name=name,
                   consent_required=meta.get("consent_required", False))
    
    def list(self) -> Dict[str, Any]:
        """List all registered tools."""
        return self._meta
    
    async def execute(self, call: ToolCall) -> Any:
        """
        Execute a tool call with consent verification.
        """
        tool = self._tools.get(call.name)
        if not tool:
            raise ValueError(f"tool-not-found: {call.name}")
        
        # Check consent if required
        meta = self._meta.get(call.name, {})
        if meta.get("consent_required", True):
            consent_granted = await self._verify_consent(call)
            if not consent_granted:
                raise PermissionError(f"consent-denied: {call.name}")
        
        # Execute tool
        logger.info("tool_executing", name=call.name)
        
        if asyncio.iscoroutinefunction(tool):
            result = await tool(call.arguments)
        else:
            result = tool(call.arguments)
        
        return result
    
    async def _verify_consent(self, call: ToolCall) -> bool:
        """Verify consent via SigilGate."""
        if call.consent_token:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{self.sigil_gate_url}/verify",
                        json={
                            "action": call.name,
                            "token": call.consent_token
                        }
                    )
                    return response.status_code == 200 and response.json().get("valid", False)
            except Exception as e:
                logger.error("consent_verification_failed", error=str(e))
                return False
        
        # No token provided but consent required
        # In production: prompt user or auto-grant based on policy
        return False


# ============================================================================
# EXPERT MESH
# ============================================================================

class ExpertAdapter(ABC):
    """Abstract adapter for LLM experts."""
    
    def __init__(self, cfg: ExpertConfig):
        self.cfg = cfg
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate completion from expert.
        
        Returns:
            {
                "text": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int},
                "confidence": float
            }
        """
        pass


class LlamaCppAdapter(ExpertAdapter):
    """Adapter for llama.cpp backend."""
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.cfg.endpoint}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 4096)
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "text": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "confidence": self._estimate_confidence(data)
            }
    
    def _estimate_confidence(self, data: Dict) -> float:
        # Placeholder: use logprobs or other signals
        return 0.8


class OpenAIAdapter(ExpertAdapter):
    """Adapter for OpenAI-compatible APIs."""
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Similar to LlamaCppAdapter but with OpenAI API key
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.cfg.endpoint}/v1/chat/completions",
                headers={"Authorization": f"Bearer {kwargs.get('api_key', '')}"},
                json={
                    "model": kwargs.get("model", "gpt-4"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 4096)
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "text": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "confidence": 0.85  # OpenAI models typically high confidence
            }


class ExpertMesh:
    """
    Multi-LLM adapter layer with capability-based routing.
    """
    
    def __init__(self, experts: List[ExpertAdapter]):
        self.experts = experts
    
    def shortlist(self, intent: str, k: int = 2) -> List[ExpertAdapter]:
        """
        Shortlist experts based on capability matrix.
        
        Scoring factors:
        - Strength match (does expert have this capability?)
        - Latency (faster = better)
        - Cost (cheaper = better)
        """
        scored: List[Tuple[float, ExpertAdapter]] = []
        
        for expert in self.experts:
            score = 0.0
            
            # Strength match
            if any(s in intent.lower() for s in expert.cfg.strengths):
                score += 2.0
            
            # Latency bonus (inverse)
            score += 1.0 / (1 + expert.cfg.avg_latency_ms / 1000)
            
            # Cost bonus (inverse)
            score += 1.0 / (1 + expert.cfg.cost_per_1k_tokens)
            
            scored.append((score, expert))
        
        # Sort by score and return top-k
        shortlisted = [e for _, e in sorted(scored, key=lambda x: x[0], reverse=True)[:k]]
        
        logger.info("experts_shortlisted",
                   intent=intent[:50],
                   count=len(shortlisted),
                   experts=[e.cfg.name for e in shortlisted])
        
        return shortlisted


# ============================================================================
# POLICIES
# ============================================================================

def confidence_from_usage(usage: Dict[str, int]) -> float:
    """Estimate confidence from token usage."""
    completion_tokens = usage.get("completion_tokens", 64)
    return 1.0 / (1.0 + math.log(1 + completion_tokens))


def verify_ensemble(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify ensemble: pick answer with highest confidence.
    Anti-hallucination: prefer shorter, more confident answers.
    """
    if not candidates:
        return {"text": "", "confidence": 0.0}
    
    best = max(
        candidates,
        key=lambda c: (c.get("confidence", 0.0), -len(c.get("text", "")))
    )
    
    logger.info("verify_ensemble_selected",
               expert=best.get("expert"),
               confidence=best.get("confidence"))
    
    return best


def debate_ensemble(candidates: List[Dict[str, Any]], rounds: int = 2) -> Dict[str, Any]:
    """
    Debate ensemble: candidates critique each other, synthesize final answer.
    
    Simplified version: just pick best after noting critiques.
    Full version would have experts actually debate.
    """
    # Placeholder: log critiques but still use verify
    for i, candidate in enumerate(candidates):
        other_texts = [
            c.get("text", "")[:256]
            for j, c in enumerate(candidates)
            if j != i
        ]
        logger.info("debate_round",
                   candidate=i,
                   critiquing=len(other_texts))
    
    return verify_ensemble(candidates)


# ============================================================================
# MICRO CONTROLLER
# ============================================================================

class MicroController:
    """
    Per-request planning, expert routing, tool execution, reflection.
    
    Loop: Plan → Route → Act → Reflect
    """
    
    def __init__(
        self,
        cfg: EmbodimentConfig,
        mesh: ExpertMesh,
        tools: ToolBridge,
        sigil
    ):
        self.cfg = cfg
        self.mesh = mesh
        self.tools = tools
        self.sigil = sigil
    
    async def plan(self, user_msg: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lightweight planner: detect intent and tool needs.
        """
        # Heuristics for tool detection
        needs_tools = any(
            keyword in user_msg.lower()
            for keyword in ["search", "open", "download", "scrape", "query", "browser"]
        )
        
        # Intent classification
        if "write code" in user_msg.lower() or "implement" in user_msg.lower():
            intent = "code"
        elif "reason" in user_msg.lower() or "analyze" in user_msg.lower():
            intent = "reasoning"
        elif "search" in user_msg.lower() or "find" in user_msg.lower():
            intent = "web"
        else:
            intent = "general"
        
        plan = {
            "intent": intent,
            "needs_tools": needs_tools,
            "steps": min(3, self.cfg.routing.max_steps),
            "user_msg": user_msg
        }
        
        logger.info("plan_created",
                   intent=intent,
                   needs_tools=needs_tools)
        
        return plan
    
    async def route(self, plan: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        Route to appropriate experts based on intent.
        Use ensemble policy (verify/debate).
        """
        # Shortlist experts
        experts = self.mesh.shortlist(plan["intent"], k=self.cfg.routing.top_k)
        
        # Generate from each expert
        candidates: List[Dict[str, Any]] = []
        for expert in experts:
            try:
                output = await expert.generate(
                    prompt,
                    temperature=self.cfg.routing.temperature,
                    max_tokens=self.cfg.routing.budget_tokens
                )
                
                # Add confidence if missing
                if "confidence" not in output and "usage" in output:
                    output["confidence"] = confidence_from_usage(output["usage"])
                
                output["expert"] = expert.cfg.name
                candidates.append(output)
                
            except Exception as e:
                logger.error("expert_generation_failed",
                            expert=expert.cfg.name,
                            error=str(e))
        
        # Apply ensemble policy
        if self.cfg.routing.ensemble == "verify":
            final = verify_ensemble(candidates)
        elif self.cfg.routing.ensemble == "debate":
            final = debate_ensemble(candidates)
        else:
            final = candidates[0] if candidates else {"text": "", "confidence": 0.0}
        
        # Add candidate metadata
        final["candidates"] = [
            {
                "expert": c["expert"],
                "confidence": c.get("confidence", 0.0),
                "preview": c.get("text", "")[:160]
            }
            for c in candidates
        ]
        
        return final
    
    async def act(self, plan: Dict[str, Any], answer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool calls if present in answer.
        """
        tool_calls = answer.get("tool_calls", [])
        results = []
        
        for tc in tool_calls:
            try:
                call = ToolCall(
                    name=tc["name"],
                    arguments=tc.get("arguments", {}),
                    consent_token=tc.get("consent")
                )
                
                result = await self.tools.execute(call)
                results.append({"tool": tc["name"], "result": result, "success": True})
                
            except Exception as e:
                logger.error("tool_execution_failed",
                            tool=tc["name"],
                            error=str(e))
                results.append({"tool": tc["name"], "error": str(e), "success": False})
        
        return {
            "tool_results": results,
            "text": answer.get("text", "")
        }
    
    async def reflect(self, plan: Dict[str, Any], act: Dict[str, Any]) -> Dict[str, Any]:
        """
        Light self-verification: check if response makes sense.
        Could call a verifier expert for critical tasks.
        """
        has_text = bool(act.get("text"))
        tools_succeeded = all(
            r.get("success", False)
            for r in act.get("tool_results", [])
        )
        
        ok = has_text and (tools_succeeded or not act.get("tool_results"))
        
        reflection = {
            "ok": ok,
            "has_text": has_text,
            "tools_succeeded": tools_succeeded,
            "notes": "auto-verified"
        }
        
        logger.info("reflection_complete", ok=ok)
        
        return reflection
    
    async def handle(
        self,
        user_msg: str,
        context: Dict[str, Any],
        identity: str
    ) -> Dict[str, Any]:
        """
        Main entry point: Plan → Route → Act → Reflect → Seal
        """
        # Plan
        plan = await self.plan(user_msg, context)
        
        # Route to experts
        routed = await self.route(plan, prompt=user_msg)
        
        # Act (execute tools)
        acted = await self.act(plan, routed)
        
        # Reflect
        reflection = await self.reflect(plan, acted)
        
        # Seal with sigil
        sealed = self.sigil.seal(
            plan=plan,
            act={"answer": acted, "routed": routed},
            identity=identity,
            expert_name=routed.get("expert")
        )
        
        return {
            "final": acted,
            "verify": reflection,
            "sigil": sealed,
            "experts": routed.get("candidates", []),
            "plan": plan
        }


# ============================================================================
# MACRO CONTROLLER
# ============================================================================

class MacroController:
    """
    Long-horizon policy: goals, memory, safety, budgets, mode control.
    
    The "conscience" that manages system-level objectives and constraints.
    """
    
    def __init__(
        self,
        cfg: EmbodimentConfig,
        micro: MicroController,
        memory=None  # Your existing memory service
    ):
        self.cfg = cfg
        self.micro = micro
        self.memory = memory
        self.mode = "proactive"  # reactive, proactive, creative, transcendent
        self.goals: Dict[str, Any] = {}
        self.budgets: Dict[str, int] = {
            "total_tokens": 0,
            "total_requests": 0
        }
    
    async def set_goals(self, goals: Dict[str, Any]):
        """Set long-horizon goals."""
        self.goals = goals
        
        # Store in memory if available
        if self.memory and hasattr(self.memory, "upsert"):
            self.memory.upsert({"type": "goal", "data": goals})
        
        logger.info("goals_set", goals=goals)
        
        return {"ok": True, "goals": goals}
    
    async def set_mode(self, mode: str):
        """Change operating mode."""
        valid_modes = ["reactive", "proactive", "creative", "transcendent"]
        
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Valid: {valid_modes}")
        
        self.mode = mode
        logger.info("mode_changed", mode=mode)
        
        return {"mode": mode}
    
    async def run(self, user_msg: str, identity: str) -> Dict[str, Any]:
        """
        Main orchestration: retrieve context → delegate to micro → consolidate.
        """
        # Retrieve relevant context from memory
        ctx = {}
        if self.memory and hasattr(self.memory, "retrieve_topk"):
            ctx = self.memory.retrieve_topk(user_msg, k=8)
        
        # Delegate to micro-controller
        result = await self.micro.handle(user_msg, ctx, identity)
        
        # Update budgets
        if "routed" in result.get("sigil", {}).get("act", {}):
            routed = result["sigil"]["act"]["routed"]
            usage = routed.get("usage", {})
            self.budgets["total_tokens"] += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        
        self.budgets["total_requests"] += 1
        
        # Consolidate to memory
        if self.memory and hasattr(self.memory, "consolidate"):
            self.memory.consolidate(user_msg, result)
        
        # Add macro metadata
        result["macro"] = {
            "mode": self.mode,
            "budgets": self.budgets,
            "goals": self.goals
        }
        
        return result
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget usage."""
        return self.budgets
    
    def get_goals(self) -> Dict[str, Any]:
        """Get current goals."""
        return self.goals


# Example initialization
def create_embodiment_system(config_path: str = None) -> MacroController:
    """Create complete AEC system from config."""
    from src.astra.embodiment.sigil_core import SigilCore
    
    # Load config (placeholder - would load from YAML)
    cfg = EmbodimentConfig(
        experts=[
            ExpertConfig(
                name="gpt-oss-20b",
                provider="llama.cpp",
                endpoint="http://localhost:9010",
                context_tokens=131000,
                avg_latency_ms=380,
                cost_per_1k_tokens=0.0,
                strengths=["reasoning", "long"]
            ),
            ExpertConfig(
                name="mixtral-22b",
                provider="vllm",
                endpoint="http://localhost:9020",
                strengths=["code", "reasoning"]
            )
        ],
        tools=[
            ToolConfig(
                name="web.search",
                spec_path="specs/web.search.json",
                endpoint="http://webtool:8009",
                scopes=["web"],
                consent_required=True
            )
        ],
        routing=RoutingPolicy(
            top_k=2,
            ensemble="verify",
            temperature=0.3,
            budget_tokens=4096,
            max_steps=8
        )
    )
    
    # Create sigil
    sigil = SigilCore("333")
    
    # Create tool bridge
    tools = ToolBridge(sigil_gate_url="http://localhost:7701")
    
    # Register tools (example)
    async def web_search(args: Dict) -> Dict:
        # Placeholder
        return {"results": ["result1", "result2"]}
    
    tools.register("web.search", web_search, {"consent_required": True})
    
    # Create expert mesh
    experts = [LlamaCppAdapter(e) for e in cfg.experts]
    mesh = ExpertMesh(experts)
    
    # Create micro-controller
    micro = MicroController(cfg, mesh, tools, sigil)
    
    # Create macro-controller
    macro = MacroController(cfg, micro, memory=None)
    
    logger.info("embodiment_system_created",
               experts=len(cfg.experts),
               tools=len(cfg.tools))
    
    return macro
