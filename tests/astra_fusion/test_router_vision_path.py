"""
ASTRA Fusion Test Suite - Router Vision Path Validation
========================================================
Sacred Code: 333

Tests that vision content is correctly routed to vision tools,
not passed to the LLM.
"""

import sys
from pathlib import Path
import pytest

# Add fusion pipeline to path
fusion_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/ops/fusion_pipeline/scripts")
sys.path.insert(0, str(fusion_path))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "runtime_hook",
        fusion_path / "05_runtime_hook_example.py"
    )
    runtime_hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime_hook)
    AstraRouter = runtime_hook.AstraRouter
except Exception as e:
    pytest.skip(f"AstraRouter not available: {e}", allow_module_level=True)


class MockLLM:
    """Mock LLM that tracks if it was called."""
    
    def __init__(self):
        self.called = False
        self.last_prompt = None
    
    def generate(self, prompt, max_tokens=512):
        self.called = True
        self.last_prompt = prompt
        return "[MOCK LLM RESPONSE]"


class MockToolBus:
    """Mock Tool Bus that tracks tool executions."""
    
    def __init__(self):
        self.executed_tools = []
        self.last_payload = None
    
    def execute(self, tool, payload):
        self.executed_tools.append(tool)
        self.last_payload = payload
        
        # Return appropriate mock response based on tool
        if "vision" in tool:
            return "[MOCK VISION TOOL: Described image content]"
        elif "audio" in tool:
            return "[MOCK AUDIO TOOL: Transcribed audio]"
        elif "code" in tool:
            return "[MOCK CODE TOOL: Analyzed code]"
        else:
            return "[MOCK TOOL RESPONSE]"


class MockMemory:
    """Mock Memory service."""
    
    def retrieve_relevant(self, query, top_k=6):
        return "<memory>Sacred Code 333 context</memory>"


class MockConsent:
    """Mock Consent manager."""
    
    def __init__(self, allow_all=True):
        self.allow_all = allow_all
        self.checks = []
    
    def allowed(self, action):
        self.checks.append(action)
        return self.allow_all


class TestRouterVisionPath:
    """Test suite for vision routing behavior."""
    
    def test_vision_prompt_routes_to_vision_tool(self):
        """Test that prompts with vision tags route to vision tool, not LLM."""
        # Create mocks
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        # Create router
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        # Prompt with vision content
        vision_prompt = """
        <|mode_start|>COGNITION<|mode_end|>
        <|vision_start|>
        Image: [embedding:1280-dim hash=abc123]
        Description: Pharaonic temple with black & gold pillars
        <|vision_end|>
        <|task_start|>
        User: Describe this image.
        <|task_end|>
        """
        
        # Execute
        response = router.handle(vision_prompt)
        
        # Assert: Vision tool was called, not LLM
        assert "vision" in mock_tool_bus.executed_tools[0], \
               "Vision tool not executed"
        assert not mock_llm.called, \
               "LLM was called when it should have been bypassed for vision content"
        assert "MOCK VISION TOOL" in response, \
               "Vision tool response not returned"
    
    def test_vision_payload_contains_vision_block(self):
        """Test that vision tool receives the vision content in payload."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        vision_prompt = """
        <|vision_start|>
        Pharaonic temple scene
        <|vision_end|>
        """
        
        router.handle(vision_prompt)
        
        # Check payload
        assert mock_tool_bus.last_payload is not None, "No payload sent to tool"
        assert "vision_block" in mock_tool_bus.last_payload, \
               "vision_block not in payload"
        assert "Pharaonic temple" in mock_tool_bus.last_payload["vision_block"], \
               "Vision content not extracted correctly"
    
    def test_pure_text_routes_to_llm(self):
        """Test that prompts without special tokens route to LLM."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        text_prompt = "What is the meaning of life?"
        
        response = router.handle(text_prompt)
        
        # Assert: LLM was called, tools were not
        assert mock_llm.called, "LLM not called for pure text prompt"
        assert len(mock_tool_bus.executed_tools) == 0, \
               "Tools executed when they shouldn't have been"
    
    def test_text_with_memory_augmentation(self):
        """Test that pure text prompts get memory augmentation."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        text_prompt = "Tell me about ASTRA."
        
        router.handle(text_prompt)
        
        # Check that LLM received memory-augmented prompt
        assert mock_llm.last_prompt is not None, "No prompt sent to LLM"
        assert "Sacred Code 333" in mock_llm.last_prompt, \
               "Memory context not added to prompt"
    
    def test_audio_routes_to_audio_tool(self):
        """Test that audio content routes to audio tool."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        audio_prompt = """
        <|audio_start|>
        [Audio waveform data]
        <|audio_end|>
        Transcribe this audio.
        """
        
        response = router.handle(audio_prompt)
        
        # Assert: Audio tool called, not LLM
        assert "audio" in mock_tool_bus.executed_tools[0], \
               "Audio tool not executed"
        assert not mock_llm.called, \
               "LLM called when audio tool should handle it"
    
    def test_mode_extraction(self):
        """Test that mode is correctly extracted from prompts."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        # Test COGNITION mode
        prompt_cognition = "<|mode_start|>COGNITION<|mode_end|> Test"
        mode = router._extract_mode(prompt_cognition)
        assert mode == "COGNITION", f"Expected COGNITION, got {mode}"
        
        # Test DREAM mode
        prompt_dream = "<|mode_start|>DREAM<|mode_end|> Test"
        mode = router._extract_mode(prompt_dream)
        assert mode == "DREAM", f"Expected DREAM, got {mode}"
        
        # Test default mode (no mode tags)
        prompt_default = "No mode tags here"
        mode = router._extract_mode(prompt_default)
        assert mode == "COGNITION", f"Expected COGNITION default, got {mode}"
    
    def test_multiple_modalities_vision_priority(self):
        """Test that when multiple modalities present, each is handled."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        # Prompt with vision (should take priority in current implementation)
        mixed_prompt = """
        <|vision_start|>
        Image data
        <|vision_end|>
        <|audio_start|>
        Audio data
        <|audio_end|>
        """
        
        response = router.handle(mixed_prompt)
        
        # First tool executed should be vision (code reads top-to-bottom)
        assert len(mock_tool_bus.executed_tools) > 0, "No tools executed"
        assert "vision" in mock_tool_bus.executed_tools[0], \
               "Vision not prioritized in multi-modal prompt"


class TestRouterSliceFunction:
    """Test the _slice utility function."""
    
    def test_slice_extracts_vision_content(self):
        """Test that _slice correctly extracts vision content."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        prompt = "<|vision_start|>Test Vision Content<|vision_end|>"
        content = router._slice(prompt, "vision")
        
        assert content == "Test Vision Content", \
               f"Expected 'Test Vision Content', got '{content}'"
    
    def test_slice_returns_none_when_tags_missing(self):
        """Test that _slice returns None when tags are not present."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        prompt = "No special tags here"
        content = router._slice(prompt, "vision")
        
        assert content is None, \
               f"Expected None, got '{content}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
