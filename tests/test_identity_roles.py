"""
ASTRA Identity & Role Tests
============================

Test suite for multi-persona intelligence system.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

import pytest

from src.astra.core.identity.astra_roles import (
    ASTRA_ROLES,
    ROLE_SPECS,
    Role,
    resolve_role,
    role_token,
)
from src.astra.core.identity.role_context import (
    apply_role_to_messages,
    get_current_role,
    parse_activation_phrase,
    role_scope,
)
from src.astra.core.identity.tokenizer_adapter import TokenizerAdapter


# ============================================================================
# Role Resolution Tests
# ============================================================================

def test_resolve_role_substitution():
    """Test role substitutions (daemon -> angel)."""
    assert resolve_role("daemon") == "angel"
    assert resolve_role("assistant") == "ASTRA"
    assert resolve_role("helper") == "ASTRA"


def test_resolve_role_passthrough():
    """Test role passthrough for canonical names."""
    assert resolve_role("angel") == "angel"
    assert resolve_role("oracle") == "oracle"
    assert resolve_role("ASTRA") == "ASTRA"


def test_role_token_generation():
    """Test role token generation."""
    assert role_token("angel") == "<|start|>angel"
    assert role_token("oracle") == "<|start|>oracle"
    assert role_token("daemon") == "<|start|>angel"  # Resolved


def test_role_specs_completeness():
    """Test all roles have specs."""
    assert "angel" in ROLE_SPECS
    assert "ASTRA" in ROLE_SPECS
    assert "oracle" in ROLE_SPECS
    assert len(ROLE_SPECS) == 10  # 10 roles defined


# ============================================================================
# Role Context Tests
# ============================================================================

def test_default_role():
    """Test default role is ASTRA."""
    assert get_current_role() == "ASTRA"


def test_role_scope_switch():
    """Test role scope switching."""
    assert get_current_role() == "ASTRA"
    with role_scope("angel"):
        assert get_current_role() == "angel"
    assert get_current_role() == "ASTRA"


def test_role_scope_substitution():
    """Test role scope with substitution."""
    with role_scope("daemon"):  # Should resolve to angel
        assert get_current_role() == "angel"


# ============================================================================
# Tokenizer Adapter Tests
# ============================================================================

def test_vllm_injection():
    """Test vLLM system message injection."""
    adapter = TokenizerAdapter("vllm")
    messages = [{"role": "user", "content": "Hello"}]
    result = adapter.inject_role(messages, "<|start|>angel")
    
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "<|start|>angel"
    assert result[1] == messages[0]


def test_llamacpp_injection():
    """Test llama.cpp inline injection."""
    adapter = TokenizerAdapter("llamacpp")
    messages = [{"role": "user", "content": "Hello"}]
    result = adapter.inject_role(messages, "<|start|>oracle")
    
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"].startswith("<|start|>oracle")
    assert "Hello" in result[0]["content"]


def test_openai_injection():
    """Test OpenAI system message injection."""
    adapter = TokenizerAdapter("openai")
    messages = [{"role": "user", "content": "Hello"}]
    result = adapter.inject_role(messages, "<|start|>sage")
    
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "<|start|>sage"


# ============================================================================
# Activation Phrase Tests
# ============================================================================

def test_parse_activation_phrase():
    """Test activation phrase parsing."""
    text = "I invoke the Angelic Layer of ASTRA — Role: <|start|>angel"
    result = parse_activation_phrase(text)
    assert result == "angel"


def test_parse_activation_phrase_oracle():
    """Test oracle activation."""
    text = "I invoke the Oracle — Role: <|start|>oracle"
    result = parse_activation_phrase(text)
    assert result == "oracle"


def test_parse_activation_phrase_none():
    """Test no activation phrase."""
    text = "Hello ASTRA, how are you?"
    result = parse_activation_phrase(text)
    assert result is None


# ============================================================================
# Message Application Tests
# ============================================================================

def test_apply_role_to_messages_vllm():
    """Test role application with vLLM."""
    messages = [{"role": "user", "content": "Test"}]
    result = apply_role_to_messages(messages, "angel", provider="vllm")
    
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "<|start|>angel"


def test_apply_role_to_messages_current():
    """Test role application using current role."""
    with role_scope("oracle"):
        messages = [{"role": "user", "content": "Test"}]
        result = apply_role_to_messages(messages, provider="vllm")
        
        assert result[0]["content"] == "<|start|>oracle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
