"""
ASTRA 2.0 Memory Engine
Implements multi-layered memory system with emotional tagging
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import sqlite3
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import logging

from astra.core.sovereign.guardian import get_guardian
from astra.security.activity_audit import audit_event

logger = logging.getLogger("astra.memory")

class MemoryTypes:
    """Memory classification types"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    EMOTIONAL = "emotional"
    CREATIVE = "creative"
    SOVEREIGN = "sovereign"

class MemoryEngine:
    """ASTRA's multi-layered memory system"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.memory_path = base_path / "memory"
        self.memory_path.mkdir(exist_ok=True)
        
        # Initialize memory stores
        self.short_term_db = self._init_sqlite("short_term.db")
        self.episodic_db = self._init_sqlite("episodic.db")
        self.vector_store = self._init_vector_store()
        
        # Memory statistics
        self.stats = {
            "short_term_count": 0,
            "long_term_count": 0,
            "episodic_count": 0,
            "emotional_events": 0,
            "last_backup": None
        }
        
        self._create_tables()
        logger.info("Memory engine initialized")
        
    def _init_sqlite(self, db_name: str) -> sqlite3.Connection:
        """Initialize SQLite database"""
        db_path = self.memory_path / db_name
        return sqlite3.connect(str(db_path))
        
    def _init_vector_store(self) -> QdrantClient:
        """Initialize Qdrant vector store"""
        vector_path = self.memory_path / "vectors"
        vector_path.mkdir(exist_ok=True)
        
        client = QdrantClient(path=str(vector_path))
        
        # Create collections if they don't exist
        collections = {
            "conversations": 1536,  # GPT embedding size
            "knowledge": 1536,
            "creative": 1536,
            "emotional": 512       # Emotional vector size
        }
        
        for name, dim in collections.items():
            try:
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
                )
            except Exception:
                # Collection already exists
                pass
                
        return client
        
    def _create_tables(self) -> None:
        """Create SQLite tables"""
        # Short-term memory table
        self.short_term_db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                role TEXT,
                content TEXT,
                emotion TEXT,
                context JSON
            )
        """)
        
        # Episodic memory table
        self.episodic_db.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                type TEXT,
                content JSON,
                emotional_state TEXT,
                sovereign_alignment REAL,
                tags JSON
            )
        """)
        
        self.short_term_db.commit()
        self.episodic_db.commit()
        
    def store_conversation(self,
                         content: str,
                         role: str,
                         emotion: Optional[str] = None,
                         context: Optional[Dict] = None) -> str:
        """Store conversation in short-term memory"""
        conversation_id = f"conv_{int(time.time())}_{hash(content)}"
        
        self.short_term_db.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)",
            (
                conversation_id,
                time.time(),
                role,
                content,
                emotion,
                json.dumps(context or {})
            )
        )
        self.short_term_db.commit()
        
        # Update stats
        self.stats["short_term_count"] += 1
        
        return conversation_id
        
    def store_episode(self,
                     content: Dict,
                     type: str,
                     emotional_state: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> str:
        """Store episodic memory"""
        episode_id = f"ep_{int(time.time())}_{hash(str(content))}"
        
        # Get sovereign alignment
        guardian = get_guardian()
        alignment = guardian.verify_sovereign_alignment(
            np.array([0.5]),  # Placeholder neural input
            creator_id=None
        )[1]
        
        self.episodic_db.execute(
            "INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                episode_id,
                time.time(),
                type,
                json.dumps(content),
                emotional_state,
                alignment,
                json.dumps(tags or [])
            )
        )
        self.episodic_db.commit()
        
        # Update stats
        self.stats["episodic_count"] += 1
        
        return episode_id
        
    def store_vector_memory(self,
                          collection: str,
                          vector: np.ndarray,
                          payload: Dict,
                          tags: Optional[List[str]] = None) -> str:
        """Store memory in vector database"""
        memory_id = f"vec_{int(time.time())}_{hash(str(payload))}"
        
        self.vector_store.upsert(
            collection_name=collection,
            points=[{
                "id": memory_id,
                "vector": vector.tolist(),
                "payload": {
                    **payload,
                    "timestamp": time.time(),
                    "tags": tags or []
                }
            }]
        )
        
        # Update stats
        self.stats["long_term_count"] += 1
        
        return memory_id
        
    def query_conversations(self,
                          limit: int = 10,
                          role: Optional[str] = None) -> List[Dict]:
        """Query recent conversations"""
        query = "SELECT * FROM conversations"
        params = []
        
        if role:
            query += " WHERE role = ?"
            params.append(role)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.short_term_db.execute(query, params)
        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "role": row[2],
                "content": row[3],
                "emotion": row[4],
                "context": json.loads(row[5])
            }
            for row in cursor.fetchall()
        ]
        
    def query_episodes(self,
                      type: Optional[str] = None,
                      emotional_state: Optional[str] = None,
                      min_alignment: float = 0.0,
                      limit: int = 10) -> List[Dict]:
        """Query episodic memories"""
        query = "SELECT * FROM episodes WHERE sovereign_alignment >= ?"
        params = [min_alignment]
        
        if type:
            query += " AND type = ?"
            params.append(type)
            
        if emotional_state:
            query += " AND emotional_state = ?"
            params.append(emotional_state)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.episodic_db.execute(query, params)
        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "type": row[2],
                "content": json.loads(row[3]),
                "emotional_state": row[4],
                "sovereign_alignment": row[5],
                "tags": json.loads(row[6])
            }
            for row in cursor.fetchall()
        ]
        
    def query_vector_memories(self,
                            collection: str,
                            vector: np.ndarray,
                            limit: int = 10) -> List[Dict]:
        """Query vector memories by similarity"""
        results = self.vector_store.search(
            collection_name=collection,
            query_vector=vector.tolist(),
            limit=limit
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results
        ]
        
    def backup_memory(self) -> None:
        """Create memory backup"""
        backup_path = self.base_path / "backups" / f"memory_{int(time.time())}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Backup SQLite databases
        for db_name in ["short_term.db", "episodic.db"]:
            src = self.memory_path / db_name
            dst = backup_path / db_name
            if src.exists():
                import shutil
                shutil.copy2(src, dst)
                
        # Backup vector store
        vector_backup = backup_path / "vectors"
        shutil.copytree(
            self.memory_path / "vectors",
            vector_backup,
            dirs_exist_ok=True
        )
        
        # Update stats
        self.stats["last_backup"] = time.time()
        
        audit_event("memory.backup.created", {
            "path": str(backup_path),
            "stats": self.stats
        })
        
        logger.info(f"Memory backup created at {backup_path}")
        
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        return self.stats

# Initialize global memory engine
_MEMORY: Optional[MemoryEngine] = None

def init_memory(base_path: Path) -> None:
    """Initialize global memory engine"""
    global _MEMORY
    _MEMORY = MemoryEngine(base_path)
    
def get_memory() -> MemoryEngine:
    """Get global memory engine instance"""
    global _MEMORY
    if not _MEMORY:
        init_memory(Path.cwd())
    return _MEMORY