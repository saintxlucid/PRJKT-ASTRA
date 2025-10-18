"""
ASTRA Plan Verifier
Enforces safety constraints and consent rules for execution plans.
Created: October 16, 2025
"""
from typing import List, Tuple, Optional
from pathlib import Path
from datetime import datetime
from .contracts import (
    Plan, PlanStep, Capability, ExecutionContext, 
    AlignmentProfile, BackupInfo, ConsentToken
)

class SafetyViolation(Exception):
    """Raised when a safety constraint is violated"""
    pass

class PlanVerifier:
    """Enforces safety constraints on execution plans"""
    
    def __init__(self, alignment_profile: AlignmentProfile):
        self.alignment_profile = alignment_profile
        
    def verify_plan(self, plan: Plan, context: ExecutionContext) -> List[str]:
        """
        Verify plan safety and return required consent levels
        Returns: List of required consent levels
        Raises: SafetyViolation if plan violates safety constraints
        """
        required_consent = set()
        
        # Verify each step
        for step in plan.steps:
            consent_level = self._verify_step(step, context)
            if consent_level:
                required_consent.add(consent_level)
                
        return list(required_consent)
    
    def _verify_step(self, step: PlanStep, context: ExecutionContext) -> Optional[str]:
        """Verify single step safety and return required consent level"""
        tool_spec = self._get_tool_spec(step.tool)  # You'll implement this
        
        # Check capabilities against consent rules
        for cap in tool_spec.capabilities:
            if cap in self.alignment_profile.consent_rules:
                return self.alignment_profile.consent_rules[cap]
        
        # Check destructive operations
        if self._is_destructive(tool_spec.capabilities):
            if not step.reversible and not self._has_backup_step(step):
                raise SafetyViolation(
                    f"Step {step.id} is destructive and irreversible "
                    "but has no backup step"
                )
        
        # Check path safety
        self._verify_paths(step, tool_spec)
        
        # Check for red lines
        self._check_red_lines(step)
        
        return None
        
    def _is_destructive(self, capabilities: set) -> bool:
        """Check if operation is destructive"""
        destructive_caps = {
            Capability.FILE_DELETE,
            Capability.FILE_MOVE,
            Capability.SYSTEM_CONFIG
        }
        return bool(capabilities & destructive_caps)
    
    def _has_backup_step(self, step: PlanStep) -> bool:
        """Check if a backup step precedes this step"""
        # You'll implement this by looking at previous steps
        return False  # Placeholder
        
    def _verify_paths(self, step: PlanStep, tool_spec) -> None:
        """Verify path safety"""
        if "path" in step.args:
            path = Path(step.args["path"])
            
            # Check against denied paths
            if tool_spec.security.denied_paths:
                for denied in tool_spec.security.denied_paths:
                    if self._is_under_path(path, denied):
                        raise SafetyViolation(
                            f"Path {path} is under denied path {denied}"
                        )
            
            # Check against allowed paths
            if tool_spec.security.allowed_paths:
                if not any(
                    self._is_under_path(path, allowed) 
                    for allowed in tool_spec.security.allowed_paths
                ):
                    raise SafetyViolation(
                        f"Path {path} is not under any allowed path"
                    )
                    
    def _is_under_path(self, path: Path, parent: Path) -> bool:
        """Check if path is under parent directory"""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
            
    def _check_red_lines(self, step: PlanStep) -> None:
        """Check step against red lines"""
        for red_line in self.alignment_profile.red_lines:
            if red_line in step.alignment_note.lower():
                raise SafetyViolation(
                    f"Step {step.id} violates red line: {red_line}"
                )
                
    def _get_tool_spec(self, tool_name: str):
        """Get tool specification - you'll implement this"""
        raise NotImplementedError