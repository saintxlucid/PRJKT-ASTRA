#!/usr/bin/env python3
"""
=====================================================================
ASTRA Fusion Pipeline - Step 5: Runtime Hook Example
=====================================================================
Purpose: Route mode & modality sections to appropriate subsystems
Integration: Tool Bus, Memory, Consent System
Sacred Code: 333
=====================================================================
"""

import re
from typing import Dict, Any, Optional


# Modal extraction patterns
MODE_RX = re.compile(r"<\|mode_start\|>(.*?)<\|mode_end\|>", re.S)

class AstraRouter:
    """
    Pre-tokenization router for ASTRA special token dispatch.
    
    Handles mode selection and modality routing before LLM tokenization.
    Integrates with Tool Bus, Memory, and Consent systems.
    """
    
    def __init__(self, llm, tool_bus, memory, consent):
        """
        Initialize ASTRA router.
        
        Args:
            llm: Core language model instance
            tool_bus: Tool execution coordinator
            memory: Memory retrieval system (semantic + episodic)
            consent: Consent management system for safety checks
        """
        self.llm = llm
        self.tool_bus = tool_bus
        self.memory = memory
        self.consent = consent
    
    def _extract_mode(self, prompt: str) -> str:
        """Extract operating mode from prompt."""
        m = MODE_RX.search(prompt)
        return (m.group(1).strip().upper() if m else "COGNITION")
    
    def _slice(self, prompt: str, tag: str) -> Optional[str]:
        """Extract content between special token tags."""
        try:
            start_tag = f"<|{tag}_start|>"
            end_tag = f"<|{tag}_end|>"
            s = prompt.index(start_tag) + len(start_tag)
            e = prompt.index(end_tag)
            return prompt[s:e].strip()
        except ValueError:
            return None
    
    def handle(self, prompt: str) -> str:
        """
        Main routing handler - dispatches based on special tokens.
        
        Pre-tokenization intercepts:
        - Vision content → Vision tool
        - Audio content → Audio tool
        - Code content → Code intelligence tool (with consent)
        
        Falls back to LLM with memory augmentation for text.
        
        Args:
            prompt: Raw user prompt with special tokens
            
        Returns:
            Response string from appropriate subsystem
        """
        # Extract mode
        mode = self._extract_mode(prompt)
        
        # Extract modality sections
        vision = self._slice(prompt, "vision")
        audio = self._slice(prompt, "audio")
        code = self._slice(prompt, "code")
        
        # PRE-TOKENIZATION INTERCEPTS
        
        # Code intelligence (requires consent)
        if code:
            if not self.consent.allowed("code"):
                return "❌ Consent required for code operations. Sacred Code: 333"
            
            return self.tool_bus.execute(
                "code.apply_plan_or_summarize",
                payload={"code_block": code, "mode": mode}
            )
        
        # Vision processing
        if vision:
            return self.tool_bus.execute(
                "vision.describe_or_answer",
                payload={"vision_block": vision, "mode": mode}
            )
        
        # Audio processing
        if audio:
            return self.tool_bus.execute(
                "audio.transcribe_or_analyze",
                payload={"audio_block": audio, "mode": mode}
            )
        
        # Memory-augmented text generation
        # Retrieve relevant context from semantic + episodic memory
        mem_context = self.memory.retrieve_relevant(prompt, top_k=6)
        
        # Construct augmented prompt
        if mem_context:
            augmented_prompt = f"{mem_context}\n\n{prompt}"
        else:
            augmented_prompt = prompt
        
        # Add mode context if non-standard
        if mode != "COGNITION":
            augmented_prompt = f"<|mode_start|>{mode}<|mode_end|>\n{augmented_prompt}"
        
        # Fall back to core LLM
        return self.llm.generate(augmented_prompt, max_tokens=512)


# =====================================================================
# Integration Example for llm_service.py
# =====================================================================

class AstraLLMService:
    """Example integration into existing LLM service."""
    
    def __init__(self, config):
        from services.llm_client import LLMClient
        from services.tool_bus import ToolBus
        from services.memory_service import MemoryService
        from services.consent_manager import ConsentManager
        
        self.llm = LLMClient(config)
        self.tool_bus = ToolBus()
        self.memory = MemoryService()
        self.consent = ConsentManager()
        
        # Initialize ASTRA router
        self.router = AstraRouter(
            llm=self.llm,
            tool_bus=self.tool_bus,
            memory=self.memory,
            consent=self.consent
        )
    
    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Main chat endpoint with ASTRA routing.
        
        Args:
            message: User message (may contain special tokens)
            context: Optional context dict
            
        Returns:
            Response string
        """
        # Route through ASTRA handler
        return self.router.handle(message)


# =====================================================================
# Standalone Test Example
# =====================================================================

def test_router():
    """Test ASTRA router with mock services."""
    
    class MockLLM:
        def generate(self, prompt, max_tokens=512):
            return f"[LLM Response to: {prompt[:50]}...]"
    
    class MockToolBus:
        def execute(self, tool, payload):
            return f"[ToolBus: {tool} executed with {len(str(payload))} bytes]"
    
    class MockMemory:
        def retrieve_relevant(self, query, top_k=6):
            return "<memory>Sacred Code 333 context</memory>"
    
    class MockConsent:
        def allowed(self, action):
            return True  # Allow all for testing
    
    # Create router
    router = AstraRouter(
        llm=MockLLM(),
        tool_bus=MockToolBus(),
        memory=MockMemory(),
        consent=MockConsent()
    )
    
    # Test cases
    print("🧪 Testing ASTRA Router")
    print("Sacred Code: 333")
    print()
    
    # Test 1: Vision
    print("Test 1: Vision routing")
    vision_prompt = """
    <|mode_start|>COGNITION<|mode_end|>
    <|vision_start|>
    [Image embedding: pharaonic temple, black & gold]
    <|vision_end|>
    Describe this image.
    """
    print(f"→ {router.handle(vision_prompt)}")
    print()
    
    # Test 2: Code
    print("Test 2: Code routing")
    code_prompt = """
    <|code_start|>
    def sacred_function():
        return 333
    <|code_end|>
    Analyze this code.
    """
    print(f"→ {router.handle(code_prompt)}")
    print()
    
    # Test 3: Pure text (memory-augmented)
    print("Test 3: Text with memory")
    text_prompt = "<|mode_start|>DREAM<|mode_end|> Tell me about ASTRA's purpose."
    print(f"→ {router.handle(text_prompt)}")
    print()


if __name__ == "__main__":
    test_router()
