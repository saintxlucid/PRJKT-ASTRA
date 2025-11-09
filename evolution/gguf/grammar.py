"""Grammar-constrained decoding and validation."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
import json
import re

@dataclass
class GrammarRule:
    """JSON grammar rule."""
    type: str
    required: List[str] = None
    properties: Dict[str, "GrammarRule"] = None
    items: Optional["GrammarRule"] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GrammarRule":
        """Create from dictionary definition."""
        rule = cls(type=data["type"])
        
        if "required" in data:
            rule.required = data["required"]
            
        if "properties" in data:
            rule.properties = {
                k: GrammarRule.from_dict(v)
                for k, v in data["properties"].items()
            }
            
        if "items" in data:
            rule.items = GrammarRule.from_dict(data["items"])
            
        return rule
        
    def to_regex(self) -> str:
        """Convert rule to regex pattern."""
        if self.type == "STRING":
            return r'"[^"]*"'
        elif self.type == "NUMBER":
            return r'-?\d+(?:\.\d+)?'
        elif self.type == "BOOLEAN":
            return r'true|false'
        elif self.type == "JSON_ARRAY":
            item_pattern = self.items.to_regex() if self.items else r'[^,\]]*'
            return fr'\[\s*(?:{item_pattern})(?:\s*,\s*{item_pattern})*\s*\]'
        elif self.type == "JSON_OBJECT":
            prop_patterns = []
            if self.properties:
                for name, rule in self.properties.items():
                    prop_pattern = fr'"{name}"\s*:\s*{rule.to_regex()}'
                    if self.required and name in self.required:
                        prop_patterns.append(prop_pattern)
                    else:
                        prop_patterns.append(fr'(?:{prop_pattern})?')
            return fr'{{\s*{",".join(prop_patterns)}\s*}}'
        else:
            return r'.*'

@dataclass
class ValidationResult:
    """Grammar validation result."""
    valid: bool
    errors: List[str]
    fixed_output: Optional[str] = None

class GrammarValidator:
    """JSON grammar validator."""
    
    def __init__(
        self,
        plan_grammar: Dict[str, Any],
        tool_grammar: Dict[str, Any]
    ):
        """Initialize validator.
        
        Args:
            plan_grammar: Plan schema grammar
            tool_grammar: Tool call schema grammar
        """
        self.plan_rule = GrammarRule.from_dict(plan_grammar)
        self.tool_rule = GrammarRule.from_dict(tool_grammar)
        
    def validate_plan(
        self,
        output: str,
        fix: bool = True
    ) -> ValidationResult:
        """Validate plan output against grammar.
        
        Args:
            output: Model output to validate
            fix: Whether to attempt fixes
            
        Returns:
            Validation result
        """
        try:
            # Try parsing JSON
            data = json.loads(output)
            
            # Check required fields
            errors = []
            if "goal" not in data:
                errors.append("Missing required field: goal")
            if "steps" not in data:
                errors.append("Missing required field: steps")
            elif not isinstance(data["steps"], list):
                errors.append("Field 'steps' must be an array")
            else:
                # Validate each step
                for i, step in enumerate(data["steps"]):
                    if not isinstance(step, dict):
                        errors.append(f"Step {i} must be an object")
                        continue
                    if "id" not in step:
                        errors.append(f"Step {i} missing required field: id")
                    if "action" not in step:
                        errors.append(f"Step {i} missing required field: action")
                        
            if errors:
                if fix:
                    # Try basic fixes
                    fixed = self._fix_plan(data)
                    return ValidationResult(
                        valid=False,
                        errors=errors,
                        fixed_output=json.dumps(fixed)
                    )
                return ValidationResult(valid=False, errors=errors)
                
            return ValidationResult(valid=True, errors=[])
            
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
            
    def validate_tool_call(
        self,
        output: str,
        fix: bool = True
    ) -> ValidationResult:
        """Validate tool call output against grammar.
        
        Args:
            output: Model output to validate
            fix: Whether to attempt fixes
            
        Returns:
            Validation result
        """
        try:
            # Try parsing JSON
            data = json.loads(output)
            
            # Check required fields
            errors = []
            if "tool" not in data:
                errors.append("Missing required field: tool")
            if "arguments" not in data:
                errors.append("Missing required field: arguments")
            elif not isinstance(data["arguments"], dict):
                errors.append("Field 'arguments' must be an object")
                
            if errors:
                if fix:
                    # Try basic fixes
                    fixed = self._fix_tool_call(data)
                    return ValidationResult(
                        valid=False,
                        errors=errors,
                        fixed_output=json.dumps(fixed)
                    )
                return ValidationResult(valid=False, errors=errors)
                
            return ValidationResult(valid=True, errors=[])
            
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
            
    def _fix_plan(self, data: Dict) -> Dict:
        """Attempt to fix invalid plan.
        
        Args:
            data: Invalid plan data
            
        Returns:
            Fixed plan data
        """
        fixed = {}
        
        # Ensure required fields
        fixed["goal"] = data.get("goal", "")
        fixed["steps"] = []
        
        # Fix steps
        steps = data.get("steps", [])
        if isinstance(steps, list):
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    fixed_step = {
                        "id": step.get("id", str(i)),
                        "action": step.get("action", ""),
                        "args": step.get("args", {}),
                        "requiresHuman": bool(step.get("requiresHuman", False))
                    }
                    fixed["steps"].append(fixed_step)
                    
        return fixed
        
    def _fix_tool_call(self, data: Dict) -> Dict:
        """Attempt to fix invalid tool call.
        
        Args:
            data: Invalid tool call data
            
        Returns:
            Fixed tool call data
        """
        fixed = {
            "tool": data.get("tool", ""),
            "arguments": data.get("arguments", {})
        }
        
        # Ensure arguments is an object
        if not isinstance(fixed["arguments"], dict):
            fixed["arguments"] = {}
            
        return fixed
        
    def generate_regex(self) -> Dict[str, str]:
        """Generate regex patterns for validation.
        
        Returns:
            Dictionary of patterns
        """
        return {
            "plan": self.plan_rule.to_regex(),
            "tool": self.tool_rule.to_regex()
        }