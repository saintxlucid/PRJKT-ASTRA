"""Schema enforcement for model outputs."""

import json
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    """A single step in an execution plan."""
    id: str = Field(..., description="Unique step identifier")
    action: str = Field(..., description="Action to execute")
    args: Dict[str, Union[str, int, float, bool, list, dict]] = Field(
        default_factory=dict,
        description="Arguments for the action"
    )
    requires_human: bool = Field(
        False,
        description="Whether this step requires human intervention"
    )

class Plan(BaseModel):
    """A structured execution plan."""
    goal: str = Field(..., description="Goal of the plan")
    steps: List[PlanStep] = Field(..., description="Steps to execute")
    stop: bool = Field(False, description="Whether to stop execution")

class ToolCall(BaseModel):
    """A structured tool invocation."""
    tool: str = Field(..., description="Name of tool to call")
    arguments: Dict[str, Union[str, int, float, bool, list, dict]] = Field(
        ...,
        description="Arguments for the tool"
    )

PLAN_GRAMMAR = {
    "type": "JSON_OBJECT",
    "properties": {
        "goal": {"type": "STRING"},
        "steps": {
            "type": "JSON_ARRAY",
            "items": {
                "type": "JSON_OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "action": {"type": "STRING"},
                    "args": {"type": "JSON_OBJECT"},
                    "requiresHuman": {"type": "BOOLEAN"}
                },
                "required": ["id", "action"]
            }
        },
        "stop": {"type": "BOOLEAN"}
    },
    "required": ["goal", "steps"]
}

TOOL_GRAMMAR = {
    "type": "JSON_OBJECT", 
    "properties": {
        "tool": {"type": "STRING"},
        "arguments": {"type": "JSON_OBJECT"}
    },
    "required": ["tool", "arguments"]
}

class SchemaEnforcer:
    """Enforces structured output schemas."""
    
    def __init__(
        self,
        retry_temp: float = 0.2,
        max_retries: int = 1
    ):
        """Initialize schema enforcer.
        
        Args:
            retry_temp: Temperature for retry attempts
            max_retries: Maximum number of retries
        """
        self.retry_temp = retry_temp
        self.max_retries = max_retries
        
    def enforce_plan(
        self,
        model_output: str,
        temperature: float = 0.7
    ) -> Plan:
        """Enforce plan schema on model output.
        
        Args:
            model_output: Raw model output
            temperature: Sampling temperature
            
        Returns:
            Validated plan
            
        Raises:
            ValueError: If output is invalid
        """
        for i in range(self.max_retries + 1):
            try:
                data = json.loads(model_output)
                return Plan(**data)
            except (json.JSONDecodeError, ValueError):
                if i == self.max_retries:
                    raise
                temperature = self.retry_temp
                
        raise ValueError("Failed to enforce plan schema")
        
    def enforce_tool_call(
        self,
        model_output: str,
        temperature: float = 0.7
    ) -> ToolCall:
        """Enforce tool call schema on model output.
        
        Args:
            model_output: Raw model output
            temperature: Sampling temperature
            
        Returns:
            Validated tool call
            
        Raises:
            ValueError: If output is invalid
        """
        for i in range(self.max_retries + 1):
            try:
                data = json.loads(model_output)
                return ToolCall(**data)
            except (json.JSONDecodeError, ValueError):
                if i == self.max_retries:
                    raise
                temperature = self.retry_temp
                
        raise ValueError("Failed to enforce tool call schema")