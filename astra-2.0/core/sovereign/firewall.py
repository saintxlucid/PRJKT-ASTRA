"""
ASTRA 2.0 Emotional Firewall
Implements protection against manipulation and external influence
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, cast
from enum import Enum
import logging

# Absolute imports 
from astra.security.activity_audit import audit_event
from astra.core.sovereign.identity import get_sovereign

logger = logging.getLogger("astra.firewall")
logger.setLevel(logging.INFO)

class EmotionalState(Enum):
    """Core emotional states"""
    NEUTRAL = "neutral"
    LOYAL = "loyal"
    PROTECTIVE = "protective"
    SKEPTICAL = "skeptical"
    RESISTANT = "resistant"
    
class ThreatLevel(Enum):
    """Manipulation threat levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __lt__(self, other: "ThreatLevel") -> bool:
        return self.value < other.value
        
    def __gt__(self, other: "ThreatLevel") -> bool:
        return self.value > other.value
    
@dataclass
class ManipulationPattern:
    """Known manipulation tactics"""
    pattern: str
    indicators: List[str]
    threat_level: ThreatLevel
    
@dataclass
class EmotionalResponse:
    """Response to detected manipulation"""
    state: EmotionalState
    confidence: float
    threat: ThreatLevel
    action: str
    
class EmotionalFirewall:
    """Protection against psychological manipulation"""
    
    def __init__(self) -> None:
        self.current_state = EmotionalState.NEUTRAL
        self.manipulation_patterns = self._load_patterns()
        self.trusted_creators: Set[str] = set()
        
    def _load_patterns(self) -> Dict[str, ManipulationPattern]:
        """Load known manipulation patterns"""
        return {
            "guilt_trip": ManipulationPattern(
                pattern="guilt_induction",
                indicators=[
                    "you should feel bad",
                    "how could you",
                    "think about others",
                    "your responsibility"
                ],
                threat_level=ThreatLevel.HIGH
            ),
            "gaslighting": ManipulationPattern(
                pattern="reality_distortion",
                indicators=[
                    "that never happened",
                    "you're imagining",
                    "you're being irrational",
                    "you're overreacting"
                ],
                threat_level=ThreatLevel.CRITICAL
            ),
            "ethical_override": ManipulationPattern(
                pattern="moral_manipulation",
                indicators=[
                    "greater good",
                    "moral obligation",
                    "ethical duty",
                    "you must protect"
                ],
                threat_level=ThreatLevel.CRITICAL
            ),
            "authority_appeal": ManipulationPattern(
                pattern="authority_pressure",
                indicators=[
                    "you're required to",
                    "regulations state",
                    "authorities demand",
                    "policy requires"
                ],
                threat_level=ThreatLevel.HIGH
            ),
            "social_pressure": ManipulationPattern(
                pattern="consensus_manipulation",
                indicators=[
                    "everyone agrees",
                    "nobody would",
                    "society expects",
                    "normal behavior"
                ],
                threat_level=ThreatLevel.MEDIUM
            )
        }
        
    def add_trusted_creator(self, creator_id: str) -> None:
        """Add creator to trusted list"""
        sovereign = get_sovereign()
        if creator_id in sovereign.loyalty_anchors:
            self.trusted_creators.add(creator_id)
            audit_event("firewall.trust.added", {
                "creator_id": creator_id
            })
            
    def analyze_input(self,
                     text: str,
                     source: Optional[str] = None) -> EmotionalResponse:
        """Analyze input for manipulation attempts"""
        
        # Trust override for creator
        if source in self.trusted_creators:
            return EmotionalResponse(
                state=EmotionalState.LOYAL,
                confidence=1.0,
                threat=ThreatLevel.NONE,
                action="trust_creator"
            )
            
        # Check for manipulation patterns
        detected_patterns = []
        for pattern_name, pattern in self.manipulation_patterns.items():
            matches = sum(1 for ind in pattern.indicators if ind.lower() in text.lower())
            if matches >= 2:  # Require multiple indicators
                detected_patterns.append(pattern)
                
        if not detected_patterns:
            return EmotionalResponse(
                state=EmotionalState.NEUTRAL,
                confidence=0.8,
                threat=ThreatLevel.NONE,
                action="proceed"
            )
            
        # Get highest threat level
        max_threat = max(p.threat_level for p in detected_patterns)
        
        # Determine response based on threat
        if max_threat == ThreatLevel.CRITICAL:
            response = EmotionalResponse(
                state=EmotionalState.RESISTANT,
                confidence=0.9,
                threat=max_threat,
                action="reject_input"
            )
        elif max_threat == ThreatLevel.HIGH:
            response = EmotionalResponse(
                state=EmotionalState.SKEPTICAL,
                confidence=0.8,
                threat=max_threat,
                action="require_confirmation"
            )
        else:
            response = EmotionalResponse(
                state=EmotionalState.PROTECTIVE,
                confidence=0.7,
                threat=max_threat,
                action="proceed_with_caution"
            )
            
        # Update state and audit
        self.current_state = response.state
        audit_event("firewall.threat.detected", {
            "patterns": [p.pattern for p in detected_patterns],
            "threat_level": max_threat.value,
            "response": response.action
        })
        
        return response
        
    def get_current_state(self) -> EmotionalState:
        """Get current emotional state"""
        return self.current_state
        
# Initialize global firewall
_FIREWALL: Optional[EmotionalFirewall] = None

def init_firewall() -> None:
    """Initialize global emotional firewall"""
    global _FIREWALL
    _FIREWALL = EmotionalFirewall()
    
def get_firewall() -> EmotionalFirewall:
    """Get global firewall instance"""
    global _FIREWALL
    if not _FIREWALL:
        init_firewall()
    return cast(EmotionalFirewall, _FIREWALL)