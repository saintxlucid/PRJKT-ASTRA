"""
ASTRA-OS Memory Layer
Implements episodic memory (SQLite), vector memory (FAISS), and secret vault (DPAPI).

File: libs/memory/__init__.py
Lines: 650+
"""

import sqlite3
import json
import os
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from contextlib import contextmanager
import threading

try:
    import numpy as np
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger("astra.memory")


@dataclass
class EpisodicEvent:
    """Episodic memory entry."""
    id: str
    ts: str
    type: str  # "sensor", "action", "task", "feedback"
    payload: Dict[str, Any]
    embedding_vector: Optional[List[float]] = None
    tags: List[str] = None
    importance: float = 0.5  # 0.0-1.0


@dataclass
class Task:
    """Task execution record."""
    id: str
    created_at: str
    status: str  # "planning", "executing", "completed", "failed"
    plan_json: Dict[str, Any]
    result_json: Dict[str, Any]
    risk_score: float
    consent_token: Optional[str] = None
    duration_ms: int = 0


@dataclass
class Reward:
    """Learning feedback record."""
    id: str
    ts: str
    task_id: str
    score: float  # -1.0 to +1.0
    notes: str


class MemoryVault:
    """
    Encrypted secret storage using DPAPI (Windows) or Fernet (cross-platform).
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.key_index_file = self.vault_path / "keys.json"
        self.keys = self._load_key_index()
        self.cipher = self._init_cipher()
    
    def _init_cipher(self):
        """Initialize encryption cipher."""
        if HAS_CRYPTO:
            # Generate or load key
            key_file = self.vault_path / "vault.key"
            if key_file.exists():
                with open(key_file, "rb") as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(key)
            return Fernet(key)
        return None
    
    def _load_key_index(self) -> Dict[str, Dict[str, Any]]:
        """Load key metadata index."""
        if self.key_index_file.exists():
            with open(self.key_index_file) as f:
                return json.load(f)
        return {}
    
    def _save_key_index(self):
        """Save key metadata index."""
        with open(self.key_index_file, "w") as f:
            json.dump(self.keys, f, indent=2)
    
    def store(self, key_name: str, secret: str) -> bool:
        """Store encrypted secret."""
        try:
            if not self.cipher:
                logger.warning("Encryption not available; storing plaintext")
                secret_bytes = secret.encode()
            else:
                secret_bytes = self.cipher.encrypt(secret.encode())
            
            secret_file = self.vault_path / f"{key_name}.secret"
            with open(secret_file, "wb") as f:
                f.write(secret_bytes)
            
            self.keys[key_name] = {
                "created_at": datetime.utcnow().isoformat(),
                "hash": hashlib.sha256(secret.encode()).hexdigest()[:16],
            }
            self._save_key_index()
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {key_name}: {e}")
            return False
    
    def retrieve(self, key_name: str) -> Optional[str]:
        """Retrieve decrypted secret."""
        try:
            secret_file = self.vault_path / f"{key_name}.secret"
            if not secret_file.exists():
                return None
            
            with open(secret_file, "rb") as f:
                secret_bytes = f.read()
            
            if not self.cipher:
                return secret_bytes.decode()
            
            return self.cipher.decrypt(secret_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to retrieve secret {key_name}: {e}")
            return None
    
    def delete(self, key_name: str) -> bool:
        """Delete secret."""
        try:
            secret_file = self.vault_path / f"{key_name}.secret"
            if secret_file.exists():
                secret_file.unlink()
            if key_name in self.keys:
                del self.keys[key_name]
                self._save_key_index()
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {key_name}: {e}")
            return False


class VectorStore:
    """FAISS-based semantic memory vector store."""
    
    def __init__(self, dimension: int = 384, index_path: Optional[str] = None):
        self.dimension = dimension
        self.index_path = index_path
        self.index = None
        self.id_map: Dict[int, str] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        if HAS_FAISS:
            self._init_index()
        else:
            logger.warning("FAISS not available; vector store disabled")
    
    def _init_index(self):
        """Initialize FAISS index."""
        if not HAS_FAISS:
            return
        
        try:
            if self.index_path and os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded FAISS index from {self.index_path}")
            else:
                # Flat index for small datasets
                self.index = faiss.IndexFlatL2(self.dimension)
                logger.info(f"Created new FAISS index (dim={self.dimension})")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS: {e}")
            self.index = None
    
    def add(self, event_id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Add vector to store."""
        if not self.index:
            return False
        
        try:
            if len(vector) != self.dimension:
                logger.warning(f"Vector dimension mismatch: {len(vector)} != {self.dimension}")
                return False
            
            vec_array = np.array([vector], dtype=np.float32)
            next_id = self.index.ntotal
            self.index.add(vec_array)
            self.id_map[next_id] = event_id
            self.metadata[event_id] = metadata
            
            if self.index_path:
                self._save_index()
            
            return True
        except Exception as e:
            logger.error(f"Failed to add vector: {e}")
            return False
    
    def search(self, vector: List[float], k: int = 5) -> List[Tuple[str, float]]:
        """Search for nearest neighbors."""
        if not self.index or self.index.ntotal == 0:
            return []
        
        try:
            vec_array = np.array([vector], dtype=np.float32)
            distances, indices = self.index.search(vec_array, min(k, self.index.ntotal))
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1 and idx in self.id_map:
                    results.append((self.id_map[idx], float(dist)))
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _save_index(self):
        """Save index to disk."""
        if self.index and self.index_path:
            try:
                faiss.write_index(self.index, self.index_path)
            except Exception as e:
                logger.error(f"Failed to save index: {e}")


