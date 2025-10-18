"""
ASTRA Fusion Test Suite - Init
================================
Sacred Code: 333

Test suite initialization and shared fixtures.
"""

import pytest
import sys
from pathlib import Path

# Add fusion pipeline to path for all tests
fusion_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/ops/fusion_pipeline/scripts")
if fusion_path.exists():
    sys.path.insert(0, str(fusion_path))


@pytest.fixture
def mock_llm():
    """Fixture for mock LLM."""
    class MockLLM:
        def __init__(self):
            self.called = False
            self.last_prompt = None
        
        def generate(self, prompt, max_tokens=512):
            self.called = True
            self.last_prompt = prompt
            return "[MOCK LLM RESPONSE]"
    
    return MockLLM()


@pytest.fixture
def mock_tool_bus():
    """Fixture for mock Tool Bus."""
    class MockToolBus:
        def __init__(self):
            self.executed_tools = []
            self.last_payload = None
        
        def execute(self, tool, payload):
            self.executed_tools.append(tool)
            self.last_payload = payload
            
            if "vision" in tool:
                return "[MOCK VISION RESPONSE]"
            elif "audio" in tool:
                return "[MOCK AUDIO RESPONSE]"
            elif "code" in tool:
                return "[MOCK CODE RESPONSE]"
            return "[MOCK TOOL RESPONSE]"
    
    return MockToolBus()


@pytest.fixture
def mock_memory():
    """Fixture for mock Memory service."""
    class MockMemory:
        def retrieve_relevant(self, query, top_k=6):
            return "<memory>Sacred Code 333 context</memory>"
    
    return MockMemory()


@pytest.fixture
def mock_consent():
    """Fixture for mock Consent manager (allow all by default)."""
    class MockConsent:
        def __init__(self):
            self.checks = []
        
        def allowed(self, action):
            self.checks.append(action)
            return True
    
    return MockConsent()


@pytest.fixture
def mock_consent_deny_code():
    """Fixture for mock Consent manager that denies code operations."""
    class MockConsent:
        def __init__(self):
            self.checks = []
        
        def allowed(self, action):
            self.checks.append(action)
            return action != "code"
    
    return MockConsent()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "benchmark: mark test as a performance benchmark"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
