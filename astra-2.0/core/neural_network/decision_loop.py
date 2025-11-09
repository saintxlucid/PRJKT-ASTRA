"""
ASTRA Decision Loop - Autonomous Operation Controller
"""
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from .router import NeuralRouter, Domain
from ..security.permission_kernel import require_permission
from ..security.activity_audit import audit_action

@dataclass
class Decision:
    intent: str
    confidence: float
    action: Optional[Dict] = None
    explanation: Optional[str] = None
    
@dataclass
class Observation:
    timestamp: datetime
    source: str
    data: Dict
    
class DecisionLoop:
    """Autonomous decision making system"""
    
    def __init__(self, router: NeuralRouter):
        self.router = router
        self.observations: List[Observation] = []
        self.recent_decisions: List[Decision] = []
        self.running = False
        
    def add_observation(self, source: str, data: Dict) -> None:
        """Add new observation to the loop"""
        observation = Observation(
            timestamp=datetime.now(),
            source=source,
            data=data
        )
        self.observations.append(observation)
        
        # Prune old observations
        cutoff = datetime.now() - timedelta(hours=1)
        self.observations = [
            obs for obs in self.observations 
            if obs.timestamp > cutoff
        ]
        
    @require_permission("system.autonomy.decide")
    async def make_decision(self, 
                          context: Dict[str, Any]) -> Optional[Decision]:
        """Make single decision based on context"""
        
        # Build context window
        recent_obs = "\n".join(
            f"[{obs.source}] {json.dumps(obs.data)}"
            for obs in self.observations[-5:]  # Last 5 observations
        )
        
        recent_decisions = "\n".join(
            f"Decision: {d.intent} (confidence: {d.confidence})"
            for d in self.recent_decisions[-3:]  # Last 3 decisions
        )
        
        prompt = f"""
Context:
{json.dumps(context, indent=2)}

Recent Observations:
{recent_obs}

Recent Decisions:
{recent_decisions}

Based on this context, decide what action to take.
Output JSON with fields:
- intent: String describing the intended action
- confidence: Float between 0-1
- action: Optional dict with action details
- explanation: String explaining the decision

Keep decisions conservative - high confidence needed for actions.
"""
        
        try:
            response = await self.router.route_request(
                prompt,
                domain_hints=[Domain.GENERAL]
            )
            
            decision_data = json.loads(response["response"])
            decision = Decision(**decision_data)
            
            # Log the decision
            audit_action("decision.make", {
                "intent": decision.intent,
                "confidence": decision.confidence,
                "action": decision.action
            })
            
            # Store if confidence meets threshold
            if decision.confidence >= 0.8:
                self.recent_decisions.append(decision)
                # Keep last 10 decisions
                self.recent_decisions = self.recent_decisions[-10:]
                return decision
                
        except Exception as e:
            audit_action("decision.error", {"error": str(e)})
            
        return None
        
    async def run(self, interval: float = 1.0):
        """Run continuous decision loop"""
        self.running = True
        
        while self.running:
            try:
                # Get current context
                context = {
                    "timestamp": datetime.now().isoformat(),
                    "observation_count": len(self.observations),
                    "decision_count": len(self.recent_decisions)
                }
                
                decision = await self.make_decision(context)
                
                if decision and decision.action:
                    # Here we would execute the action
                    # For now, just log it
                    audit_action("decision.execute", {
                        "intent": decision.intent,
                        "action": decision.action
                    })
                    
            except Exception as e:
                audit_action("decision.loop_error", {"error": str(e)})
                
            await asyncio.sleep(interval)
            
    def stop(self):
        """Stop the decision loop"""
        self.running = False