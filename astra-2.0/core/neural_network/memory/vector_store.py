"""
ASTRA Vector Memory Store - Persistent Memory System
"""
from typing import List, Dict, Tuple, Optional
import numpy as np
from pathlib import Path
import faiss
import sqlite3
import json
from datetime import datetime
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer

@dataclass
class Document:
    page_content: str
    metadata: Dict

class VectorStore:
    def __init__(self, 
                 path: Path,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 dimension: int = 384):
        """Initialize vector store with SQLite + FAISS"""
        self.path = path
        self.dimension = dimension
        
        # Initialize embedding model
        self.embedder = SentenceTransformer(embedding_model)
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(dimension)  # Inner product similarity
        
        # Initialize SQLite connection
        self.db_path = path / "memory.db"
        self._init_db()
        
        # Load existing vectors
        self._load_existing()
        
    def _init_db(self) -> None:
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
    def _load_existing(self) -> None:
        """Load existing memories into FAISS"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content FROM memories")
            texts = [row[0] for row in cursor.fetchall()]
            
        if texts:
            vectors = self.embedder.encode(texts)
            self.index.add(vectors.astype(np.float32))
            
    def add_texts(self, 
                 texts: List[str], 
                 metadatas: Optional[List[Dict]] = None) -> List[str]:
        """Add texts and metadata to memory"""
        if not texts:
            return []
            
        # Generate embeddings
        vectors = self.embedder.encode(texts)
        
        # Add to FAISS
        self.index.add(vectors.astype(np.float32))
        
        # Add to SQLite
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.executemany(
                """
                INSERT INTO memories (content, metadata, created_at)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        text, 
                        json.dumps(meta or {}),
                        now
                    )
                    for text, meta in zip(
                        texts, 
                        metadatas or [{}] * len(texts)
                    )
                ]
            )
            
        return [str(cursor.lastrowid + i) for i in range(len(texts))]
        
    def similarity_search(self,
                        query: str,
                        k: int = 4) -> List[Tuple[Document, float]]:
        """Search for similar texts"""
        # Generate query vector
        query_vec = self.embedder.encode([query])
        
        # Search FAISS
        scores, indices = self.index.search(
            query_vec.astype(np.float32), 
            k
        )
        
        # Get texts and metadata
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT content, metadata 
                FROM memories 
                WHERE id IN ({})
                """.format(",".join("?" * len(indices[0]))),
                [int(i) + 1 for i in indices[0]]  # SQLite is 1-indexed
            )
            rows = cursor.fetchall()
            
        # Build document objects
        docs_with_scores = []
        for row, score in zip(rows, scores[0]):
            docs_with_scores.append((
                Document(
                    page_content=row["content"],
                    metadata=json.loads(row["metadata"])
                ),
                float(score)
            ))
            
        return sorted(docs_with_scores, key=lambda x: x[1], reverse=True)
        
    def clear(self) -> None:
        """Clear all memories"""
        self.index.reset()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories")
            
    def save(self) -> None:
        """Save FAISS index to disk"""
        index_path = self.path / "vectors.index"
        faiss.write_index(self.index, str(index_path))
        
    def load(self) -> None:
        """Load FAISS index from disk"""
        index_path = self.path / "vectors.index"
        if index_path.exists():
            self.index = faiss.read_index(str(index_path))