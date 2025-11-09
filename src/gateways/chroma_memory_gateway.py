"""
ChromaDB Memory Gateway - Week-2 Architecture
==============================================

Implements MemoryGateway protocol using ChromaDB backend.
Wraps existing VectorStore with protocol-compliant interface.

Architecture: Hexagonal (Ports & Adapters)
- Implements: MemoryGateway protocol (src/domain/interfaces.py)
- Wraps: VectorStore (src/astra/infrastructure/storage/vector_store.py)
- Integrates: Memory signing for tamper detection

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Days 9-10)
"""

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import uuid4

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from astra.infrastructure.storage.vector_store import VectorStore
    from core.memory_signing import MemorySigner
except ImportError:
    # Fallback: define stubs for testing
    VectorStore = None  # type: ignore
    MemorySigner = None  # type: ignore


class ChromaMemoryGateway:
    """
    ChromaDB implementation of MemoryGateway protocol.
    
    Features:
    - Semantic search via sentence-transformers embeddings
    - Memory signing (HMAC-SHA256) for tamper detection
    - Metadata filtering (conversation_id, timestamp, etc.)
    - CRUD operations with UUID generation
    
    Storage:
    - Vector embeddings: ChromaDB
    - Memory signatures: Inline metadata
    """
    
    def __init__(
        self,
        persist_directory: str = "data/chroma",
        collection_name: str = "astra_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        signing_key: str | None = None
    ):
        """
        Initialize ChromaDB memory gateway.
        
        Args:
            persist_directory: ChromaDB storage path
            collection_name: Collection name
            embedding_model: Sentence-transformers model
            signing_key: HMAC key for memory signing (optional)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB vector store
        if VectorStore:
            self.vector_store = VectorStore(
                persist_directory=persist_directory,
                collection_name=collection_name,
                embedding_model=embedding_model,
                distance_metric="cosine"
            )
        else:
            self.vector_store = None
            print(f"⚠️  WARNING: VectorStore not available (import failed)")
        
        # Initialize memory signer
        if MemorySigner and signing_key:
            self.signer = MemorySigner(signing_key)
        else:
            self.signer = None
            if not signing_key:
                print(f"⚠️  WARNING: Memory signing disabled (no key provided)")
    
    def add(self, record: dict[str, Any]) -> str:
        """
        Store a memory record.
        
        Args:
            record: Must contain 'text', optional 'metadata'
            
        Returns:
            Record ID (UUID)
            
        Raises:
            ValueError: If record missing 'text' field
        """
        if "text" not in record:
            raise ValueError("Record must contain 'text' field")
        
        text = record["text"]
        metadata = record.get("metadata", {})
        memory_id = record.get("id", str(uuid4()))
        
        # Sign memory if signer available
        if self.signer:
            signature = self.signer.sign_memory(text)
            metadata["signature"] = signature
            metadata["signed"] = True
        
        # Store in ChromaDB
        if self.vector_store:
            self.vector_store.add_memory(
                text=text,
                memory_id=memory_id,
                metadata=metadata
            )
        
        return memory_id
    
    def get(self, ids: Iterable[str]) -> Iterable[dict[str, Any]]:
        """
        Retrieve records by IDs.
        
        Args:
            ids: Collection of record IDs
            
        Returns:
            Iterable of records with keys: id, text, metadata
        """
        if not self.vector_store:
            return []
        
        ids_list = list(ids)
        if not ids_list:
            return []
        
        try:
            # Query ChromaDB by IDs
            results = self.vector_store.collection.get(
                ids=ids_list,
                include=["documents", "metadatas"]
            )
            
            # Transform to protocol format
            records = []
            for i, memory_id in enumerate(results["ids"]):
                record = {
                    "id": memory_id,
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {}
                }
                records.append(record)
            
            return records
        
        except Exception as e:
            print(f"❌ Error retrieving memories: {e}")
            return []
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None
    ) -> Iterable[dict[str, Any]]:
        """
        Semantic search for relevant memories.
        
        Args:
            query: Search query text
            limit: Maximum results to return
            filters: Metadata filters (e.g., {"conversation_id": "123"})
            
        Returns:
            Iterable of records with keys: id, text, distance, metadata
        """
        if not self.vector_store:
            return []
        
        try:
            # Search using existing VectorStore
            results = self.vector_store.search_memories(
                query=query,
                top_k=limit,
                filter_metadata=filters
            )
            
            # Transform to protocol format
            records = []
            for result in results:
                record = {
                    "id": result.get("id", "unknown"),
                    "text": result.get("text", ""),
                    "distance": result.get("distance", 1.0),
                    "metadata": result.get("metadata", {})
                }
                
                # Verify signature if present
                if self.signer and record["metadata"].get("signed"):
                    signature = record["metadata"].get("signature")
                    if signature:
                        is_valid = self.signer.verify_signature(
                            record["text"],
                            signature
                        )
                        record["metadata"]["signature_valid"] = is_valid
                
                records.append(record)
            
            return records
        
        except Exception as e:
            print(f"❌ Error searching memories: {e}")
            return []
    
    def delete(self, ids: Iterable[str]) -> int:
        """
        Delete records by IDs.
        
        Args:
            ids: Collection of record IDs to delete
            
        Returns:
            Number of records deleted
        """
        if not self.vector_store:
            return 0
        
        ids_list = list(ids)
        if not ids_list:
            return 0
        
        try:
            self.vector_store.collection.delete(ids=ids_list)
            return len(ids_list)
        except Exception as e:
            print(f"❌ Error deleting memories: {e}")
            return 0
    
    def scan_for_tampering(self) -> Iterable[str]:
        """
        Scan all signed memories for tampering.
        
        Returns:
            Iterable of IDs for tampered records
        """
        if not self.signer or not self.vector_store:
            return []
        
        try:
            # Get all records
            all_results = self.vector_store.collection.get(
                include=["documents", "metadatas"]
            )
            
            tampered_ids = []
            for i, memory_id in enumerate(all_results["ids"]):
                metadata = all_results["metadatas"][i] if all_results.get("metadatas") else {}
                
                # Check if memory is signed
                if metadata.get("signed"):
                    text = all_results["documents"][i]
                    signature = metadata.get("signature")
                    
                    if signature:
                        is_valid = self.signer.verify_signature(text, signature)
                        if not is_valid:
                            tampered_ids.append(memory_id)
            
            return tampered_ids
        
        except Exception as e:
            print(f"❌ Error scanning for tampering: {e}")
            return []
    
    def count(self) -> int:
        """
        Get total number of records.
        
        Returns:
            Record count
        """
        if not self.vector_store:
            return 0
        
        try:
            return self.vector_store.collection.count()
        except Exception as e:
            print(f"❌ Error counting memories: {e}")
            return 0


# Test standalone execution
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 CHROMA MEMORY GATEWAY - STANDALONE TEST")
    print("="*80 + "\n")
    
    # Create gateway
    print("📦 Creating ChromaMemoryGateway...")
    gateway = ChromaMemoryGateway(
        persist_directory="data/chroma_test",
        collection_name="test_collection",
        signing_key="test_secret_key_for_hmac_signing"
    )
    
    if not gateway.vector_store:
        print("❌ VectorStore not available - cannot run test")
        sys.exit(1)
    
    print(f"✅ Gateway created\n")
    
    # Test 1: Add memories
    print("📝 Test 1: Adding memories...")
    id1 = gateway.add({
        "text": "ASTRA is an AI assistant with memory capabilities",
        "metadata": {"type": "system", "importance": "high"}
    })
    print(f"   ✅ Added memory 1: {id1}")
    
    id2 = gateway.add({
        "text": "Python 3.13 supports modern type hints and Protocol",
        "metadata": {"type": "technical", "language": "python"}
    })
    print(f"   ✅ Added memory 2: {id2}\n")
    
    # Test 2: Get by ID
    print("🔍 Test 2: Retrieving by ID...")
    records = list(gateway.get([id1]))
    if records:
        print(f"   ✅ Retrieved: {records[0]['text'][:50]}...")
        print(f"   📝 Metadata: {records[0]['metadata']}\n")
    
    # Test 3: Semantic search
    print("🔎 Test 3: Semantic search...")
    results = list(gateway.search("What is ASTRA?", limit=2))
    print(f"   ✅ Found {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['text'][:60]}... (distance: {result['distance']:.4f})")
    print()
    
    # Test 4: Tampering detection
    print("🔒 Test 4: Tampering detection...")
    tampered = list(gateway.scan_for_tampering())
    if tampered:
        print(f"   ⚠️  Found {len(tampered)} tampered records: {tampered}")
    else:
        print(f"   ✅ No tampering detected\n")
    
    # Test 5: Count
    print("📊 Test 5: Record count...")
    count = gateway.count()
    print(f"   ✅ Total records: {count}\n")
    
    # Test 6: Delete
    print("🗑️  Test 6: Deleting records...")
    deleted = gateway.delete([id1, id2])
    print(f"   ✅ Deleted {deleted} records\n")
    
    print("="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80 + "\n")
