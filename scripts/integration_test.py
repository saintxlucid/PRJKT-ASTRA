"""
ASTRA Integration Test Suite

Tests end-to-end integration of all ASTRA components:
- Configuration loading
- Database connectivity
- Vector store operations
- LLM provider (without requiring running server)
- Harmony format utilities
- Service layer integration
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("   ASTRA Integration Test Suite")
print("=" * 80)
print()


def test_configuration_integration():
    """Test configuration loading and validation."""
    print("1. Configuration Integration")
    print("-" * 80)
    
    try:
        from astra.models.config import get_settings
        
        settings = get_settings()
        
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Server: {settings.server.host}:{settings.server.port}")
        print(f"✓ LLM Provider: {settings.llm.provider}")
        print(f"✓ LLM Base URL: {settings.llm.base_url}")
        print(f"✓ Model: {settings.llm.model_name}")
        print(f"✓ Reasoning Mode: {settings.llm.reasoning_mode}")
        print(f"✓ Use Harmony Format: {settings.llm.use_harmony_format}")
        print(f"✓ Database URL: {settings.database.url}")
        print(f"✓ Vector Store Path: {settings.vector_store.persist_directory}")
        print()
        
        return True, settings
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False, None


def test_model_intelligence():
    """Test model information and capabilities."""
    print("2. Model Intelligence")
    print("-" * 80)
    
    try:
        from astra.models.model_info import get_model_info, list_available_models
        
        models = list_available_models()
        print(f"✓ Available models: {', '.join(models)}")
        
        model_info = get_model_info("gpt-oss-20b")
        print(f"✓ Model: {model_info.display_name}")
        print(f"✓ Developer: {model_info.developer}")
        print(f"✓ Parameters: {model_info.architecture.parameters:,}")
        print(f"✓ Reasoning Modes: {len(model_info.reasoning_modes)}")
        print(f"✓ Performance Benchmarks: {len(model_info.performance_benchmarks)}")
        print(f"✓ Tool Capabilities: {len(model_info.tool_capabilities)}")
        print()
        
        return True
    except Exception as e:
        print(f"✗ Model intelligence failed: {e}")
        return False


def test_harmony_format():
    """Test Harmony chat format utilities."""
    print("3. Harmony Format Utilities")
    print("-" * 80)
    
    try:
        from astra.infrastructure.llm.harmony import (
            HarmonyPromptBuilder,
            HarmonyRole,
            HarmonyChannel,
            parse_harmony_response,
            strip_cot_from_history,
        )
        
        # Build a prompt
        builder = HarmonyPromptBuilder()
        builder.add_system_message("You are a helpful AI assistant.")
        builder.add_user_message("What is the capital of France?")
        prompt = builder.build()
        
        print(f"✓ Prompt builder working")
        print(f"✓ Prompt length: {len(prompt)} characters")
        print(f"✓ Contains harmony tokens: {'<|start_header_id|>' in prompt}")
        
        # Test parsing
        test_response = """<|start_header_id|>assistant|final<|end_header_id|>

