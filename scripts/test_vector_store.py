"""Smoke test for vector store after Chroma fix."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from astra.infrastructure.storage.vector_store import VectorStore


def test_vector_store():
    """Test vector store count and embedding."""
    print("🧪 Testing VectorStore...")
    
    # Initialize store
    store = VectorStore(
        persist_directory="data/chroma",
        collection_name="astra_memory",
    )
    
    # Test count
    count = store.count()
    print(f"✅ Vector store count: {count}")
    
    # Test embed
    try:
        results = store.search_memories("test query", top_k=2)
        print(f"✅ Search returned {len(results)} results")
        if results:
            print(f"   Sample: {results[0]['text'][:60]}...")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    print("🎉 Unit 1 SMOKE TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_vector_store()
    sys.exit(0 if success else 1)