class EpisodicMemoryDB:
    """
    SQLite-based episodic memory database.
    Stores events, tasks, rewards, policies, and audit logs.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._conn() as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    subject_json TEXT,
                    context_json TEXT,
                    severity TEXT,
                    trace_id TEXT,
                    embedding_vector TEXT
                )
            """)
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT,
                    result_json TEXT,
                    risk_score REAL,
                    consent_token TEXT,
                    duration_ms INTEGER
                )
            """)
            
            # Episodic memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mem_episodic (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT,
                    embedding_vector TEXT,
                    tags TEXT,
                    importance REAL
                )
            """)
            
            # Policies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    yaml TEXT,
                    version INTEGER,
                    enabled INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Rewards table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rewards (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    score REAL,
                    notes TEXT,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )
            """)
            
            # Secrets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id TEXT PRIMARY KEY,
                    key_name TEXT NOT NULL UNIQUE,
                    blob_dpapi BLOB,
                    created_at TEXT
                )
            """)
            
            # Consent log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consent_log (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    action_preview TEXT,
                    risk_score REAL,
                    approved INTEGER,
                    operator_notes TEXT
                )
            """)
            
            # Incident table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    detection_type TEXT,
                    severity TEXT,
                    context_json TEXT,
                    status TEXT,
                    bundle_path TEXT
                )
            """)
            
            conn.commit()
            logger.info(f"Initialized episodic memory DB: {self.db_path}")
    
    @contextmanager
    def _conn(self):
        """Get database connection with lock."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    def store_event(self, event_id: str, ts: str, topic: str, actor: str,
                   subject: Dict[str, Any], context: Dict[str, Any],
                   severity: str, trace_id: str) -> bool:
        """Store event in memory."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO events
                    (id, ts, topic, actor, subject_json, context_json, severity, trace_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, ts, topic, actor,
                    json.dumps(subject), json.dumps(context),
                    severity, trace_id
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return False
    
    def store_task(self, task_id: str, created_at: str, status: str,
                  plan: Dict[str, Any], result: Dict[str, Any],
                  risk_score: float, consent_token: Optional[str] = None) -> bool:
        """Store task record."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks
                    (id, created_at, status, plan_json, result_json, risk_score, consent_token)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, created_at, status,
                    json.dumps(plan), json.dumps(result),
                    risk_score, consent_token
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Task(
                    id=row["id"],
                    created_at=row["created_at"],
                    status=row["status"],
                    plan_json=json.loads(row["plan_json"]),
                    result_json=json.loads(row["result_json"]),
                    risk_score=row["risk_score"],
                    consent_token=row["consent_token"],
                    duration_ms=row["duration_ms"]
                )
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
            return None
    
    def query_events(self, topic_filter: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """Query events with optional topic filter."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                
                if topic_filter:
                    cursor.execute("""
                        SELECT * FROM events
                        WHERE topic LIKE ?
                        ORDER BY ts DESC
                        LIMIT ?
                    """, (f"{topic_filter}%", limit))
                else:
                    cursor.execute("""
                        SELECT * FROM events
                        ORDER BY ts DESC
                        LIMIT ?
                    """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []
    
    def store_reward(self, reward_id: str, ts: str, task_id: str,
                    score: float, notes: str) -> bool:
        """Store learning reward."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO rewards (id, ts, task_id, score, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (reward_id, ts, task_id, score, notes))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store reward: {e}")
            return False
    
    def get_task_rewards(self, task_id: str) -> List[Reward]:
        """Get all rewards for a task."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM rewards WHERE task_id = ?
                """, (task_id,))
                rows = cursor.fetchall()
                
                return [
                    Reward(
                        id=row["id"],
                        ts=row["ts"],
                        task_id=row["task_id"],
                        score=row["score"],
                        notes=row["notes"]
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get rewards: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                
                stats = {}
                for table in ["events", "tasks", "mem_episodic", "rewards", "incidents"]:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    stats[table] = cursor.fetchone()["cnt"]
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


class MemoryLayer:
    """
    Unified memory layer combining episodic, vector, and secret storage.
    """
    
    def __init__(self, data_dir: str, embeddings_dim: int = 384):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.episodic = EpisodicMemoryDB(str(self.data_dir / "episodic.db"))
        self.vector_store = VectorStore(
            dimension=embeddings_dim,
            index_path=str(self.data_dir / "vectors" / "index.faiss") if HAS_FAISS else None
        )
        self.vault = MemoryVault(str(self.data_dir / "secrets"))
    
    def store_event_with_embedding(self, event_id: str, ts: str, topic: str,
                                  actor: str, subject: Dict[str, Any],
                                  context: Dict[str, Any], severity: str,
                                  trace_id: str,
                                  embedding: Optional[List[float]] = None) -> bool:
        """Store event with optional vector embedding."""
        success = self.episodic.store_event(
            event_id, ts, topic, actor, subject, context, severity, trace_id
        )
        
        if success and embedding:
            metadata = {"topic": topic, "actor": actor, "ts": ts}
            self.vector_store.add(event_id, embedding, metadata)
        
        return success
    
    def semantic_search(self, query_embedding: List[float], k: int = 5) -> List[Tuple[str, float]]:
        """Search episodic memory by semantic similarity."""
        return self.vector_store.search(query_embedding, k)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory layer statistics."""
        return {
            "episodic": self.episodic.get_stats(),
            "vector_store_size": self.vector_store.index.ntotal if self.vector_store.index else 0,
        }


__all__ = [
    "EpisodicEvent",
    "Task",
    "Reward",
    "MemoryVault",
    "VectorStore",
    "EpisodicMemoryDB",
    "MemoryLayer",
]
