"""
ASTRA Enhanced Memory System
Unified memory system with BGE-M3 embeddings and workflow learning.
Created: October 16, 2025
"""
from typing import List, Dict, Any, Optional
import structlog
from pathlib import Path
import sqlite3
import json
from datetime import datetime
import chromadb
from chromadb.config import Settings
import numpy as np
from transformers import AutoModel, AutoTokenizer
import torch
from dataclasses import dataclass
from collections import defaultdict

logger = structlog.get_logger()

@dataclass
class MemoryConfig:
    """Memory system configuration"""
    semantic_store_path: Path
    episodic_db_path: Path
    embedding_model: str = "BAAI/bge-m3"
    top_k: int = 6
    multi_query: bool = True
    workflow_threshold: int = 3

class Memory:
    """Memory record with metadata"""
    def __init__(
        self,
        content: str,
        memory_type: str,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.memory_type = memory_type
        self.timestamp = timestamp
        self.metadata = metadata or {}

class WorkflowStep:
    """Step in a learned workflow"""
    def __init__(
        self,
        tool: str,
        args: Dict[str, Any],
        description: str
    ):
        self.tool = tool
        self.args = args
        self.description = description

class Workflow:
    """Learned workflow sequence"""
    def __init__(
        self,
        name: str,
        description: str,
        steps: List[WorkflowStep],
        success_count: int = 0
    ):
        self.name = name
        self.description = description
        self.steps = steps
        self.success_count = success_count

class EnhancedMemorySystem:
    """
    Enhanced memory system with BGE-M3 embeddings and workflow learning.
    """
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.setup_stores()
        self.load_embedding_model()
        
    def setup_stores(self):
        """Initialize memory stores"""
        # Semantic store (ChromaDB)
        self.semantic_store = chromadb.Client(
            Settings(
                persist_directory=str(self.config.semantic_store_path)
            )
        )
        self.semantic_collection = self.semantic_store.get_or_create_collection(
            name="semantic_memories",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Episodic store (SQLite)
        self.episodic_db = sqlite3.connect(self.config.episodic_db_path)
        self.setup_tables()
        
        logger.info(
            "Memory stores initialized",
            semantic_path=str(self.config.semantic_store_path),
            episodic_path=str(self.config.episodic_db_path)
        )
        
    def setup_tables(self):
        """Create database tables"""
        with self.episodic_db:
            # Episodic memories
            self.episodic_db.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memories (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    relevance_score REAL DEFAULT 1.0
                )
            """)
            
            # Workflows
            self.episodic_db.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0
                )
            """)
            
    def load_embedding_model(self):
        """Initialize BGE-M3 embedding model"""
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.embedding_model)
        self.model = AutoModel.from_pretrained(self.config.embedding_model)
        
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")
            
        logger.info(
            "Loaded embedding model",
            model=self.config.embedding_model,
            device=self.model.device
        )
        
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using BGE-M3.
        Args:
            texts: List of texts to embed
        Returns:
            List of embedding vectors
        """
        # Tokenize and encode
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        
        if torch.cuda.is_available():
            encoded = {k: v.to("cuda") for k, v in encoded.items()}
            
        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**encoded)
            embeddings = outputs.last_hidden_state[:, 0].cpu().numpy()
            
        return embeddings.tolist()
        
    def store_semantic_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store semantic memory with BGE-M3 embedding.
        Args:
            content: Memory content
            metadata: Optional metadata
        Returns:
            Memory ID
        """
        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()
        
        # Generate embedding
        embedding = self.generate_embeddings([content])[0]
        
        # Store in ChromaDB
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.semantic_collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[memory_id]
        )
        
        return memory_id
        
    def query_semantic_memory(
        self,
        query: str,
        top_k: Optional[int] = None,
        multi_query: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Query semantic memories using BGE-M3.
        Args:
            query: Search query
            top_k: Number of results
            multi_query: Use multi-query strategy
        Returns:
            List of relevant memories
        """
        top_k = top_k or self.config.top_k
        multi_query = multi_query if multi_query is not None else self.config.multi_query
        
        if multi_query:
            # Generate multiple query variations
            queries = [
                query,
                f"context: {query}",
                f"remember: {query}",
                f"similar to: {query}"
            ]
            embeddings = self.generate_embeddings(queries)
            
            # Combine results
            all_results = []
            for embedding in embeddings:
                results = self.semantic_collection.query(
                    query_embeddings=[embedding],
                    n_results=top_k
                )
                all_results.extend(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                ))
                
            # Sort and deduplicate
            all_results.sort(key=lambda x: x[2])
            seen = set()
            final_results = []
            for doc, meta, dist in all_results:
                if doc not in seen:
                    seen.add(doc)
                    final_results.append({
                        "content": doc,
                        "metadata": meta,
                        "relevance": 1 - dist
                    })
                    if len(final_results) >= top_k:
                        break
                        
            return final_results
            
        else:
            # Single query
            embedding = self.generate_embeddings([query])[0]
            results = self.semantic_collection.query(
                query_embeddings=[embedding],
                n_results=top_k
            )
            
            return [{
                "content": doc,
                "metadata": meta,
                "relevance": 1 - dist
            } for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )]
            
    def store_episodic_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store episodic memory.
        Args:
            content: Memory content
            metadata: Optional metadata
        Returns:
            Memory ID
        """
        with self.episodic_db:
            cursor = self.episodic_db.execute(
                """
                INSERT INTO episodic_memories (content, timestamp, metadata)
                VALUES (?, ?, ?)
                """,
                (
                    content,
                    datetime.now().isoformat(),
                    json.dumps(metadata or {})
                )
            )
            return cursor.lastrowid
            
    def update_memory_relevance(self, memory_id: int, relevance: float):
        """Update episodic memory relevance score"""
        with self.episodic_db:
            self.episodic_db.execute(
                """
                UPDATE episodic_memories 
                SET relevance_score = ?
                WHERE id = ?
                """,
                (relevance, memory_id)
            )
            
    def cleanup_episodic_memories(self, threshold: float = 0.3):
        """Remove low-relevance episodic memories"""
        with self.episodic_db:
            self.episodic_db.execute(
                """
                DELETE FROM episodic_memories
                WHERE relevance_score < ?
                """,
                (threshold,)
            )
            
    def record_workflow(
        self,
        steps: List[Dict[str, Any]],
        outcome: str
    ):
        """
        Record workflow for learning.
        Args:
            steps: List of executed steps
            outcome: Execution outcome
        """
        # Extract key workflow information
        workflow_key = tuple(
            (step["tool"], tuple(sorted(step["args"].items())))
            for step in steps
        )
        
        with self.episodic_db:
            cursor = self.episodic_db.execute(
                """
                SELECT id, success_count, steps 
                FROM workflows
                WHERE name = ?
                """,
                (str(workflow_key),)
            )
            result = cursor.fetchone()
            
            if result:
                # Update existing workflow
                workflow_id, success_count, stored_steps = result
                if outcome == "success":
                    new_count = success_count + 1
                    self.episodic_db.execute(
                        """
                        UPDATE workflows
                        SET success_count = ?
                        WHERE id = ?
                        """,
                        (new_count, workflow_id)
                    )
            else:
                # Store new workflow
                self.episodic_db.execute(
                    """
                    INSERT INTO workflows (name, description, steps, success_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        str(workflow_key),
                        f"Workflow with {len(steps)} steps",
                        json.dumps(steps),
                        1 if outcome == "success" else 0
                    )
                )
                
    def get_learned_workflows(
        self,
        min_success: Optional[int] = None
    ) -> List[Workflow]:
        """
        Get learned workflows.
        Args:
            min_success: Minimum success count filter
        Returns:
            List of workflows
        """
        min_success = min_success or self.config.workflow_threshold
        
        with self.episodic_db:
            cursor = self.episodic_db.execute(
                """
                SELECT name, description, steps, success_count
                FROM workflows
                WHERE success_count >= ?
                ORDER BY success_count DESC
                """,
                (min_success,)
            )
            
            workflows = []
            for name, desc, steps_json, count in cursor:
                steps = json.loads(steps_json)
                workflow_steps = [
                    WorkflowStep(
                        tool=step["tool"],
                        args=step["args"],
                        description=step.get("description", "")
                    )
                    for step in steps
                ]
                
                workflows.append(Workflow(
                    name=name,
                    description=desc,
                    steps=workflow_steps,
                    success_count=count
                ))
                
            return workflows