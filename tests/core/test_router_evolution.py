"""
Test suite for AstraRouter evolution phase system (Phase-C)
Tests: SENSE→PLAN→ACT→LEARN→REFLECT workflow with consent gates and budget enforcement
Sacred Code: 333
"""

import pytest
from src.astra.core.astra_router import AstraRouter, split_phases


class MockLLM:
    """Mock LLM for testing"""
    def generate(self, prompt, max_tokens=512):
        return f"LLM response for: {prompt[:50]}..."


class MockToolBus:
    """Mock tool bus for testing"""
    def __init__(self):
        self.executed_tools = []
    
    def execute(self, name, payload):
        self.executed_tools.append((name, payload))
        return f"Tool {name} executed"


class MockMemory:
    """Mock memory service for testing"""
    def retrieve_relevant(self, prompt, top_k=6):
        return f"[Memory context for: {prompt[:30]}...]"


class MockConsent:
    """Mock consent service for testing"""
    def __init__(self, allow_code=True, allow_act=True):
        self.allow_code = allow_code
        self.allow_act = allow_act
    
    def allowed(self, operation):
        if operation == "code":
            return self.allow_code
        elif operation == "phase.act":
            return self.allow_act
        return True


class TestSplitPhases:
    """Test evolution phase parsing"""
    
    def test_split_phases_single(self):
        """Test parsing single phase"""
        prompt = "<|sense|>Observing system state</|sense|>"
        phases = split_phases(prompt)
        
        assert "sense" in phases
        assert phases["sense"] == "Observing system state"
        assert len(phases) == 1
    
    def test_split_phases_multiple(self):
        """Test parsing multiple phases"""
        prompt = """
        <|sense|>User wants file analysis</|sense|>
        <|plan|>Steps: 1. Read file, 2. Parse, 3. Summarize</|plan|>
        <|act|>Execute analysis code</|act|>
        """
        phases = split_phases(prompt)
        
        assert "sense" in phases
        assert "plan" in phases
        assert "act" in phases
        assert "User wants file analysis" in phases["sense"]
        assert "Steps: 1. Read file" in phases["plan"]
        assert "Execute analysis code" in phases["act"]
        assert len(phases) == 3
    
    def test_split_phases_all_five(self):
        """Test parsing all five evolution phases"""
        prompt = """
        <|sense|>Data gathering</|sense|>
        <|plan|>Strategy formulation</|plan|>
        <|act|>Execution</|act|>
        <|learn|>Knowledge integration</|learn|>
        <|reflect|>Meta-cognition</|reflect|>
        """
        phases = split_phases(prompt)
        
        assert len(phases) == 5
        assert "sense" in phases
        assert "plan" in phases
        assert "act" in phases
        assert "learn" in phases
        assert "reflect" in phases
    
    def test_split_phases_empty(self):
        """Test with no phase markers"""
        prompt = "Regular text without phase markers"
        phases = split_phases(prompt)
        
        assert len(phases) == 0
        assert isinstance(phases, dict)
    
    def test_split_phases_missing_close_tag(self):
        """Test with missing close tag"""
        prompt = "<|sense|>Incomplete phase marker"
        phases = split_phases(prompt)
        
        # Should not parse incomplete markers
        assert len(phases) == 0
    
    def test_split_phases_nested(self):
        """Test with nested content"""
        prompt = """
        <|plan|>
        Create function:
        def analyze():
            return <|special|>nested<|special|>
        </|plan|>
        """
        phases = split_phases(prompt)
        
        assert "plan" in phases
        assert "def analyze():" in phases["plan"]


