"""Schema enforcement for structured model outputs.

Provides grammar-constrained decoding schemas for:
- Planning (PlanSchema)
- Tool Usage (ToolSchema)
- Responses with Citations (ResponseSchema)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re
from pathlib import Path


class SchemaValidationError(Exception):
    """Raised when output fails schema validation."""
    pass


class SchemaType(str, Enum):
    """Types of supported schemas."""
    PLAN = "plan"
    TOOL = "tool"
    RESPONSE = "response"


@dataclass
class PlanStep:
    """Single step in a plan."""
    action: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    expected_result: Optional[str] = None


@dataclass
class Plan:
    """Complete planning schema."""
    goal: str
    steps: List[PlanStep]
    stop_condition: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """Create Plan from dictionary."""
        steps = [
            PlanStep(**step) if isinstance(step, dict) else step
            for step in data.get('steps', [])
        ]
        return cls(
            goal=data['goal'],
            steps=steps,
            stop_condition=data['stop_condition']
        )


@dataclass
class ToolCall:
    """Tool invocation schema."""
    name: str
    args: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class Response:
    """Response with citations schema."""
    answer: str
    citations: List[str]
    confidence: float
    sources: Optional[List[Dict[str, Any]]] = None


class SchemaEnforcer:
    """Enforces structured output schemas through grammar validation."""

    def __init__(self, grammar_dir: Optional[Path] = None):
        """Initialize schema enforcer.
        
        Args:
            grammar_dir: Directory containing GBNF grammar files.
                        If None, uses default grammars.
        """
        self.grammar_dir = grammar_dir or Path(__file__).parent / "grammars"
        self._load_grammars()

    def _load_grammars(self) -> None:
        """Load GBNF grammar files."""
        self.grammars = {}
        for schema_type in SchemaType:
            grammar_path = self.grammar_dir / f"{schema_type.value}.gbnf"
            if grammar_path.exists():
                self.grammars[schema_type] = grammar_path.read_text()
            else:
                # Use default grammar
                self.grammars[schema_type] = self._get_default_grammar(schema_type)

    def _get_default_grammar(self, schema_type: SchemaType) -> str:
        """Get default GBNF grammar for schema type."""
        if schema_type == SchemaType.PLAN:
            return '''
root ::= "{" ws "goal:" ws string "," ws "steps:" ws steps_array "," ws "stop_condition:" ws string ws "}"
steps_array ::= "[" ws (step (ws "," ws step)*)? ws "]"
step ::= "{" ws "action:" ws string 
         ("," ws "tool:" ws string)? 
         ("," ws "args:" ws json_object)?
         ("," ws "expected_result:" ws string)? ws "}"
string ::= "\\"" ([^"\\\\] | "\\\\" ["\\\\/bfnrt] | "\\\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])* "\\""
json_object ::= "{" ws (string ws ":" ws json_value (ws "," ws string ws ":" ws json_value)*)? ws "}"
json_value ::= string | number | json_object | json_array | "true" | "false" | "null"
json_array ::= "[" ws (json_value (ws "," ws json_value)*)? ws "]"
number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?
ws ::= [ \\t\\n\\r]*
'''
        elif schema_type == SchemaType.TOOL:
            return '''
root ::= "{" ws "name:" ws string "," ws "args:" ws json_object 
         ("," ws "description:" ws string)? ws "}"
string ::= "\\"" ([^"\\\\] | "\\\\" ["\\\\/bfnrt] | "\\\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])* "\\""
json_object ::= "{" ws (string ws ":" ws json_value (ws "," ws string ws ":" ws json_value)*)? ws "}"
json_value ::= string | number | json_object | json_array | "true" | "false" | "null"
json_array ::= "[" ws (json_value (ws "," ws json_value)*)? ws "]"
number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?
ws ::= [ \\t\\n\\r]*
'''
        elif schema_type == SchemaType.RESPONSE:
            return '''
root ::= "{" ws "answer:" ws string "," ws 
         "citations:" ws citation_array "," ws
         "confidence:" ws number
         ("," ws "sources:" ws source_array)? ws "}"
citation_array ::= "[" ws (string (ws "," ws string)*)? ws "]"
source_array ::= "[" ws (source (ws "," ws source)*)? ws "]"
source ::= "{" ws "type:" ws string "," ws "id:" ws string 
          ("," ws "metadata:" ws json_object)? ws "}"
string ::= "\\"" ([^"\\\\] | "\\\\" ["\\\\/bfnrt] | "\\\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])* "\\""
json_object ::= "{" ws (string ws ":" ws json_value (ws "," ws string ws ":" ws json_value)*)? ws "}"
json_value ::= string | number | json_object | json_array | "true" | "false" | "null"
json_array ::= "[" ws (json_value (ws "," ws json_value)*)? ws "]"
number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?
ws ::= [ \\t\\n\\r]*
'''
        raise ValueError(f"Unknown schema type: {schema_type}")

    def validate(self, text: str, schema_type: SchemaType) -> bool:
        """Validate text against schema grammar.
        
        Args:
            text: Text to validate
            schema_type: Type of schema to validate against
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            SchemaValidationError if validation fails
        """
        try:
            # First validate JSON structure
            data = json.loads(text)
            
            # Then validate against grammar
            grammar = self.grammars[schema_type]
            if not self._validate_grammar(text, grammar):
                raise SchemaValidationError(
                    f"Output does not match {schema_type.value} grammar"
                )
                
            # Finally validate schema-specific rules
            if schema_type == SchemaType.PLAN:
                self._validate_plan(data)
            elif schema_type == SchemaType.TOOL:
                self._validate_tool(data)
            elif schema_type == SchemaType.RESPONSE:
                self._validate_response(data)
                
            return True
            
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Invalid JSON: {str(e)}")
            
    def _validate_grammar(self, text: str, grammar: str) -> bool:
        """Validate text against GBNF grammar."""
        # TODO: Implement GBNF grammar validation
        # For now, just validate JSON structure
        return True
        
    def _validate_plan(self, data: Dict[str, Any]) -> None:
        """Validate plan-specific rules."""
        required = {'goal', 'steps', 'stop_condition'}
        if not all(k in data for k in required):
            raise SchemaValidationError(
                f"Missing required plan fields: {required - set(data.keys())}"
            )
            
        if not isinstance(data['steps'], list):
            raise SchemaValidationError("Steps must be an array")
            
        for i, step in enumerate(data['steps']):
            if not isinstance(step, dict):
                raise SchemaValidationError(f"Step {i} must be an object")
            if 'action' not in step:
                raise SchemaValidationError(f"Step {i} missing required field: action")
                
    def _validate_tool(self, data: Dict[str, Any]) -> None:
        """Validate tool-specific rules."""
        required = {'name', 'args'}
        if not all(k in data for k in required):
            raise SchemaValidationError(
                f"Missing required tool fields: {required - set(data.keys())}"
            )
            
        if not isinstance(data['args'], dict):
            raise SchemaValidationError("Args must be an object")
            
    def _validate_response(self, data: Dict[str, Any]) -> None:
        """Validate response-specific rules."""
        required = {'answer', 'citations', 'confidence'}
        if not all(k in data for k in required):
            raise SchemaValidationError(
                f"Missing required response fields: {required - set(data.keys())}"
            )
            
        if not isinstance(data['citations'], list):
            raise SchemaValidationError("Citations must be an array")
            
        if not isinstance(data['confidence'], (int, float)):
            raise SchemaValidationError("Confidence must be a number")
            
        if not 0 <= data['confidence'] <= 1:
            raise SchemaValidationError("Confidence must be between 0 and 1")
            
        if 'sources' in data:
            if not isinstance(data['sources'], list):
                raise SchemaValidationError("Sources must be an array")
            for i, source in enumerate(data['sources']):
                if not isinstance(source, dict):
                    raise SchemaValidationError(f"Source {i} must be an object")
                required = {'type', 'id'}
                if not all(k in source for k in required):
                    raise SchemaValidationError(
                        f"Source {i} missing required fields: {required - set(source.keys())}"
                    )