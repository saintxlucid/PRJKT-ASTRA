# ChromaDB Memory Gateway with BGE-M3 Embeddings
# SPDX-License-Identifier: MIT
"""
ChromaMemoryGateway: Persistent semantic memory with BGE-M3 embeddings.

Implements MemoryGateway protocol with:
- BGE-M3 state-of-the-art embeddings (1024D, multi-lingual, 8192 context)
- HMAC-SHA256 memory signing for tamper detection
- Provenance tracking (source document citations)
- Automatic embedding on store()
- Semantic + metadata search
- Collection lifecycle (create, delete)

Performance: 15-20% better retrieval vs older models (MiniLM, all-mpnet-base-v2)
"""
from __future__ import annotations
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# BGE-M3 embedder
try:
    from services.embeddings_bge_m3 import BGE_M3_Embedder, EmbeddingConfig
    BGE_M3_AVAILABLE = True
except ImportError:
    BGE_M3_AVAILABLE = False

# Domain interfaces
from domain.interfaces import MemoryGateway
from domain.events import EventBus, emit


@dataclass
class MemoryRecord:
    """Single memory record with provenance."""
    id: str
    text: str
    metadata: dict
    embedding: list[float] | None = None
    signature: str | None = None
    source_file: str | None = None  # Provenance: source document
    timestamp: float | None = None


class ChromaMemoryGatewayBGE(MemoryGateway):
    """
    ChromaDB-backed memory with BGE-M3 embeddings and provenance tracking.
    
    Features:
    - BGE-M3 embeddings (state-of-the-art, local, 1024D)
    - HMAC-SHA256 signing (tamper detection)
    - Provenance tracking (citations: "According to [doc X]...")
    - Persistent storage (survives restarts)
    - Metadata filtering (source, type, timestamp)
    
    Usage:
        gateway = ChromaMemoryGatewayBGE(
            persist_dir="data/memory_bge_m3",
            hmac_key="your-secret-key"
        )
        
        # Store with provenance
        gateway.store(
            text="ASTRA uses hexagonal architecture",
            metadata={"source_file": "ARCHITECTURE.md", "section": "Design"}
        )
        
        # Search with provenance
        results = gateway.search("What architecture does ASTRA use?", top_k=3)
        for r in results:
            print(f"{r.text} (Source: {r.source_file})")
    """
    
    def __init__(
        self,
        persist_dir: str | Path = "data/memory_bge_m3",
        collection_name: str = "astra_memories_bge_m3",
        hmac_key: str | None = None,
        embedding_config: dict | None = None
    ):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("chromadb not installed. Run: pip install chromadb")
        
        if not BGE_M3_AVAILABLE:
            raise RuntimeError(
                "BGE-M3 embedder not available.\n"
                "Install: pip install sentence-transformers"
            )
        
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.hmac_key = (hmac_key or "astra-default-key").encode("utf-8")
        
        # Initialize ChromaDB
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize BGE-M3 embedder
        embed_cfg = EmbeddingConfig(**(embedding_config or {}))
        self.embedder = BGE_M3_Embedder(embed_cfg)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(self.collection_name)
            emit("memory_collection_loaded", {
                "collection": self.collection_name,
                "count": self.collection.count()
            })
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "model": "BAAI/bge-m3",
                    "dimension": 1024,
                    "description": "BGE-M3 embeddings with provenance"
                }
            )
            emit("memory_collection_created", {"collection": self.collection_name})
    
    def _sign_text(self, text: str) -> str:
        """Generate HMAC-SHA256 signature for tamper detection."""
        return hmac.new(
            self.hmac_key,
            text.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_signature(self, text: str, signature: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        expected = self._sign_text(text)
        return hmac.compare_digest(expected, signature)
    
    def store(
        self,
        text: str,
        metadata: dict | None = None,
        memory_id: str | None = None
    ) -> str:
        """
        Store text with BGE-M3 embedding and provenance.
        
        Args:
            text: Text to store
            metadata: Optional metadata (source_file, type, etc.)
            memory_id: Optional explicit ID (default: auto-generated)
        
        Returns:
            Memory ID
        """
        metadata = metadata or {}
        
        # Auto-generate ID if not provided
        if not memory_id:
            memory_id = hashlib.sha256(
                (text + str(time.time())).encode("utf-8")
            ).hexdigest()[:16]
        
        # Embed with BGE-M3
        start = time.time()
        embedding = self.embedder.embed_single(text).tolist()
        embed_time = time.time() - start
        
        # Sign text
        signature = self._sign_text(text)
        
        # Add metadata
        metadata["signature"] = signature
        metadata["timestamp"] = time.time()
        metadata["embed_latency_ms"] = int(embed_time * 1000)
        
        # Store in ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        emit("memory_stored", {
            "memory_id": memory_id,
            "text_length": len(text),
            "source_file": metadata.get("source_file"),
            "embed_latency_ms": metadata["embed_latency_ms"]
        })
        
        return memory_id
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: dict | None = None
    ) -> list[MemoryRecord]:
        """
        Search memories with BGE-M3 semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            filter_metadata: Optional metadata filters (e.g., {"source_file": "ARCH.md"})
        
        Returns:
            List of MemoryRecord with provenance
        """
        # Embed query with BGE-M3
        query_embedding = self.embedder.embed_single(query).tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata  # Metadata filtering
        )
        
        # Parse results
        memories = []
        tampered_count = 0
        
        if results and "ids" in results and results["ids"]:
            for i, mem_id in enumerate(results["ids"][0]):
                text = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results else None
                
                # Verify signature
                signature = metadata.get("signature", "")
                is_valid = self._verify_signature(text, signature)
                
                if not is_valid:
                    tampered_count += 1
                    emit("memory_tampered", {
                        "memory_id": mem_id,
                        "text_preview": text[:100]
                    })
                
                memories.append(MemoryRecord(
                    id=mem_id,
                    text=text,
                    metadata=metadata,
                    signature=signature,
                    source_file=metadata.get("source_file"),
                    timestamp=metadata.get("timestamp")
                ))
        
        emit("memory_searched", {
            "query": query,
            "top_k": top_k,
            "results_count": len(memories),
            "tampered_count": tampered_count
        })
        
        return memories
    
    def get(self, memory_id: str) -> MemoryRecord | None:
        """Get specific memory by ID."""
        try:
            result = self.collection.get(ids=[memory_id])
            
            if result and "ids" in result and result["ids"]:
                text = result["documents"][0]
                metadata = result["metadatas"][0]
                
                return MemoryRecord(
                    id=memory_id,
                    text=text,
                    metadata=metadata,
                    signature=metadata.get("signature"),
                    source_file=metadata.get("source_file"),
                    timestamp=metadata.get("timestamp")
                )
        except Exception as e:
            emit("memory_get_failed", {"memory_id": memory_id, "error": str(e)})
        
        return None
    
    def delete(self, memory_id: str) -> bool:
        """Delete specific memory."""
        try:
            self.collection.delete(ids=[memory_id])
            emit("memory_deleted", {"memory_id": memory_id})
            return True
        except Exception as e:
            emit("memory_delete_failed", {"memory_id": memory_id, "error": str(e)})
            return False
    
    def count(self) -> int:
        """Count total memories."""
        return self.collection.count()
    
    def clear(self) -> bool:
        """Clear all memories (DESTRUCTIVE)."""
        try:
            # Delete and recreate collection
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "model": "BAAI/bge-m3",
                    "dimension": 1024,
                    "description": "BGE-M3 embeddings with provenance"
                }
            )
            emit("memory_cleared", {"collection": self.collection_name})
            return True
        except Exception as e:
            emit("memory_clear_failed", {"error": str(e)})
            return False


