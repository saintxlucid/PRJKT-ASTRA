"""
ASTRA LLM Infrastructure Tests
Validates metadata, server config, chat template, and grammar handling.
Created: October 16, 2025
"""
import pytest
from pathlib import Path
import json
from astra.llm.metadata import (
    MetadataHandler, AstraMetadata, AstraPersona,
    PersonalityTraits, SamplingParams
)
from astra.llm.server import LLMServerConfig
from astra.llm.chat import ChatManager, ASTRA_TOKENS
from astra.llm.grammar import GrammarManager

@pytest.fixture
def test_model_path():
    """Test model path"""
    return Path("/models/test-model.gguf")

@pytest.fixture
def metadata_handler(test_model_path):
    """Test metadata handler"""
    return MetadataHandler(test_model_path)

@pytest.fixture
def chat_manager():
    """Test chat manager"""
    return ChatManager()

@pytest.fixture
def grammar_manager(tmp_path):
    """Test grammar manager with temp dir"""
    return GrammarManager(tmp_path / "grammars")

def test_metadata_loading(metadata_handler):
    """Test metadata loading and validation"""
    metadata = metadata_handler.metadata
    
    assert isinstance(metadata, AstraMetadata)
    assert metadata.identity_version == "2.5"
    assert metadata.persona == AstraPersona.GUARDIAN_ENGINEER
    
    # Validate traits
    assert 0 <= metadata.traits.warmth <= 1.0
    assert 0 <= metadata.traits.precision <= 1.0
    assert 0 <= metadata.traits.candor <= 1.0
    assert 0 <= metadata.traits.prudence <= 1.0
    
    # Check sampling params
    sampling = metadata.sampling
    assert 0 <= sampling.temperature <= 2.0
    assert 0 <= sampling.top_p <= 1.0
    assert sampling.repeat_penalty >= 1.0

def test_server_config(test_model_path):
    """Test server configuration"""
    config = LLMServerConfig(
        model_path=test_model_path,
        grammar_path=Path("/grammars/plan.gbnf"),
        host="127.0.0.1",
        port=8001
    )
    
    args = config.get_server_args()
    
    # Check essential args
    assert "--model" in args
    assert "--grammar-file" in args
    assert "--host" in args
    assert "--port" in args
    
    # Check sampling params
    assert "--temp" in args
    assert "--top-p" in args
    assert "--repeat-penalty" in args

def test_chat_template(chat_manager):
    """Test chat template formatting"""
    messages = [
        {"role": "system", "content": "You are ASTRA."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "tool", "content": "Tool result"}
    ]
    
    # Test normal mode
    output = chat_manager.format_messages(messages)
    assert "<|system|>" in output
    assert "<|user|>" in output
    assert "<|assistant|>" in output
    assert "<|astra.tool_result|>" in output
    assert "<|astra.end|>" in output
    
    # Test plan mode
    plan_output = chat_manager.format_messages(messages, plan_mode=True)
    assert "<|astra.plan|>" in plan_output

def test_grammar_generation(grammar_manager):
    """Test grammar file generation"""
    # Test plan grammar
    plan_grammar = grammar_manager.get_plan_grammar()
    assert "goal" in plan_grammar
    assert "steps" in plan_grammar
    assert "meta" in plan_grammar
    
    # Test tool grammar
    tool_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "recursive": {"type": "boolean"}
        }
    }
    
    tool_grammar = grammar_manager.create_tool_grammar(
        "test_tool",
        tool_schema
    )
    
    assert "object" in tool_grammar
    assert "string" in tool_grammar
    assert "bool" in tool_grammar

def test_special_tokens():
    """Test special token handling"""
    # Verify all required tokens exist
    required_tokens = {
        "plan", "steps", "tool_call", "tool_result",
        "consent", "backup", "verify", "rationale"
    }
    
    token_text = " ".join(ASTRA_TOKENS)
    for token in required_tokens:
        assert token in token_text.lower()

def test_chat_message_validation(chat_manager):
    """Test message validation"""
    # Valid message
    valid = {
        "role": "user",
        "content": "Hello"
    }
    assert chat_manager.validate_message(valid)
    
    # Invalid role
    invalid_role = {
        "role": "invalid",
        "content": "Hello"
    }
    assert not chat_manager.validate_message(invalid_role)
    
    # Missing content
    missing_content = {
        "role": "user"
    }
    assert not chat_manager.validate_message(missing_content)

def test_plan_extraction(chat_manager):
    """Test plan extraction from response"""
    response = """<|assistant|> Let me help with that.
<|astra.plan|>{
    "goal": "Test plan",
    "steps": []
}<|astra.end|>
"""
    plan = chat_manager.extract_plan(response)
    assert plan is not None
    assert "goal" in plan
    
    # Test without plan
    no_plan = "<|assistant|> Just a normal response."
    assert chat_manager.extract_plan(no_plan) is None

def test_rationale_extraction(chat_manager):
    """Test rationale extraction"""
    response = """<|assistant|> <|astra.rationale|>
Safety first: Creating backup before deletion.
<|astra.end|>
"""
    rationale = chat_manager.extract_rationale(response)
    assert rationale is not None
    assert "Safety first" in rationale