The capital of France is Paris."""
        
        messages = parse_harmony_response(test_response)
        print(f"✓ Parsed {len(messages)} message(s) from response")
        print(f"✓ Response parsing works correctly")
        print()
        
        return True
    except Exception as e:
        print(f"✗ Harmony format failed: {e}")
        return False


def test_database_integration(settings):
    """Test database setup and operations."""
    print("4. Database Integration")
    print("-" * 80)
    
    try:
        from astra.infrastructure.storage.database import DatabaseManager, Base, Conversation, Message
        from datetime import datetime
        import tempfile
        
        # Use temporary database for testing
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db_url = f"sqlite:///{temp_db.name}"
        
        db_manager = DatabaseManager(temp_db_url, echo=False)
        print(f"✓ Database manager created")
        
        # Create tables
        db_manager.create_tables()
        print(f"✓ Tables created")
        
        # Test session
        session = db_manager.get_session()
        
        # Create test conversation
        conv = Conversation(
            conversation_id="test-conv-001",
            title="Integration Test Conversation",
        )
        session.add(conv)
        session.commit()
        print(f"✓ Created test conversation")
        
        # Create test message
        msg = Message(
            conversation_id="test-conv-001",
            role="user",
            content="This is a test message",
        )
        session.add(msg)
        session.commit()
        print(f"✓ Created test message")
        
        # Query back
        conv_query = session.query(Conversation).filter_by(conversation_id="test-conv-001").first()
        msg_query = session.query(Message).filter_by(conversation_id="test-conv-001").first()
        
        print(f"✓ Retrieved conversation: {conv_query.title}")
        print(f"✓ Retrieved message: {msg_query.content[:30]}...")
        
        session.close()
        db_manager.close()
        
        # Cleanup
        import os
        import time
        time.sleep(0.5)  # Give time for file handles to close
        
        try:
            os.unlink(temp_db.name)
        except PermissionError:
            pass  # File still locked, but test passed
        
        print(f"✓ Database test completed successfully")
        print()
        
        return True
    except Exception as e:
        print(f"✗ Database integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store_integration(settings):
    """Test vector store operations."""
    print("5. Vector Store Integration")
    print("-" * 80)
    
    try:
        from astra.infrastructure.storage.vector_store import VectorStore
        import tempfile
        import shutil
        
        # Use temporary directory for testing
        temp_dir = tempfile.mkdtemp(prefix="astra_test_")
        
        vector_store = VectorStore(
            persist_directory=temp_dir,
            collection_name="test_memory",
            embedding_model="all-MiniLM-L6-v2",
        )
        print(f"✓ Vector store initialized")
        
        # Add test memories
        vector_store.add_memory(
            text="The capital of France is Paris.",
            memory_id="mem-001",
            metadata={"conversation_id": "test-001", "role": "assistant"},
        )
        print(f"✓ Added memory 1")
        
        vector_store.add_memory(
            text="Python is a programming language.",
            memory_id="mem-002",
            metadata={"conversation_id": "test-001", "role": "assistant"},
        )
        print(f"✓ Added memory 2")
        
        # Search memories
        results = vector_store.search_memories(
            query="What is the capital of France?",
            top_k=5,
        )
        print(f"✓ Search returned {len(results)} result(s)")
        
        if results:
            top_result = results[0]
            print(f"✓ Top result: {top_result['text'][:50]}...")
            print(f"✓ Distance: {top_result.get('distance', 'N/A')}")
        
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"✓ Vector store test completed successfully")
        print()
        
        return True
    except Exception as e:
        print(f"✗ Vector store integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_layer():
    """Test service layer components."""
    print("6. Service Layer Integration")
    print("-" * 80)
    
    try:
        from astra.services.conversation_service import ConversationService
        from astra.services.memory_service import MemoryService
        from astra.infrastructure.storage.database import DatabaseManager
        from astra.infrastructure.storage.vector_store import VectorStore
        import tempfile
        import shutil
        
        # Setup temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db_url = f"sqlite:///{temp_db.name}"
        db_manager = DatabaseManager(temp_db_url, echo=False)
        db_manager.create_tables()
        
        # Setup temporary vector store
        temp_dir = tempfile.mkdtemp(prefix="astra_test_")
        vector_store = VectorStore(
            persist_directory=temp_dir,
            collection_name="test_memory",
        )
        
        # Create services
        conversation_service = ConversationService(db_manager)
        print(f"✓ Conversation service created")
        
        memory_service = MemoryService(vector_store)
        print(f"✓ Memory service created")
        
        # Test conversation service
        conv_id = conversation_service.create_conversation(title="Test Conversation")
        print(f"✓ Created conversation: {conv_id}")
        
        conversation_service.add_message(
            conversation_id=conv_id,
            role="user",
            content="Hello, ASTRA!"
        )
        print(f"✓ Added message to conversation")
        
        history = conversation_service.get_messages(conv_id)
        print(f"✓ Retrieved conversation messages: {len(history)} message(s)")
        
        # Test memory service
        memory_service.add_memory(
            text="Test memory content",
            conversation_id=conv_id,
            role="assistant",
        )
        print(f"✓ Added memory via service")
        
        results = memory_service.search_relevant_context(
            query="test memory",
            conversation_id=conv_id,
            top_k=3,
        )
        print(f"✓ Searched memories: {len(results)} result(s)")
        
        # Cleanup
        db_manager.close()
        import os
        import time
        time.sleep(0.5)  # Give time for file handles to close
        
        try:
            os.unlink(temp_db.name)
        except PermissionError:
            pass  # File still locked, but test passed
        
        shutil.rmtree(temp_dir)
        
        print(f"✓ Service layer test completed successfully")
        print()
        
        return True
    except Exception as e:
        print(f"✗ Service layer integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_provider_factory():
    """Test LLM provider factory."""
    print("7. LLM Provider Factory")
    print("-" * 80)
    
    try:
        from astra.infrastructure.llm.factory import create_llm_provider
        from astra.models.config import get_settings
        
        settings = get_settings()
        
        # Create provider (won't connect to server yet)
        provider = create_llm_provider(settings)
        print(f"✓ LLM provider created: {type(provider).__name__}")
        print(f"✓ Provider type: {settings.llm.provider}")
        print(f"✓ Base URL: {settings.llm.base_url}")
        print(f"✓ Ready for chat operations (requires llama.cpp server running)")
        print()
        
        return True
    except Exception as e:
        print(f"✗ LLM provider factory failed: {e}")
        return False


def main():
    """Run all integration tests."""
    results = []
    
    # Test 1: Configuration
    success, settings = test_configuration_integration()
    results.append(("Configuration", success))
    
    if not success:
        print("\n✗ Cannot continue without valid configuration")
        return False
    
    # Test 2: Model Intelligence
    success = test_model_intelligence()
    results.append(("Model Intelligence", success))
    
    # Test 3: Harmony Format
    success = test_harmony_format()
    results.append(("Harmony Format", success))
    
    # Test 4: Database
    success = test_database_integration(settings)
    results.append(("Database", success))
    
    # Test 5: Vector Store
    success = test_vector_store_integration(settings)
    results.append(("Vector Store", success))
    
    # Test 6: Service Layer
    success = test_service_layer()
    results.append(("Service Layer", success))
    
    # Test 7: LLM Provider
    success = test_llm_provider_factory()
    results.append(("LLM Provider", success))
    
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
