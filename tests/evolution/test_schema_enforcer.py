"""Tests for schema enforcement."""

import pytest
import json
from pathlib import Path
from evolution.schema.enforcer import (
    SchemaEnforcer,
    SchemaType,
    SchemaValidationError,
    Plan,
    PlanStep,
    ToolCall,
    Response
)

@pytest.fixture
def enforcer():
    """Create schema enforcer instance."""
    return SchemaEnforcer()

@pytest.fixture
def valid_plan():
    """Create valid plan JSON."""
    return {
        "goal": "Process user request",
        "steps": [
            {
                "action": "Search workspace",
                "tool": "semantic_search",
                "args": {"query": "find relevant files"}
            },
            {
                "action": "Read file contents",
                "tool": "read_file",
                "args": {"path": "/path/to/file"}
            }
        ],
        "stop_condition": "All files processed"
    }

@pytest.fixture
def valid_tool():
    """Create valid tool call JSON."""
    return {
        "name": "read_file",
        "args": {
            "path": "/path/to/file",
            "offset": 1,
            "limit": 100
        },
        "description": "Read file contents"
    }

@pytest.fixture
def valid_response():
    """Create valid response JSON."""
    return {
        "answer": "The file contains configuration data.",
        "citations": [
            "config.json:10-15",
            "README.md:25"
        ],
        "confidence": 0.95,
        "sources": [
            {
                "type": "file",
                "id": "config.json",
                "metadata": {"last_modified": "2025-10-22"}
            }
        ]
    }


class TestSchemaEnforcer:
    """Test schema enforcement functionality."""
    
    def test_plan_validation_success(self, enforcer, valid_plan):
        """Test successful plan validation."""
        plan_json = json.dumps(valid_plan)
        assert enforcer.validate(plan_json, SchemaType.PLAN)
        
        # Test dataclass creation
        plan = Plan.from_dict(valid_plan)
        assert plan.goal == valid_plan["goal"]
        assert len(plan.steps) == len(valid_plan["steps"])
        
    def test_plan_validation_failure(self, enforcer):
        """Test plan validation failures."""
        invalid_plans = [
            # Missing required field
            {
                "steps": [],
                "stop_condition": "test"
            },
            # Invalid steps format
            {
                "goal": "test",
                "steps": "not an array",
                "stop_condition": "test"
            },
            # Step missing action
            {
                "goal": "test",
                "steps": [{"tool": "test"}],
                "stop_condition": "test"
            }
        ]
        
        for invalid_plan in invalid_plans:
            with pytest.raises(SchemaValidationError):
                enforcer.validate(json.dumps(invalid_plan), SchemaType.PLAN)
                
    def test_tool_validation_success(self, enforcer, valid_tool):
        """Test successful tool validation."""
        tool_json = json.dumps(valid_tool)
        assert enforcer.validate(tool_json, SchemaType.TOOL)
        
        # Test dataclass creation
        tool = ToolCall(**valid_tool)
        assert tool.name == valid_tool["name"]
        assert tool.args == valid_tool["args"]
        
    def test_tool_validation_failure(self, enforcer):
        """Test tool validation failures."""
        invalid_tools = [
            # Missing required field
            {
                "args": {}
            },
            # Invalid args type
            {
                "name": "test",
                "args": "not an object"
            }
        ]
        
        for invalid_tool in invalid_tools:
            with pytest.raises(SchemaValidationError):
                enforcer.validate(json.dumps(invalid_tool), SchemaType.TOOL)
                
    def test_response_validation_success(self, enforcer, valid_response):
        """Test successful response validation."""
        response_json = json.dumps(valid_response)
        assert enforcer.validate(response_json, SchemaType.RESPONSE)
        
        # Test dataclass creation
        response = Response(**valid_response)
        assert response.answer == valid_response["answer"]
        assert response.citations == valid_response["citations"]
        
    def test_response_validation_failure(self, enforcer):
        """Test response validation failures."""
        invalid_responses = [
            # Missing required field
            {
                "answer": "test",
                "citations": []
            },
            # Invalid citations format
            {
                "answer": "test",
                "citations": "not an array",
                "confidence": 0.9
            },
            # Invalid confidence
            {
                "answer": "test",
                "citations": [],
                "confidence": 1.5
            },
            # Invalid source format
            {
                "answer": "test",
                "citations": [],
                "confidence": 0.9,
                "sources": [{"type": "file"}]  # Missing id
            }
        ]
        
        for invalid_response in invalid_responses:
            with pytest.raises(SchemaValidationError):
                enforcer.validate(json.dumps(invalid_response), SchemaType.RESPONSE)
                
    def test_grammar_loading(self, tmp_path):
        """Test grammar file loading."""
        grammar_dir = tmp_path / "grammars"
        grammar_dir.mkdir()
        
        # Create custom grammar file
        plan_grammar = grammar_dir / "plan.gbnf"
        plan_grammar.write_text("root ::= plan")
        
        enforcer = SchemaEnforcer(grammar_dir)
        assert SchemaType.PLAN in enforcer.grammars
        assert enforcer.grammars[SchemaType.PLAN] == "root ::= plan"
        
        # Test default grammar fallback
        assert SchemaType.TOOL in enforcer.grammars
        assert enforcer.grammars[SchemaType.TOOL].strip() != ""