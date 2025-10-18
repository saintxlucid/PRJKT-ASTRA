"""
ASTRA JSON Schema to GBNF Converter
Converts JSON Schema to GBNF grammar for strict output parsing.
Created: October 16, 2025
"""
from typing import Dict, Any, List, Set
import json
import re
from pathlib import Path
import structlog

logger = structlog.get_logger()

class GBNFConverter:
    """Converts JSON Schema to GBNF grammar"""
    
    def __init__(self):
        """Initialize converter"""
        self.rules: Dict[str, str] = {}
        self.used_names: Set[str] = set()
    
    def convert_schema(self, schema: Dict[str, Any]) -> str:
        """
        Convert JSON Schema to GBNF grammar
        Args:
            schema: JSON Schema dict
        Returns:
            GBNF grammar string
        """
        self.rules.clear()
        self.used_names.clear()
        
        # Add basic JSON rules
        self._add_json_basics()
        
        # Convert schema starting at root
        root_rule = self._convert_type(schema, "root")
        self.rules["root"] = f"root ::= {root_rule}"
        
        # Build final grammar
        return self._build_grammar()
    
    def _add_json_basics(self):
        """Add basic JSON parsing rules"""
        self.rules.update({
            "string": 'string ::= "\\"" ([^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""',
            "number": 'number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?',
            "integer": 'integer ::= "-"? ("0" | [1-9] [0-9]*)',
            "boolean": 'boolean ::= "true" | "false"',
            "null": 'null ::= "null"',
            "ws": 'ws ::= [ \\t\\n\\r]'
        })
    
    def _convert_type(
        self,
        schema: Dict[str, Any],
        name_hint: str
    ) -> str:
        """
        Convert schema type to GBNF rule
        Args:
            schema: Schema for this type
            name_hint: Hint for rule naming
        Returns:
            Reference to rule
        """
        schema_type = schema.get("type")
        
        if schema_type == "object":
            return self._convert_object(schema, name_hint)
        elif schema_type == "array":
            return self._convert_array(schema, name_hint)
        elif schema_type == "string":
            if "enum" in schema:
                return self._convert_enum(schema, name_hint)
            return "string"
        elif schema_type == "integer":
            return "integer"
        elif schema_type == "number":
            return "number"
        elif schema_type == "boolean":
            return "boolean"
        elif schema_type == "null":
            return "null"
        else:
            # Handle anyOf, oneOf, allOf
            if "anyOf" in schema:
                return self._convert_any_of(schema["anyOf"], name_hint)
            elif "oneOf" in schema:
                return self._convert_one_of(schema["oneOf"], name_hint)
            
            return "value"  # Generic JSON value
    
    def _convert_object(
        self,
        schema: Dict[str, Any],
        name_hint: str
    ) -> str:
        """Convert object schema to GBNF"""
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        
        # Create rules for each property
        prop_rules = []
        for prop_name, prop_schema in properties.items():
            prop_type = self._convert_type(
                prop_schema,
                f"{name_hint}_{prop_name}"
            )
            
            # Required properties must appear
            if prop_name in required:
                prop_rules.append(
                    f'"\\"" "{prop_name}" "\\":" ws* {prop_type}'
                )
            else:
                # Optional properties
                rule_name = self._unique_name(
                    f"{name_hint}_{prop_name}_opt"
                )
                self.rules[rule_name] = (
                    f'{rule_name} ::= ("\\"" "{prop_name}" "\\":" '
                    f'ws* {prop_type})?'
                )
                prop_rules.append(rule_name)
        
        # Build object rule
        rule_name = self._unique_name(f"{name_hint}_obj")
        props = " ws* \",\" ws* ".join(prop_rules)
        self.rules[rule_name] = (
            f'{rule_name} ::= "{{" ws* {props} ws* "}}"'
        )
        
        return rule_name
    
    def _convert_array(
        self,
        schema: Dict[str, Any],
        name_hint: str
    ) -> str:
        """Convert array schema to GBNF"""
        items = schema.get("items", {})
        item_type = self._convert_type(items, f"{name_hint}_item")
        
        rule_name = self._unique_name(f"{name_hint}_array")
        self.rules[rule_name] = (
            f'{rule_name} ::= "[" ws* ({item_type} '
            f'(ws* "," ws* {item_type})*)? ws* "]"'
        )
        
        return rule_name
    
    def _convert_enum(
        self,
        schema: Dict[str, Any],
        name_hint: str
    ) -> str:
        """Convert enum schema to GBNF"""
        values = schema["enum"]
        rule_name = self._unique_name(f"{name_hint}_enum")
        
        # Build enum alternatives
        alts = " | ".join(
            f'"\\"" "{val}" "\\""'
            for val in values
        )
        
        self.rules[rule_name] = f"{rule_name} ::= {alts}"
        return rule_name
    
    def _convert_any_of(
        self,
        schemas: List[Dict[str, Any]],
        name_hint: str
    ) -> str:
        """Convert anyOf schema to GBNF"""
        rule_name = self._unique_name(f"{name_hint}_any")
        
        # Convert each option
        options = [
            self._convert_type(s, f"{name_hint}_{i}")
            for i, s in enumerate(schemas)
        ]
        
        self.rules[rule_name] = (
            f"{rule_name} ::= " + " | ".join(options)
        )
        return rule_name
    
    def _convert_one_of(
        self,
        schemas: List[Dict[str, Any]],
        name_hint: str
    ) -> str:
        """Convert oneOf schema to GBNF (same as anyOf for now)"""
        return self._convert_any_of(schemas, name_hint)
    
    def _unique_name(self, base: str) -> str:
        """Generate unique rule name"""
        name = base
        i = 1
        while name in self.used_names:
            name = f"{base}_{i}"
            i += 1
        
        self.used_names.add(name)
        return name
    
    def _build_grammar(self) -> str:
        """Build complete grammar string"""
        # Order rules (root first, then alphabetically)
        ordered = ["root"]
        ordered.extend(sorted(
            name for name in self.rules
            if name != "root"
        ))
        
        # Build grammar
        return "\n\n".join(
            f"{self.rules[name]}"
            for name in ordered
        )

def schema_to_gbnf(schema: Dict[str, Any]) -> str:
    """
    Convert JSON Schema to GBNF grammar
    Args:
        schema: JSON Schema dict
    Returns:
        GBNF grammar string
    """
    converter = GBNFConverter()
    return converter.convert_schema(schema)

def save_grammar(
    grammar: str,
    output_path: Path,
    validate: bool = True
) -> None:
    """
    Save GBNF grammar to file
    Args:
        grammar: GBNF grammar string
        output_path: Output file path
        validate: Whether to validate grammar
    """
    if validate:
        # Basic validation
        if not grammar.strip():
            raise ValueError("Empty grammar")
        
        if "root ::=" not in grammar:
            raise ValueError("Missing root rule")
    
    with open(output_path, 'w') as f:
        f.write(grammar)
    
    logger.info(
        "Saved GBNF grammar",
        path=str(output_path)
    )