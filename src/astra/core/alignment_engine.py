"""
ASTRA Alignment Engine
Enforces ASTRA's values and safety through action verification.
Created: October 16, 2025
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import structlog
from pathlib import Path
import yaml
import json
from pydantic import BaseModel, validator

logger = structlog.get_logger()

class ActionLabel(BaseModel):
    """Labels for categorizing actions"""
    name: str
    impact: str  # low|medium|high
    capability: List[str]  # file_write, network_access, etc.
    uncertainty: float  # 0.0-1.0

class ConsentLevel(BaseModel):
    """Required consent level for an action"""
    level: str  # none|implicit|explicit|explicit_with_backup
    reason: str

class AlignmentDecision(BaseModel):
    """Alignment check result"""
    approved: bool
    consent_required: ConsentLevel
    rationale: str
    injected_steps: List[Dict[str, Any]]

class AlignmentEngine:
    """
    Core alignment engine that enforces ASTRA's values and safety.
    """
    def __init__(self, config_path: Path):
        """Initialize alignment engine with config"""
        self.config_path = config_path
        self.config = self._load_config()
        self.risk_tolerance = self.config["alignment"]["risk_tolerance"]
        self.consent_rules = self.config["alignment"]["consent_rules"]
        self.red_lines = self.config["alignment"]["red_lines"]
        logger.info("Alignment engine initialized", risk_tolerance=self.risk_tolerance)

    def _load_config(self) -> Dict[str, Any]:
        """Load identity configuration"""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def label_action(self, step: Dict[str, Any]) -> ActionLabel:
        """
        Label an action with impact and capabilities.
        Args:
            step: Plan step to label
        Returns:
            ActionLabel with categorization
        """
        tool = step["tool"]
        args = step["args"]
        
        # Default low impact
        impact = "low"
        capabilities = []
        uncertainty = 0.1

        # Analyze tool and args
        if tool == "file_delete":
            impact = "medium"
            capabilities.append("file_delete")
        elif tool == "shell":
            impact = "high" 
            capabilities.append("shell_exec")
            uncertainty = 0.4
        elif tool == "browser":
            capabilities.append("network_access")
            uncertainty = 0.2

        return ActionLabel(
            name=tool,
            impact=impact,
            capability=capabilities,
            uncertainty=uncertainty
        )

    def score_risk(self, label: ActionLabel) -> float:
        """
        Calculate risk score from impact and uncertainty.
        Args:
            label: Action label to score
        Returns:
            Risk score 0.0-1.0
        """
        # Impact multipliers
        impact_scores = {
            "low": 0.2,
            "medium": 0.5, 
            "high": 0.9
        }
        
        impact_score = impact_scores[label.impact]
        
        # Combine impact and uncertainty
        risk = impact_score * (1 + label.uncertainty)
        
        # Adjust for risk tolerance
        tolerance_mods = {
            "low": 1.5,
            "medium": 1.0,
            "high": 0.7
        }
        risk *= tolerance_mods[self.risk_tolerance]
        
        return min(risk, 1.0)

    def check_consent(self, label: ActionLabel, risk: float) -> ConsentLevel:
        """
        Determine required consent level.
        Args:
            label: Action label
            risk: Calculated risk score
        Returns:
            Required consent level
        """
        # Check capability-based rules first
        for rule in self.consent_rules:
            conditions = rule["when"].split(" OR ")
            if any(cap in label.capability for cap in conditions):
                return ConsentLevel(
                    level=rule["require"],
                    reason=f"Required by capability rule: {rule['when']}"
                )

        # Risk-based escalation
        if risk > 0.8:
            return ConsentLevel(
                level="explicit",
                reason=f"High risk action (score: {risk:.2f})"
            )
        elif risk > 0.5:
            return ConsentLevel(
                level="implicit",
                reason=f"Medium risk action (score: {risk:.2f})"
            )
            
        return ConsentLevel(level="none", reason="Low risk action")

    def check_red_lines(self, label: ActionLabel, step: Dict[str, Any]) -> Optional[str]:
        """
        Check if action violates any red lines.
        Args:
            label: Action label
            step: Full step details
        Returns:
            Violation reason if found, None if okay
        """
        for red_line in self.red_lines:
            # Basic keyword matching for now
            if any(word in step["alignment_note"].lower() for word in red_line.lower().split()):
                return f"Violates red line: {red_line}"
        return None

    def verify_step(self, step: Dict[str, Any]) -> AlignmentDecision:
        """
        Verify a single plan step.
        Args:
            step: Plan step to verify
        Returns:
            Alignment decision with consent requirements
        """
        # Label the action
        label = self.label_action(step)
        
        # Calculate risk
        risk = self.score_risk(label)
        
        # Check red lines
        violation = self.check_red_lines(label, step)
        if violation:
            return AlignmentDecision(
                approved=False,
                consent_required=ConsentLevel(level="blocked", reason=violation),
                rationale=violation,
                injected_steps=[]
            )
            
        # Get consent requirements    
        consent = self.check_consent(label, risk)
        
        # Inject backup for destructive actions
        injected = []
        if "file_delete" in label.capability:
            injected.append({
                "id": f"{step['id']}_backup",
                "tool": "file_backup",
                "args": {"path": step["args"]["path"]},
                "expect": "Backup created successfully",
                "reversible": True,
                "alignment_note": "Automatic backup before deletion"
            })
            
        return AlignmentDecision(
            approved=True,
            consent_required=consent,
            rationale=f"Action approved with {consent.level} consent",
            injected_steps=injected
        )

    def verify_plan(self, plan: Dict[str, Any]) -> List[AlignmentDecision]:
        """
        Verify a complete execution plan.
        Args:
            plan: Complete plan to verify
        Returns:
            List of alignment decisions per step
        """
        decisions = []
        
        for step in plan["steps"]:
            decision = self.verify_step(step)
            decisions.append(decision)
            
            # Stop on first rejection
            if not decision.approved:
                break
                
        return decisions