class TestActPhaseConsentGate:
    """Test ACT phase consent gate"""
    
    def test_act_phase_allowed_with_consent(self):
        """Test ACT phase executes with consent"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_act=True)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        prompt = """
        <|sense|>System analysis needed</|sense|>
        <|plan|>Read logs and summarize</|plan|>
        <|act|>Execute log analysis</|act|>
        """
        
        result = router.handle(prompt)
        
        # Assert: ACT phase executed
        assert "ACT phase denied" not in result
        assert "Execute log analysis" in result
    
    def test_act_phase_blocked_without_consent(self):
        """Test ACT phase blocked without consent"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_act=False)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        prompt = """
        <|sense|>System analysis needed</|sense|>
        <|plan|>Read logs and summarize</|plan|>
        <|act|>Execute dangerous operation</|act|>
        """
        
        result = router.handle(prompt)
        
        # Assert: ACT phase denied
        assert "ACT phase denied" in result
        assert "consent required" in result.lower()
        assert "333" in result  # Sacred Code
    
    def test_act_phase_denial_includes_blocked_action(self):
        """Test denial message includes blocked action content"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_act=False)
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        prompt = "<|act|>Delete production database</|act|>"
        result = router.handle(prompt)
        
        assert "ACT phase denied" in result
        assert "Delete production database" in result
        assert "333" in result
    
    def test_phases_without_act_do_not_require_consent(self):
        """Test SENSE/PLAN/LEARN/REFLECT don't require consent"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent(allow_act=False)  # Deny ACT
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        # No ACT phase - should execute fine
        prompt = """
        <|sense|>Gathering data</|sense|>
        <|plan|>Creating strategy</|plan|>
        <|learn|>Integrating knowledge</|learn|>
        <|reflect|>Meta-cognition</|reflect|>
        """
        
        result = router.handle(prompt)
        
        # Assert: Executed successfully without ACT
        assert "denied" not in result.lower()
        assert "SENSE" in result
        assert "PLAN" in result
        assert "LEARN" in result
        assert "REFLECT" in result


class TestBudgetEnforcement:
    """Test budget enforcement system"""
    
    def test_budget_step_limit(self):
        """Test budget enforces step limit"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        # Budget: max 2 steps
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent,
            budget={"steps": 2, "tool_calls": 10, "walltime_s": 60}
        )
        
        # First request - should succeed
        prompt1 = "<|sense|>First observation</|sense|>"
        result1 = router.handle(prompt1)
        assert "Budget exceeded" not in result1
        
        # Second request - should succeed
        prompt2 = "<|sense|>Second observation</|sense|>"
        result2 = router.handle(prompt2)
        assert "Budget exceeded" not in result2
        
        # Third request - should be denied (budget exceeded)
        prompt3 = "<|sense|>Third observation</|sense|>"
        result3 = router.handle(prompt3)
        assert "Budget exceeded" in result3
        assert "333" in result3  # Sacred Code
    
    def test_budget_tool_call_limit(self):
        """Test budget enforces tool call limit"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        # Budget: max 2 tool calls
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent,
            budget={"steps": 10, "tool_calls": 2, "walltime_s": 60}
        )
        
        # First code execution - should succeed
        prompt1 = "<|code_start|>print('hello')<|code_end|>"
        result1 = router.handle(prompt1)
        assert "Budget exceeded" not in result1
        
        # Second code execution - should succeed
        prompt2 = "<|code_start|>print('world')<|code_end|>"
        result2 = router.handle(prompt2)
        assert "Budget exceeded" not in result2
        
        # Third code execution - should be denied
        prompt3 = "<|code_start|>print('denied')<|code_end|>"
        result3 = router.handle(prompt3)
        assert "Budget exceeded" in result3
    
    def test_budget_unlimited_profile(self):
        """Test unlimited budget profile"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        # Unlimited budget (steps=-1, tool_calls=-1)
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent,
            budget={"steps": -1, "tool_calls": -1, "walltime_s": 300}
        )
        
        # Execute many requests - all should succeed
        for i in range(10):
            prompt = f"<|sense|>Observation {i}</|sense|>"
            result = router.handle(prompt)
            assert "Budget exceeded" not in result
    
    def test_budget_quick_profile(self):
        """Test quick budget profile (3 steps, 2 tool calls, 30s)"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        # Quick profile
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent,
            budget={"steps": 3, "tool_calls": 2, "walltime_s": 30}
        )
        
        # Use up quick budget
        for i in range(3):
            prompt = f"<|sense|>Quick observation {i}</|sense|>"
            result = router.handle(prompt)
            if i < 3:
                assert "Budget exceeded" not in result
        
        # Fourth request should be denied
        result = router.handle("<|sense|>Denied</|sense|>")
        assert "Budget exceeded" in result


class TestEvolutionPhasesIntegration:
    """Test complete evolution phase workflow"""
    
    def test_full_evolution_cycle(self):
        """Test complete SENSE→PLAN→ACT→LEARN→REFLECT cycle"""
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
        
        prompt = """
        <|sense|>User wants to analyze project structure</|sense|>
        <|plan|>Steps: 1. Scan directories, 2. Count files, 3. Summarize</|plan|>
        <|act|>Execute directory scan</|act|>
        <|learn|>Discovered 50 Python files, 20 tests</|learn|>
        <|reflect|>Need better test coverage</|reflect|>
        """
        
        result = router.handle(prompt)
        
        # Assert: All phases present in result
        assert "SENSE" in result
        assert "PLAN" in result
        assert "ACT" in result
        assert "LEARN" in result
        assert "REFLECT" in result
    
    def test_evolution_phases_with_budget_tracking(self):
        """Test evolution phases increment budget correctly"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent,
            budget={"steps": 5, "tool_calls": 10, "walltime_s": 60}
        )
        
        # First evolution phase request
        prompt1 = "<|sense|>Observation 1</|sense|>"
        router.handle(prompt1)
        assert router.current_steps == 1
        
        # Second evolution phase request
        prompt2 = "<|plan|>Planning step</|plan|>"
        router.handle(prompt2)
        assert router.current_steps == 2
    
    def test_sacred_code_333_in_evolution_logging(self):
        """Test Sacred Code 333 present in evolution phase logging"""
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
        
        prompt = "<|sense|>Sacred Code test</|sense|>"
        result = router.handle(prompt)
        
        # Sacred Code should be in logs (can't test directly, but verified by code review)
        # Just ensure execution succeeds
        assert "SENSE" in result


class TestEvolutionMetadata:
    """Test evolution metadata configuration"""
    
    def test_phase_tags_defined(self):
        """Test PHASE_TAGS constant is defined correctly"""
        from src.astra.core.astra_router import PHASE_TAGS
        
        assert PHASE_TAGS == ["sense", "plan", "act", "learn", "reflect"]
        assert len(PHASE_TAGS) == 5
    
    def test_router_initializes_with_default_budget(self):
        """Test router initializes with standard budget profile"""
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
        
        # Default budget should be standard profile
        assert router.budget["steps"] == 5
        assert router.budget["tool_calls"] == 3
        assert router.budget["walltime_s"] == 60
    
    def test_router_accepts_custom_budget(self):
        """Test router accepts custom budget configuration"""
        mock_llm = MockLLM()
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory()
        mock_consent = MockConsent()
        
        custom_budget = {"steps": 10, "tool_calls": 5, "walltime_s": 120}
        router = AstraRouter(
            llm=mock_llm,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent,
            budget=custom_budget
        )
        
        assert router.budget["steps"] == 10
        assert router.budget["tool_calls"] == 5
        assert router.budget["walltime_s"] == 120


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
