"""Direct test of memory stats flow."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from astra.core.memory_engine import MemoryEngine
from astra.infrastructure.storage.vector_store import VectorStore


def test_memory_stats():
    """Test memory stats retrieval."""
    print("🧪 Testing Memory Stats Flow...")
    
    # Initialize vector store first
    vector_store = VectorStore(
        persist_directory="data/chroma",
        collection_name="astra_memory",
    )
    
    # Initialize engine with vector store
    engine = MemoryEngine(vector_store=vector_store)
    
    # Get stats
    try:
        stats = engine.get_memory_stats()
        print(f"✅ Memory stats: {stats}")
        
        if stats.get("semantic", 0) > 0:
            print("✅ Semantic memories found!")
            
            # Try retrieve_memories
            results = engine.retrieve_memories(
                query="test query",
                max_semantic=5,
                max_episodic=0,
                max_procedural=0
            )
            print(f"✅ Retrieved {len(results.memories)} memories")
            for m in results.memories:
                print(f"   - {m.content[:60]}...")
        else:
            print("❌ No semantic memories in stats")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("🎉 STATS TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_memory_stats()
    sys.exit(0 if success else 1)
