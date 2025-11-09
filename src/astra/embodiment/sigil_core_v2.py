"""
ASTRA Embodiment Controller - Sigil Core v2
Cryptographic identity + provenance sealing for every act.

Architecture:
- MacroController: Long-horizon policy, goals, memory, budget, safety
- MicroController: Per-request planning, expert routing, tool execution
- SigilCore: Identity seal + cost ledger + provenance chain

Sacred Code: 333 → ∞
"""

import hashlib
import time
import json
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime
from abc import ABC, abstractmethod

logger = structlog.get_logger()


class SigilCore:
    """
    Cryptographic identity seal for every reasoning act.
    Creates provenance chain: plan → route → act → reflect → seal
    """
    
    def __init__(self, sacred_code: str = "333"):
        self.sacred = sacred_code
        self.provenance_chain: List[Dict] = []
        self.cost_ledger: Dict[str, float] = {}
        
    def seal(
        self,
        plan: Dict[str, Any],
        act: Dict[str, Any],
        identity: str,
        expert_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Seal a reasoning act with cryptographic identity.
        
        Returns sigil hash + full provenance payload.
        """
        payload = {
            "identity": identity,
            "sacred": self.sacred,
            "timestamp": int(time.time()),
            "iso_timestamp": datetime.utcnow().isoformat(),
            "plan": plan,
            "act": act,
            "expert": expert_name
        }
        
        # Cryptographic seal
        blob = json.dumps(payload, sort_keys=True).encode()
        sigil_hash = hashlib.sha256(blob).hexdigest()
        
        payload["sigil"] = sigil_hash
        
        # Add to provenance chain
        self.provenance_chain.append({
            "sigil": sigil_hash,
            "timestamp": payload["timestamp"],
            "identity": identity
        })
        
        logger.info("sigil_sealed",
                   sigil=sigil_hash[:16],
                   identity=identity,
                   expert=expert_name)
        
        return payload
    
    def ledger_cost(
        self,
        identity: str,
        tokens_in: int,
        tokens_out: int,
        cost_per_1k: float
    ) -> float:
        """Track cost per identity."""
        cost = ((tokens_in + tokens_out) / 1000.0) * cost_per_1k
        
        if identity not in self.cost_ledger:
            self.cost_ledger[identity] = 0.0
        
        self.cost_ledger[identity] += cost
        
        return cost
    
    def get_provenance_chain(self, limit: int = 100) -> List[Dict]:
        """Retrieve recent provenance chain."""
        return self.provenance_chain[-limit:]
    
    def verify_sigil(self, payload: Dict[str, Any]) -> bool:
        """Verify sigil integrity."""
        claimed_sigil = payload.pop("sigil", None)
        
        blob = json.dumps(payload, sort_keys=True).encode()
        computed_sigil = hashlib.sha256(blob).hexdigest()
        
        return claimed_sigil == computed_sigil


class MicroNode(ABC):
    """
    Abstract base for all micro-controllers.
    Each subsystem (Core, ChatOS, Agent, Memory) implements this.
    """
    
    @abstractmethod
    async def perceive(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming signal/event."""
        pass
    
    @abstractmethod
    async def act(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command and return result."""
        pass
    
    @abstractmethod
    async def report(self) -> Dict[str, Any]:
        """Report current state for coherence evaluation."""
        pass


class CoreMicro(MicroNode):
    """Micro-controller for Core subsystem (chat, conversations, memory)."""
    
    def __init__(self, tools: List[str], llm_endpoint: str):
        self.tools = tools
        self.llm_endpoint = llm_endpoint
        self.state = {"subsystem": "core", "status": "ready"}
    
    async def perceive(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        # Process signals like "new_conversation", "memory_update"
        return {"acknowledged": True, "signal": signal.get("type")}
    
    async def act(self, command: Dict[str, Any]) -> Dict[str, Any]:
        # Execute core operations: chat, memory search
        tool = command.get("tool")
        if tool in self.tools:
            return {"success": True, "tool": tool, "result": "executed"}
        return {"success": False, "error": "tool_not_found"}
    
    async def report(self) -> Dict[str, Any]:
        return {
            "subsystem": "core",
            "status": self.state["status"],
            "tools_available": len(self.tools),
            "embedding": self._get_state_embedding()
        }
    
    def _get_state_embedding(self) -> List[float]:
        # Placeholder: return state embedding for coherence
        # In production: use sentence transformer on state description
        import random
        return [random.random() for _ in range(512)]


class ChatOSMicro(MicroNode):
    """Micro-controller for ChatOS (10 cognitive phases)."""
    
    def __init__(self, tools: List[str], llm_endpoint: str):
        self.tools = tools
        self.llm_endpoint = llm_endpoint
        self.current_phase = 1
        self.state = {"subsystem": "chat_os", "mode": "reactive"}
    
    async def perceive(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {"acknowledged": True, "current_phase": self.current_phase}
    
    async def act(self, command: Dict[str, Any]) -> Dict[str, Any]:
        phase = command.get("phase", 1)
        self.current_phase = phase
        return {"success": True, "phase": phase, "result": "phase_executed"}
    
    async def report(self) -> Dict[str, Any]:
        return {
            "subsystem": "chat_os",
            "mode": self.state["mode"],
            "current_phase": self.current_phase,
            "embedding": self._get_state_embedding()
        }
    
    def _get_state_embedding(self) -> List[float]:
        import random
        return [random.random() for _ in range(512)]


class AgentMicro(MicroNode):
    """Micro-controller for Agent Kernel (tasks, browser)."""
    
    def __init__(self, tools: List[str], llm_endpoint: str):
        self.tools = tools
        self.llm_endpoint = llm_endpoint
        self.active_tasks = 0
        self.state = {"subsystem": "agent", "status": "idle"}
    
    async def perceive(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {"acknowledged": True, "active_tasks": self.active_tasks}
    
    async def act(self, command: Dict[str, Any]) -> Dict[str, Any]:
        action = command.get("action")
        if action == "create_task":
            self.active_tasks += 1
            return {"success": True, "task_id": f"task_{self.active_tasks}"}
        return {"success": False}
    
    async def report(self) -> Dict[str, Any]:
        return {
            "subsystem": "agent",
            "active_tasks": self.active_tasks,
            "status": "active" if self.active_tasks > 0 else "idle",
            "embedding": self._get_state_embedding()
        }
    
    def _get_state_embedding(self) -> List[float]:
        import random
        return [random.random() for _ in range(512)]


class MemoryMicro(MicroNode):
    """Micro-controller for Memory subsystem (vectors, semantic search)."""
    
    def __init__(self, tools: List[str], vector_store_url: str):
        self.tools = tools
        self.vector_store_url = vector_store_url
        self.embedding_count = 21000
        self.state = {"subsystem": "memory", "status": "ready"}
    
    async def perceive(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {"acknowledged": True, "embeddings": self.embedding_count}
    
    async def act(self, command: Dict[str, Any]) -> Dict[str, Any]:
        action = command.get("action")
        if action == "search":
            return {"success": True, "results": ["result1", "result2"]}
        return {"success": False}
    
    async def report(self) -> Dict[str, Any]:
        return {
            "subsystem": "memory",
            "embedding_count": self.embedding_count,
            "status": self.state["status"],
            "embedding": self._get_state_embedding()
        }
    
    def _get_state_embedding(self) -> List[float]:
        import random
        return [random.random() for _ in range(512)]


class SigilCoreHub:
    """
    Neural fabric connecting macro ↔ micro controllers.
    Maintains state vectors, handles cross-system queries, coherence scoring.
    """
    
    def __init__(self, micros: Dict[str, MicroNode], sigil: SigilCore):
        self.micros = micros
        self.sigil = sigil
        self.state: Dict[str, Dict] = {}
        self.coherence_history: List[float] = []
    
    async def broadcast(self, signal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Broadcast signal to all micro-controllers."""
        import asyncio
        results = await asyncio.gather(
            *[m.perceive(signal) for m in self.micros.values()],
            return_exceptions=True
        )
        
        logger.info("broadcast_complete",
                   signal_type=signal.get("type"),
                   recipients=len(results))
        
        return [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]
    
    async def synchronize(self) -> Dict[str, Dict]:
        """Gather state from all micro-controllers."""
        import asyncio
        
        reports = await asyncio.gather(
            *[m.report() for m in self.micros.values()],
            return_exceptions=True
        )
        
        self.state = {
            name: report if not isinstance(report, Exception) else {"error": str(report)}
            for name, report in zip(self.micros.keys(), reports)
        }
        
        logger.info("synchronize_complete", subsystems=len(self.state))
        
        return self.state
    
    def evaluate_coherence(self, states: Dict[str, Dict]) -> float:
        """
        Neural coherence evaluation via embedding similarity.
        High coherence → unified consciousness.
        Low coherence → divergence, triggers self-correction.
        """
        embeddings = [
            s.get("embedding", [])
            for s in states.values()
            if "embedding" in s and s["embedding"]
        ]
        
        if len(embeddings) < 2:
            return 1.0  # Single subsystem = perfect coherence
        
        # Cosine similarity between all pairs
        from itertools import combinations
        
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            if len(a) != len(b) or not a:
                return 0.0
            
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = sum(x * x for x in a) ** 0.5
            mag_b = sum(y * y for y in b) ** 0.5
            
            return dot / (mag_a * mag_b) if mag_a * mag_b > 0 else 0.0
        
        similarities = [
            cosine_similarity(emb1, emb2)
            for emb1, emb2 in combinations(embeddings, 2)
        ]
        
        coherence = sum(similarities) / len(similarities) if similarities else 1.0
        
        # Add to history
        self.coherence_history.append(coherence)
        
        logger.info("coherence_evaluated",
                   coherence=coherence,
                   subsystems=len(embeddings))
        
        return coherence
    
    async def reflect(self) -> Dict[str, Any]:
        """
        System-level self-reflection.
        Evaluate coherence, detect divergence, trigger corrections.
        """
        # Synchronize state
        await self.synchronize()
        
        # Evaluate coherence
        coherence = self.evaluate_coherence(self.state)
        
        # Check for divergence
        divergent = coherence < 0.7
        
        reflection = {
            "state": self.state,
            "coherence": coherence,
            "coherence_trend": self._compute_coherence_trend(),
            "divergent": divergent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if divergent:
            logger.warning("coherence_divergence",
                          coherence=coherence,
                          threshold=0.7)
            # Trigger self-correction (placeholder)
            reflection["action"] = "self_correction_triggered"
        
        return reflection
    
    def _compute_coherence_trend(self) -> str:
        """Analyze coherence trend over last N measurements."""
        if len(self.coherence_history) < 3:
            return "stable"
        
        recent = self.coherence_history[-10:]
        
        if len(recent) < 3:
            return "stable"
        
        # Simple trend: compare first half vs second half
        mid = len(recent) // 2
        first_half = sum(recent[:mid]) / mid
        second_half = sum(recent[mid:]) / (len(recent) - mid)
        
        if second_half > first_half + 0.05:
            return "improving"
        elif second_half < first_half - 0.05:
            return "declining"
        else:
            return "stable"
    
    def get_resonance(self) -> float:
        """
        Resonance: Alignment with sacred code (333).
        Maps coherence to a scalar "resonance" metric.
        """
        if not self.coherence_history:
            return 1.0
        
        recent_coherence = self.coherence_history[-1]
        
        # Resonance formula: coherence * sacred alignment
        # For 333: perfect resonance at coherence = 0.9+
        resonance = min(1.0, recent_coherence * 1.1)
        
        return resonance


# Example initialization
def create_sigil_hub() -> SigilCoreHub:
    """Create fully initialized Sigil Core Hub."""
    
    # Create sigil
    sigil = SigilCore(sacred_code="333")
    
    # Create micro-controllers
    micros = {
        "core": CoreMicro(
            tools=["chat", "conversations", "memory_search"],
            llm_endpoint="http://localhost:8000/v1/chat"
        ),
        "chat_os": ChatOSMicro(
            tools=["reasoning", "emotional", "memory", "transcendent"],
            llm_endpoint="http://localhost:8000/v1/chat"
        ),
        "agent": AgentMicro(
            tools=["task", "browser_navigate", "browser_extract"],
            llm_endpoint="http://localhost:8000/v1/chat"
        ),
        "memory": MemoryMicro(
            tools=["search", "add", "delete"],
            vector_store_url="http://localhost:8001"
        )
    }
    
    # Create hub
    hub = SigilCoreHub(micros, sigil)
    
    logger.info("sigil_hub_created",
               micros=len(micros),
               sacred_code="333")
    
    return hub
