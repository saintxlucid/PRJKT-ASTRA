"""
ASTRA Grammar Management
Manages GBNF grammars for structured outputs.
Created: October 16, 2025
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

# Core plan grammar
PLAN_GRAMMAR = """
root            ::= plan
plan            ::= "{""goal"":string,""steps"":steps,""meta"":meta"}"
steps           ::= "[" ws* step_list? ws* "]"
step_list       ::= step (ws* "," ws* step)*
step            ::= "{" ws* step_fields ws* "}"
step_fields     ::= "\"id\":" int "," ws*
                   "\"tool\":" string "," ws*
                   "\"args\":" obj "," ws*
                   "\"expect\":" obj "," ws*
                   "\"reversible\":" bool "," ws*
                   "\"confirm\":" bool

meta            ::= "{" ws* "\"rationale\":string" ws* "}"

# JSON basics
string         ::= "\""" ([^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""
int            ::= "-"? ("0" | [1-9] [0-9]*)
bool           ::= "true" | "false"
null           ::= "null"
obj            ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
pair           ::= string ws* ":" ws* value
array          ::= "[" ws* (value (ws* "," ws* value)*)? ws* "]"
value          ::= string | int | obj | array | bool | null
ws             ::= [ \t\n\r]
"""

class GrammarManager:
    """Manages GBNF grammars for output structuring"""
    
    def __init__(self, grammar_dir: Path):
        """
        Initialize grammar manager
        Args:
            grammar_dir: Directory for grammar files
        """
        self.grammar_dir = grammar_dir
        self.grammar_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache of compiled grammars
        self._grammars: Dict[str, str] = {}
        
        logger.info(
            "Initialized grammar manager",
            grammar_dir=str(grammar_dir)
        )
    
    def get_plan_grammar(self) -> str:
        """Get the core plan grammar"""
        if "plan" not in self._grammars:
            self._grammars["plan"] = PLAN_GRAMMAR
            
            # Write to file for llama.cpp
            grammar_path = self.grammar_dir / "plan.gbnf"
            with open(grammar_path, 'w') as f:
                f.write(PLAN_GRAMMAR)
                
            logger.info(
                "Wrote plan grammar",
                path=str(grammar_path)
            )
        
        return self._grammars["plan"]
    
    def create_tool_grammar(
        self,
        tool_name: str,
        schema: Dict[str, Any]
    ) -> str:
        """
        Create grammar for tool arguments
        Args:
            tool_name: Name of the tool
            schema: JSON Schema for tool arguments
        Returns:
            GBNF grammar string
        """
        if tool_name in self._grammars:
            return self._grammars[tool_name]
        
        # Convert JSON Schema to GBNF
        grammar = self._schema_to_gbnf(schema)
        self._grammars[tool_name] = grammar
        
        # Write to file
        grammar_path = self.grammar_dir / f"{tool_name}.gbnf"
        with open(grammar_path, 'w') as f:
            f.write(grammar)
        
        logger.info(
            "Created tool grammar",
            tool=tool_name,
            path=str(grammar_path)
        )
        
        return grammar
    
    def _schema_to_gbnf(self, schema: Dict[str, Any]) -> str:
        """Convert JSON Schema to GBNF grammar"""
        # TODO: Implement full schema conversion
        # For now, return a basic object grammar
        return """
root   ::= object
object ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
pair   ::= string ws* ":" ws* value
array  ::= "[" ws* (value (ws* "," ws* value)*)? ws* "]"
value  ::= string | number | object | array | bool | null
string ::= "\\"" ([^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""
number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
bool   ::= "true" | "false"
null   ::= "null"
ws     ::= [ \\t\\n\\r]
"""

    def validate_grammar(self, grammar: str) -> bool:
        """
        Validate GBNF grammar syntax
        Args:
            grammar: GBNF grammar string
        Returns:
            True if valid
        """
        # TODO: Implement GBNF syntax validation
        return True