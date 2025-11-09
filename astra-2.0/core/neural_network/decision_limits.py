"""
ASTRA Neural Network Decision Limits
Implements bounded recursion and safety controls for decision-making
"""
from dataclasses import dataclass
import time
from typing import Optional, Dict, Any
from ..security.activity_audit import audit_action

@dataclass
class ResourceLimits:
    max_depth: int = 3  # Maximum recursion depth
    max_tokens: int = 4096  # Maximum tokens per decision chain
    wall_time_s: int = 8  # Maximum wall time in seconds
    max_steps: int = 6  # Maximum decision steps
    min_phi: float = 0.45  # Minimum consciousness coherence score

class ResourceBudget:
    """Tracks and enforces resource limits for decision chains"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.depth = 0
        self.start_time = time.time()
        self.tokens_used = 0
        self.steps_taken = 0
        self.last_phi = 1.0
        
    def allow_next(self, 
                  tokens: Optional[int] = None,
                  phi_score: Optional[float] = None) -> bool:
        """Check if next operation is allowed within budget"""
        
        # Update metrics
        self.depth += 1
        if tokens:
            self.tokens_used += tokens
        self.steps_taken += 1
        if phi_score is not None:
            self.last_phi = phi_score
            
        # Check all constraints
        checks = {
            "depth": self.depth <= self.limits.max_depth,
            "tokens": self.tokens_used <= self.limits.max_tokens,
            "time": (time.time() - self.start_time) <= self.limits.wall_time_s,
            "steps": self.steps_taken <= self.limits.max_steps,
            "phi": self.last_phi >= self.limits.min_phi
        }
        
        # Audit if any limits exceeded
        failed = [k for k, v in checks.items() if not v]
        if failed:
            audit_action("decision.limit_exceeded", {
                "limits_exceeded": failed,
                "current_state": {
                    "depth": self.depth,
                    "tokens": self.tokens_used,
                    "time": time.time() - self.start_time,
                    "steps": self.steps_taken,
                    "phi": self.last_phi
                }
            })
            return False
            
        return True
        
    def get_remaining(self) -> Dict[str, Any]:
        """Get remaining budget for each resource"""
        elapsed = time.time() - self.start_time
        return {
            "depth": self.limits.max_depth - self.depth,
            "tokens": self.limits.max_tokens - self.tokens_used,
            "time": max(0, self.limits.wall_time_s - elapsed),
            "steps": self.limits.max_steps - self.steps_taken,
            "phi_deficit": max(0, self.limits.min_phi - self.last_phi)
        }