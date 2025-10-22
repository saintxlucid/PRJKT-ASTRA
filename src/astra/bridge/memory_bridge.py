"""
ASTRA Bridge Memory Service
Interface for LTM and Episodic memory adapters.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from enum import Enum
import structlog

logger = structlog.get_logger()

class MemoryType(str, Enum):
    """Type of memory storage."""
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    HYBRID = "hybrid"

@dataclass
class Document:
    """Document representation."""
    id: str
    content: str
    metadata: Dict[str, Any]

@dataclass
class QueryResult:
    """Query result with documents."""
    documents: List[Document]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class RetrievalResult:
    """Result of retrieval operation."""
    query: str
    documents: List[Document]
    metadata: Dict[str, Any]

class MemoryStore:
    """Base class for memory storage."""
    
    def get_relevant(self, query: str, context: Optional[Dict] = None) -> List[Document]:
        """Get relevant documents for query."""
        raise NotImplementedError
    
    def update(self, docs: List[Document]) -> None:
        """Update documents in store."""
        raise NotImplementedError
    
    def store(self, query: str, answer: str, context: Dict) -> None:
        """Store query-answer pair."""
        raise NotImplementedError

class LongTermMemory(MemoryStore):
    """Semantic memory storage."""
    
    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.docs: List[Document] = []
        if path and path.exists():
            self._load()
    
    def get_relevant(self, query: str, context: Optional[Dict] = None) -> List[Document]:
        """Get semantically relevant documents."""
        # Simple keyword matching for demo
        keywords = query.lower().split()
        results = []
        for doc in self.docs:
            if any(kw in doc.content.lower() for kw in keywords):
                results.append(doc)
        return results
    
    def update(self, docs: List[Document]) -> None:
        """Update semantic memory."""
        self.docs.extend(docs)
        if self.path:
            self._save()
    
    def _load(self) -> None:
        """Load from file."""
        try:
            data = json.loads(self.path.read_text())
            self.docs = [
                Document(
                    id=d["id"],
                    content=d["content"],
                    metadata=d["metadata"]
                )
                for d in data
            ]
        except Exception as e:
            logger.error("ltm_load_failed", error=str(e))
            
    def _save(self) -> None:
        """Save to file."""
        try:
            data = [
                {
                    "id": d.id,
                    "content": d.content,
                    "metadata": d.metadata
                }
                for d in self.docs
            ]
            self.path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error("ltm_save_failed", error=str(e))

class EpisodicMemory(MemoryStore):
    """Episodic memory storage."""
    
    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.episodes: List[Dict] = []
        if path and path.exists():
            self._load()
            
    def get_relevant(self, query: str, context: Optional[Dict] = None) -> List[Document]:
        """Get contextually relevant episodes."""
        # Simple recency-based retrieval for demo
        docs = []
        for episode in reversed(self.episodes):
            if episode["query"] == query:
                doc = Document(
                    id=f"epi_{len(docs)}",
                    content=episode["answer"],
                    metadata={"context": episode["context"]}
                )
                docs.append(doc)
        return docs
    
    def store(self, query: str, answer: str, context: Dict) -> None:
        """Store new episode."""
        self.episodes.append({
            "query": query,
            "answer": answer,
            "context": context
        })
        if self.path:
            self._save()
    
    def _load(self) -> None:
        """Load from file."""
        try:
            self.episodes = json.loads(self.path.read_text())
        except Exception as e:
            logger.error("episodic_load_failed", error=str(e))
            
    def _save(self) -> None:
        """Save to file."""
        try:
            self.path.write_text(json.dumps(self.episodes, indent=2))
        except Exception as e:
            logger.error("episodic_save_failed", error=str(e))

class MemoryBridge:
    """Bridge between different memory types."""
    
    def __init__(
        self,
        memory_type: str = "hybrid",
        ltm_path: Optional[Path] = None,
        episodic_path: Optional[Path] = None
    ):
        """Initialize memory stores."""
        if memory_type not in [t.value for t in MemoryType]:
            raise ValueError(f"Invalid memory type: {memory_type}")
            
        self.memory_type = MemoryType(memory_type)
        self.ltm = LongTermMemory(ltm_path)
        self.episodic = EpisodicMemory(episodic_path)
    
    def pre_retrieve(self, query: str, context: Dict) -> QueryResult:
        """Pre-retrieval hook to augment query."""
        ltm_docs = []
        episodic_docs = []
        
        try:
            # Get relevant documents from both stores
            ltm_docs = self.ltm.get_relevant(query)
        except Exception as e:
            logger.error("ltm_retrieve_failed", error=str(e))
            
        try:
            episodic_docs = self.episodic.get_relevant(query, context)
        except Exception as e:
            logger.error("episodic_retrieve_failed", error=str(e))
        
        # Combine results
        all_docs = ltm_docs + episodic_docs
        return QueryResult(documents=all_docs)
    
    def post_retrieve(self, result: RetrievalResult, context: Dict) -> RetrievalResult:
        """Post-retrieval hook to update memory."""
        try:
            # Update LTM with new documents
            self.ltm.update(result.documents)
        except Exception as e:
            logger.error("ltm_update_failed", error=str(e))
        return result
    
    def post_answer(self, query: str, answer: str, context: Dict) -> None:
        """Post-answer hook to store interaction."""
        # Store in episodic memory
        self.episodic.store(query, answer, context)
    
    def save_state(self) -> None:
        """Save memory state to disk."""
        if hasattr(self.ltm, '_save'):
            self.ltm._save()
        if hasattr(self.episodic, '_save'):
            self.episodic._save()

class MemoryBridgeService:
    """Service wrapper for memory bridge functionality."""

    def __init__(
        self,
        memory_type: str = "hybrid",
        ltm_path: Optional[Path] = None,
        episodic_path: Optional[Path] = None
    ):
        """Initialize memory bridge service."""
        self.bridge = MemoryBridge(memory_type, ltm_path, episodic_path)
        
    async def get_relevant(self, query: str, context: Optional[Dict] = None) -> QueryResult:
        """Get relevant documents asynchronously."""
        return self.bridge.pre_retrieve(query, context or {})
    
    async def store_interaction(self, query: str, answer: str, context: Dict) -> None:
        """Store interaction in memory."""
        self.bridge.post_answer(query, answer, context)
        
    async def update_documents(self, result: RetrievalResult) -> RetrievalResult:
        """Update document store with new documents."""
        try:
            return self.bridge.post_retrieve(result, {})
        except Exception as e:
            logger.error("service_update_failed", error=str(e))
            return result  # Return original result on error
    
    def save(self) -> None:
        """Save memory state."""
        self.bridge.save_state()