"""
Test ASTRA Identity Engine

Quick test script to verify identity loading works.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import yaml
from src.astra.core.identity_engine import IdentityEngine

def test_identity():
    """Test identity loading"""
    print("\n" + "="*80)
    print("ASTRA IDENTITY ENGINE TEST")
    print("="*80 + "\n")
    
    # Create engine
    engine = IdentityEngine()
    
    # Load identity
    identity = engine.load_identity()
    
    print(f"✓ Identity loaded successfully!")
    print(f"\n  Name: {identity.name}")
    print(f"  Full Name: {identity.full_name}")
    print(f"  Version: {identity.version}")
    print(f"  Creator: {identity.creator}")
    print(f"  Project: {identity.project}")
    print(f"\n  Essence: {identity.essence}")
    
    print(f"\nPersonality Traits:")
    print(f"  Warmth: {identity.warmth:.2f}")
    print(f"  Precision: {identity.precision:.2f}")
    print(f"  Creativity: {identity.creativity:.2f}")
    print(f"  Formality: {identity.formality:.2f}")
    print(f"  Verbosity: {identity.verbosity:.2f}")
    print(f"  Enthusiasm: {identity.enthusiasm:.2f}")
    
    # Test system prompt generation
    print("\n" + "="*80)
    print("SYSTEM PROMPT (without memory):")
    print("="*80)
    prompt = engine.generate_system_prompt()
    print(prompt[:500] + "...\n")
    
    # Test with memory
    print("="*80)
    print("SYSTEM PROMPT (with sample memory):")
    print("="*80)
    sample_memory = """SEMANTIC MEMORY (Facts & Knowledge):
  1. User prefers direct, concise answers
  2. Working on PROJECT_ASTRA_1.0 deployment
  3. Uses Python 3.11 and FastAPI"""
    
    prompt_with_memory = engine.generate_system_prompt(memory_context=sample_memory)
    # Show the memory injection part
    memory_idx = prompt_with_memory.find("RETRIEVED MEMORIES")
    if memory_idx > 0:
        print(prompt_with_memory[memory_idx:memory_idx+300] + "...\n")
    
    # Test greeting
    print("="*80)
    print("ACTIVATION GREETING:")
    print("="*80)
    greeting = engine.generate_greeting(semantic_count=147)
    print(greeting)
    
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_identity()