# Factory function
def build_chroma_gateway_bge_from_config(conf: dict) -> ChromaMemoryGatewayBGE:
    """
    Factory: Build ChromaMemoryGatewayBGE from config.
    
    Config example (astra.yaml):
        memory:
          backend: "chromadb"
          persist_directory: "data/memory_bge_m3"
          collection_name: "astra_memories_bge_m3"
          embeddings:
            model: "BAAI/bge-m3"
            device: "cpu"
            batch_size: 32
          signing:
            hmac_key: "${ASTRA_MEMORY_KEY}"
    """
    mem_conf = conf.get("memory", {})
    embed_conf = mem_conf.get("embeddings", {})
    signing_conf = mem_conf.get("signing", {})
    
    return ChromaMemoryGatewayBGE(
        persist_dir=mem_conf.get("persist_directory", "data/memory_bge_m3"),
        collection_name=mem_conf.get("collection_name", "astra_memories_bge_m3"),
        hmac_key=signing_conf.get("hmac_key"),
        embedding_config=embed_conf
    )


# Example usage
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("=== ChromaMemoryGatewayBGE Test ===\n")
    
    # Initialize
    gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3_test",
        hmac_key="test-key"
    )
    
    print(f"✅ Initialized: {gateway.count()} memories\n")
    
    # Store with provenance
    print("Storing memories with provenance...")
    gateway.store(
        "ASTRA uses hexagonal architecture with domain-driven design",
        metadata={"source_file": "ARCHITECTURE.md", "section": "Design"}
    )
    gateway.store(
        "Memory signing uses HMAC-SHA256 for tamper detection",
        metadata={"source_file": "security/memory_signing.md", "type": "security"}
    )
    gateway.store(
        "BGE-M3 provides 15-20% better retrieval than older models",
        metadata={"source_file": "embeddings_bge_m3.py", "type": "technical"}
    )
    
    print(f"✅ Stored 3 memories (total: {gateway.count()})\n")
    
    # Search with provenance
    print("Searching: 'What architecture does ASTRA use?'")
    results = gateway.search("What architecture does ASTRA use?", top_k=2)
    
    for i, r in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Text: {r.text[:80]}...")
        print(f"    Source: {r.source_file}")
        print(f"    Signature valid: {gateway._verify_signature(r.text, r.signature)}")
    
    print("\n✅ Test complete")
