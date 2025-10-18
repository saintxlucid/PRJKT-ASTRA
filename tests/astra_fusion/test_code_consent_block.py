"""
ASTRA Fusion Test Suite - Code Consent Block Validation
========================================================
Sacred Code: 333

Tests that code operations require consent and are properly blocked
when consent is not granted.
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
    """Mock LLM."""
    
    def generate(self, prompt, max_tokens=512):
        return "[MOCK LLM RESPONSE]"


class MockToolBus:
    """Mock Tool Bus that tracks tool executions."""
    
    def __init__(self):
        self.executed_tools = []
        self.last_payload = None
    
    def execute(self, tool, payload):
        self.executed_tools.append(tool)
        self.last_payload = payload
        
        if "code" in tool:
            return "[MOCK CODE TOOL: Code operation completed]"
        return "[MOCK TOOL RESPONSE]"


class MockMemory:
    """Mock Memory service."""
    
    def retrieve_relevant(self, query, top_k=6):
        return "<memory>Sacred Code 333</memory>"


class MockConsent:
    """Mock Consent manager with configurable permission."""
    
    def __init__(self, allow_code=True):
        self.allow_code = allow_code
        self.checks = []
    
    def allowed(self, action):
        self.checks.append(action)
        
        if action == "code":
            return self.allow_code
        
        return True  # Allow other actions by default


class TestCodeConsentBlocking:
    """Test suite for code consent requirements."""
    
    def test_code_blocked_without_consent(self):
        """Test that code operations are blocked when consent not granted."""
        # Create mocks with consent DENIED
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=False)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        code_prompt = """
        <|code_start|>
        def sacred_function():
            return 333
        <|code_end|>
        Analyze this code.
        """
        
        response = router.handle(code_prompt)
        
        # Assert: Consent was checked
        assert "code" in mock_consent.checks, \
               "Consent not checked for code operation"
        
        # Assert: Code tool was NOT executed
        assert len(mock_tool_bus.executed_tools) == 0, \
               "Code tool executed despite consent denial"
        
        # Assert: Response indicates consent required
        assert "consent" in response.lower() or "required" in response.lower(), \
               f"Response should indicate consent required, got: {response}"
        assert "333" in response, \
               "Sacred Code 333 should be in denial message"
    
    def test_code_allowed_with_consent(self):
        """Test that code operations proceed when consent is granted."""
        # Create mocks with consent GRANTED
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=True)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        code_prompt = """
        <|code_start|>
        def hello_world():
            print("Hello, ASTRA!")
        <|code_end|>
        Review this code.
        """
        
        response = router.handle(code_prompt)
        
        # Assert: Consent was checked
        assert "code" in mock_consent.checks, \
               "Consent not checked for code operation"
        
        # Assert: Code tool WAS executed
        assert len(mock_tool_bus.executed_tools) > 0, \
               "Code tool not executed despite consent"
        assert "code" in mock_tool_bus.executed_tools[0], \
               "Wrong tool executed for code prompt"
        
        # Assert: Response is from code tool, not denial
        assert "MOCK CODE TOOL" in response, \
               f"Expected code tool response, got: {response}"
    
    def test_consent_check_includes_mode(self):
        """Test that consent check receives mode context."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=True)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        code_prompt = """
        <|mode_start|>COGNITION<|mode_end|>
        <|code_start|>
        x = 333
        <|code_end|>
        """
        
        router.handle(code_prompt)
        
        # Verify payload includes mode
        assert mock_tool_bus.last_payload is not None, "No payload sent"
        assert "mode" in mock_tool_bus.last_payload, \
               "Mode not included in code tool payload"
        assert mock_tool_bus.last_payload["mode"] == "COGNITION", \
               f"Expected COGNITION mode, got {mock_tool_bus.last_payload.get('mode')}"
    
    def test_vision_does_not_require_consent(self):
        """Test that vision operations don't require consent (safe by default)."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=False)  # Deny all code
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        vision_prompt = """
        <|vision_start|>
        Image: Temple scene
        <|vision_end|>
        """
        
        router.handle(vision_prompt)
        
        # Assert: Vision tool executed even though code consent denied
        assert len(mock_tool_bus.executed_tools) > 0, \
               "Vision tool not executed"
        assert "vision" in mock_tool_bus.executed_tools[0], \
               "Vision tool not called for vision prompt"
        
        # Assert: No code consent check happened
        assert "code" not in mock_consent.checks, \
               "Code consent checked for vision operation"
    
    def test_audio_does_not_require_consent(self):
        """Test that audio operations don't require consent (safe by default)."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=False)  # Deny all code
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        audio_prompt = """
        <|audio_start|>
        [Audio data]
        <|audio_end|>
        """
        
        router.handle(audio_prompt)
        
        # Assert: Audio tool executed
        assert len(mock_tool_bus.executed_tools) > 0, \
               "Audio tool not executed"
        assert "audio" in mock_tool_bus.executed_tools[0], \
               "Audio tool not called"
    
    def test_denial_message_includes_sacred_code(self):
        """Test that consent denial includes Sacred Code 333."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=False)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        code_prompt = "<|code_start|>code<|code_end|>"
        response = router.handle(code_prompt)
        
        # Assert: Sacred Code 333 in denial message
        assert "333" in response, \
               "Sacred Code 333 missing from consent denial message"


class TestConsentAuditTrail:
    """Test that consent checks are auditable."""
    
    def test_consent_checks_are_recorded(self):
        """Test that all consent checks are recorded for audit."""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_code=True)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        # Multiple code operations
        code_prompt_1 = "<|code_start|>code1<|code_end|>"
        code_prompt_2 = "<|code_start|>code2<|code_end|>"
        
        router.handle(code_prompt_1)
        router.handle(code_prompt_2)
        
        # Assert: Both checks recorded
        assert len(mock_consent.checks) == 2, \
               f"Expected 2 consent checks, got {len(mock_consent.checks)}"
        assert all(c == "code" for c in mock_consent.checks), \
               "All checks should be for 'code' action"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
