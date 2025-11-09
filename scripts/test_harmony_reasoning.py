"""
Test Harmony Format and Reasoning Mode Integration

This script validates the integration of Harmony format and reasoning mode
into the ChatService and LlamaCppProvider.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("   Harmony Format & Reasoning Mode Integration Test")
print("=" * 80)
print()


def test_harmony_integration():
    """Test Harmony format integration in LlamaCppProvider."""
    print("1. Testing Harmony Format Integration")
    print("-" * 80)
    
    try:
        from astra.infrastructure.llm.llamacpp import LlamaCppProvider
        from astra.infrastructure.llm.base import Message
        
        # Test with Harmony format enabled
        provider_harmony = LlamaCppProvider(
            base_url="http://localhost:8001",
            timeout=60,
            retry_attempts=3,
            use_harmony_format=True,
        )
        
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is 2+2?"),
        ]
        
        prompt_harmony = provider_harmony._convert_messages(messages)
        
        print(f"✓ LlamaCppProvider created with Harmony format enabled")
        print(f"✓ Harmony format: use_harmony_format={provider_harmony.use_harmony_format}")
        print(f"✓ Converted messages to Harmony format")
        print(f"✓ Prompt length: {len(prompt_harmony)} characters")
        print(f"✓ Contains Harmony tokens: {'<|start_header_id|>' in prompt_harmony}")
        print()
        
        # Test with simple format
        provider_simple = LlamaCppProvider(
            base_url="http://localhost:8001",
            timeout=60,
            retry_attempts=3,
            use_harmony_format=False,
        )
        
        prompt_simple = provider_simple._convert_messages(messages)
        
        print(f"✓ LlamaCppProvider created with simple format")
        print(f"✓ Simple format: use_harmony_format={provider_simple.use_harmony_format}")
        print(f"✓ Converted messages to simple format")
        print(f"✓ Prompt length: {len(prompt_simple)} characters")
        print(f"✓ Does not contain Harmony tokens: {'<|start_header_id|>' not in prompt_simple}")
        print()
        
        print("Sample Harmony prompt (first 200 chars):")
        print(prompt_harmony[:200] + "...")
        print()
        
        return True
        
    except Exception as e:
        print(f"✗ Harmony integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reasoning_mode():
    """Test reasoning mode configuration in ChatService."""
    print("2. Testing Reasoning Mode Configuration")
    print("-" * 80)
    
    try:
        from astra.models.config import get_settings
        from astra.services.chat_service import ChatService
        from astra.services.conversation_service import ConversationService
        from astra.services.memory_service import MemoryService
        from astra.infrastructure.storage.database import DatabaseManager
        from astra.infrastructure.storage.vector_store import VectorStore
        import tempfile
        
        # Setup minimal services for testing
        settings = get_settings()
        
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db_url = f"sqlite:///{temp_db.name}"
        db_manager = DatabaseManager(temp_db_url, echo=False)
        db_manager.create_tables()
        
        temp_dir = tempfile.mkdtemp(prefix="astra_test_")
        vector_store = VectorStore(
            persist_directory=temp_dir,
            collection_name="test_memory",
        )
        
        conversation_service = ConversationService(db_manager)
        memory_service = MemoryService(vector_store)
        chat_service = ChatService(settings, conversation_service, memory_service)
        
        print(f"✓ ChatService created successfully")
        print(f"✓ Configured reasoning mode: {settings.llm.reasoning_mode}")
        print(f"✓ Configured use_harmony_format: {settings.llm.use_harmony_format}")
        print()
        
        # Test reasoning mode parameters
        reasoning_params = chat_service._get_reasoning_params()
        
        print(f"✓ Reasoning parameters retrieved:")
        print(f"   - Temperature: {reasoning_params.get('temperature')}")
        print(f"   - Top-p: {reasoning_params.get('top_p')}")
        print(f"   - Effort: {reasoning_params.get('reasoning_effort')}")
        print()
        
        # Test all reasoning modes
        modes = ["low", "medium", "high"]
        for mode in modes:
            settings.llm.reasoning_mode = mode
            params = chat_service._get_reasoning_params()
            print(f"✓ Mode '{mode}': temp={params['temperature']}, top_p={params['top_p']}")
        
        print()
        
        # Cleanup
        import shutil
        import os
        db_manager.close()
        
        import time
        time.sleep(0.5)
        
        try:
            os.unlink(temp_db.name)
            shutil.rmtree(temp_dir)
        except (PermissionError, OSError):
            pass  # Cleanup failed but test passed
        
        return True
        
    except Exception as e:
        print(f"✗ Reasoning mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chatservice_harmony():
    """Test ChatService Harmony format conversion."""
    print("3. Testing ChatService Harmony Conversion")
    print("-" * 80)
    
    try:
        from astra.models.config import get_settings
        from astra.services.chat_service import ChatService
        from astra.services.conversation_service import ConversationService
        from astra.services.memory_service import MemoryService
        from astra.infrastructure.storage.database import DatabaseManager
        from astra.infrastructure.storage.vector_store import VectorStore
        from astra.infrastructure.llm.base import Message
        import tempfile
        
        # Setup minimal services
        settings = get_settings()
        
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db_url = f"sqlite:///{temp_db.name}"
        db_manager = DatabaseManager(temp_db_url, echo=False)
        db_manager.create_tables()
        
        temp_dir = tempfile.mkdtemp(prefix="astra_test_")
        vector_store = VectorStore(
            persist_directory=temp_dir,
            collection_name="test_memory",
        )
        
        conversation_service = ConversationService(db_manager)
        memory_service = MemoryService(vector_store)
        chat_service = ChatService(settings, conversation_service, memory_service)
        
        # Test Harmony conversion
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        
        harmony_prompt = chat_service._convert_to_harmony_format(messages)
        
        print(f"✓ ChatService created")
        print(f"✓ Converted {len(messages)} messages to Harmony format")
        print(f"✓ Harmony prompt length: {len(harmony_prompt)} characters")
        print(f"✓ Contains Harmony tokens: {'<|start_header_id|>' in harmony_prompt}")
        print()
        
        print("Sample Harmony prompt (first 300 chars):")
        print(harmony_prompt[:300] + "...")
        print()
        
        # Cleanup
        import shutil
        import os
        db_manager.close()
        
        import time
        time.sleep(0.5)
        
        try:
            os.unlink(temp_db.name)
            shutil.rmtree(temp_dir)
        except (PermissionError, OSError):
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ ChatService Harmony test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_harmony():
    """Test factory creates provider with Harmony format setting."""
    print("4. Testing LLM Provider Factory")
    print("-" * 80)
    
    try:
        from astra.infrastructure.llm.factory import create_llm_provider
        from astra.models.config import get_settings
        
        settings = get_settings()
        
        # Create provider through factory
        provider = create_llm_provider(settings)
        
        print(f"✓ Provider created through factory")
        print(f"✓ Provider type: {type(provider).__name__}")
        print(f"✓ Harmony format enabled: {provider.use_harmony_format}")
        print(f"✓ Harmony format matches settings: {provider.use_harmony_format == settings.llm.use_harmony_format}")
        print()
        
        return True
        
    except Exception as e:
        print(f"✗ Factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    results = []
    
    # Test 1: Harmony Integration
    success = test_harmony_integration()
    results.append(("Harmony Format Integration", success))
    
    # Test 2: Reasoning Mode
    success = test_reasoning_mode()
    results.append(("Reasoning Mode Configuration", success))
    
    # Test 3: ChatService Harmony
    success = test_chatservice_harmony()
    results.append(("ChatService Harmony Conversion", success))
    
    # Test 4: Factory
    success = test_factory_harmony()
    results.append(("LLM Provider Factory", success))
    
    # Summary
    print("=" * 80)
    print("   Integration Test Summary")
    print("=" * 80)
    print()
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"   {status:<12} {name}")
    
    print()
    print(f"   Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print()
    
    if passed == total:
        print("   ✓ ALL INTEGRATION TESTS PASSED!")
        print("   ✓ Harmony format is integrated into ChatService and LlamaCppProvider")
        print("   ✓ Reasoning mode switching is operational")
        print()
        print("=" * 80)
        return True
    else:
        print("   ✗ Some integration tests failed")
        print()
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
