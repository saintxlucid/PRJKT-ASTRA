"""Memory engine core implementation"""
import os
import time
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, cast
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from chromadb.api.types import Document, Documents, QueryResult, GetResult
from chromadb.api.models.Collection import Collection
from typing import TypeVar, Type, Any, Dict

ChromaClient = TypeVar('ChromaClient', bound='chromadb.ClientAPI')
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

from .memory_types import (
    MemoryResult, MemoryItem, ChromaResults, to_include, process_results,
    safe_get_result_value, safe_get_metadata_value, 
    safe_format_memory_result, safe_format_memory_item
)

logger = logging.getLogger("astra.memory")

@dataclass
class NutritionScore:
    """Data quality and relevance scoring"""
    quality: float  # Cleanliness, structure
    relevance: float  # Topic relevance
    insight: float  # Novel information
    emotional: float  # Emotional resonance
    essence: float  # Core truth alignment
    
    def total(self) -> float:
        """Calculate total nutrition score"""
        weights = {
            'quality': 0.2,
            'relevance': 0.2,
            'insight': 0.2, 
            'emotional': 0.2,
            'essence': 0.2
        }
        return float(sum(float(getattr(self, k)) * float(v) for k,v in weights.items()))

import time
from tenacity import retry, stop_after_attempt, wait_exponential

class MemoryStore:
    """ASTRA's memory store implementation"""
    
    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        
        # Initialize store components
        self.client: Any = None  # Will be chromadb.Client
        self.embedder: Optional[SentenceTransformer] = None
        self.semantic: Optional[Collection] = None
        self.episodic: Optional[Collection] = None
        self.procedural: Optional[Collection] = None
        
        self._initialize_store()
        logger.info(f"Memory store initialized at {persist_dir}")
        
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _initialize_store(self) -> None:
        """Initialize ChromaDB with retry logic"""
        try:
            # Initialize ChromaDB
            self.client = chromadb.Client(Settings(
                persist_directory=self.persist_dir,
                anonymized_telemetry=False
            ))
            
            # Test connection with heartbeat
            try:
                self.client.heartbeat()
            except Exception as e:
                logger.warning(f"Heartbeat check failed: {e}")
            
            # Initialize embeddings model
            self.embedder = SentenceTransformer('all-mpnet-base-v2')
            
            # Create collections with validation
            self.semantic = self._get_or_create_collection("semantic_memories")
            self.episodic = self._get_or_create_collection("episodic_memories")
            self.procedural = self._get_or_create_collection("procedural_memories")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory store: {e}")
            raise
            
    def _get_or_create_collection(self, name: str) -> Collection:
        """Get or create a collection with validation"""
        if not self.client:
            raise RuntimeError("ChromaDB client not initialized")
            
        try:
            # Get or create collection
            coll = self.client.get_or_create_collection(name)
            
            # Validate collection
            try:
                count = coll.count()
                if count < 0:
                    raise ValueError(f"Invalid collection count: {count}")
            except Exception as e:
                logger.warning(f"Collection validation warning for {name}: {e}")
            
            return cast(Collection, coll)
            
        except Exception as e:
            logger.error(f"Failed to initialize collection {name}: {e}")
            raise
            
    def persist(self) -> None:
        """Persist ChromaDB state to disk"""
        if not self.client:
            logger.warning("No ChromaDB client to persist")
            return
            
        try:
            logger.info("Persisting memory store...")
            # Use _raw_api for direct access to persistence methods
            raw_client = getattr(self.client, '_raw_api', self.client)
            if hasattr(raw_client, 'persist'):
                raw_client.persist()
            logger.info("Memory store persisted successfully")
        except Exception as e:
            logger.error(f"Failed to persist memory store: {e}")
            raise

    def calculate_nutrition(self, content: str, metadata: Dict[str, Any]) -> NutritionScore:
        """Calculate nutrition scores for incoming data"""
        importance = metadata.get("importance", 0.5)
        
        # Calculate sub-scores using enhanced metrics
        words = [w.strip(".,!?:;()[]\"'").lower() for w in content.split()]
        uniq = len(set(words))
        novelty = min(1.0, uniq / max(1, min(200, len(words))))
        
        # Emotional density from lexicon
        EMO_LEXICON = set(["love","hate","pain","cry","joy","rage","sacred","burn","fire",
                          "night","lost","home","bless","tears","fear","hope","dream"])
        emo_density = min(1.0, sum(1 for w in words if w in EMO_LEXICON) / 8.0)
        
        return NutritionScore(
            quality=0.85,  # Based on text quality
            relevance=0.90 * importance,  # Topic relevance 
            insight=novelty * 0.90,  # Information novelty
            emotional=max(0.80, emo_density),  # Emotional resonance
            essence=0.85 * importance  # Core truth alignment
        )
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        if not self.embedder:
            raise RuntimeError("Embeddings model not initialized")
        return self.embedder.encode(text).tolist()

class MemoryEngine:
    """Enhanced MemoryEngine for ASTRA core"""
    
    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}
        self.store: Optional[MemoryStore] = None
        self.connected = False
        
        # Default config
        self.persist_dir = self.cfg.get("persist_dir", "./data/astra_memories")
        self.min_nutrition = self.cfg.get("min_nutrition", 0.5)
        
    async def connect(self) -> None:
        """Initialize memory store connection"""
        try:
            self.store = MemoryStore(persist_dir=self.persist_dir)
            self.connected = True
            logger.info("Memory store connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect memory store: {e}")
            raise
    
    def info(self) -> Dict[str, Any]:
        """Get memory system info"""
        if not self.store:
            return {
                "connected": False,
                "persist_dir": self.persist_dir,
                "memory_counts": {"semantic": 0, "episodic": 0, "procedural": 0},
                "min_nutrition": self.min_nutrition
            }

        if not all([self.store.semantic, self.store.episodic, self.store.procedural]):
            logger.warning("Some collections not initialized")
            return {
                "connected": self.connected,
                "persist_dir": self.persist_dir,
                "memory_counts": {"semantic": 0, "episodic": 0, "procedural": 0},
                "min_nutrition": self.min_nutrition
            }
            
        collections = {
            "semantic": self.store.semantic,
            "episodic": self.store.episodic,
            "procedural": self.store.procedural
        }
        
        counts = {}
        for name, coll in collections.items():
            try:
                if coll:
                    counts[name] = coll.count()
                else:
                    counts[name] = 0
            except Exception as e:
                logger.error(f"Failed to get count for {name}: {e}")
                counts[name] = -1
                
        return {
            "connected": self.connected,
            "persist_dir": self.persist_dir,
            "memory_counts": counts,
            "min_nutrition": self.min_nutrition
        }
        
    async def ingest(self, content: str, memory_type: str = "semantic", **metadata: Any) -> Dict[str, Any]:
        """Ingest new memory with nutrition scoring"""
        if not self.connected or not self.store:
            raise RuntimeError("Memory store not connected")

        if not self.store.semantic:
            raise RuntimeError("Semantic collection not initialized")
            
        if memory_type == "semantic":
            # Calculate nutrition
            nutrition = self.store.calculate_nutrition(content, metadata)
            
            # Generate embedding
            embedding = self.store.embed_text(content)
            
            # Create memory ID
            memory_id = f"sem_{len(content)}_{int(datetime.now().timestamp())}"
            
            # Store in ChromaDB
            try:
                self.store.semantic.add(
                    documents=[content],
                    embeddings=embedding,
                    metadatas=[{
                        **metadata,
                        "nutrition": nutrition.total(),
                        "created_at": datetime.now().isoformat()
                    }],
                    ids=[memory_id]
                )
            except Exception as e:
                logger.error(f"Failed to add memory {memory_id}: {e}")
                raise
            
            logger.info(f"Stored semantic memory {memory_id} with nutrition {nutrition.total():.2f}")
            
            return {
                "id": memory_id,
                "type": memory_type,
                "nutrition": nutrition.total(),
                "metadata": metadata
            }
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")
            
    async def search(self, query: str, memory_type: str = "semantic", limit: int = 5) -> List[MemoryResult]:
        """Search memories with nutrition filtering"""
        if not self.connected or not self.store:
            raise RuntimeError("Memory store not connected")

        if not self.store.semantic:
            raise RuntimeError("Semantic collection not initialized")
            
        if memory_type == "semantic":
            # Generate query embedding
            query_embedding = self.store.embed_text(query)
            
            # Search with nutrition filter
            try:
                results = self.store.semantic.query(
                    query_embeddings=query_embedding,
                    n_results=limit,
                    include=to_include()
                )
            except Exception as e:
                logger.error(f"Failed to query semantic memories: {e}")
                return []
            
            if not results:
                return []
                
            # Format results safely
            safe_results = process_results(results)
            memories = []
            
            for i in range(len(safe_results['ids'])):
                memory = safe_format_memory_result(
                    id_=safe_results['ids'][i],
                    content=safe_get_result_value(safe_results, 'documents', i),
                    metadata=safe_get_result_value(safe_results, 'metadatas', i),
                    energy=safe_get_metadata_value(
                        safe_get_result_value(safe_results, 'metadatas', i),
                        'nutrition'
                    )
                )
                memories.append(memory)
                
            return memories
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")
    
    async def reflect(self, memory_type: str = "semantic", window: int = 100) -> Dict[str, Any]:
        """Analyze recent memories for patterns and insights"""
        if not self.connected or not self.store:
            raise RuntimeError("Memory store not connected")

        if not self.store.semantic:
            raise RuntimeError("Semantic collection not initialized")
            
        if memory_type == "semantic":
            # Get recent memories
            try:
                results = self.store.semantic.get(
                    limit=window,
                    include=to_include()
                )
            except Exception as e:
                logger.error(f"Failed to get recent memories: {e}")
                return {"insights": [], "error": str(e)}
            
            if not results:
                return {"insights": []}
                
            safe_results = process_results(results)
            if not safe_results['ids']:
                return {"insights": []}
                
            insights: List[Dict[str, Any]] = []
            time_range: Dict[str, Optional[str]] = {
                "start": None,
                "end": None
            }
            
            # 1. Nutrition analysis
            nutrition_scores: List[float] = []
            for i in range(len(safe_results['ids'])):
                meta = safe_get_result_value(safe_results, 'metadatas', i, {})
                score = safe_get_metadata_value(meta, 'nutrition', 0.0)
                nutrition_scores.append(float(score))
            
            if nutrition_scores:
                avg_nutrition = sum(nutrition_scores) / len(nutrition_scores)
                insights.append({
                    "type": "nutrition",
                    "description": f"Average memory nutrition: {avg_nutrition:.2f}",
                    "value": avg_nutrition
                })
            
            # 2. Time analysis
            timestamps: List[datetime] = []
            for i in range(len(safe_results['ids'])):
                meta = safe_get_result_value(safe_results, 'metadatas', i, {})
                ts_str = safe_get_metadata_value(meta, 'created_at')
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(str(ts_str))
                        timestamps.append(ts)
                    except (ValueError, TypeError):
                        continue
                        
            if timestamps:
                newest = max(timestamps)
                oldest = min(timestamps)
                time_span = (newest - oldest).total_seconds()
                insights.append({
                    "type": "temporal",
                    "description": f"Memory span: {time_span/3600:.1f} hours",
                    "value": time_span
                })
                time_range = {
                    "start": oldest.isoformat(),
                    "end": newest.isoformat()
                }
            
            # 3. Content analysis 
            word_counts: List[int] = []
            for i in range(len(safe_results['ids'])):
                doc = safe_get_result_value(safe_results, 'documents', i)
                if doc:
                    word_counts.append(len(str(doc).split()))
                    
            if word_counts:
                avg_words = sum(word_counts) / len(word_counts)
                insights.append({
                    "type": "content",
                    "description": f"Average memory length: {avg_words:.1f} words",
                    "value": avg_words
                })
            
            return {
                "insights": insights,
                "memory_count": len(safe_results['ids']),
                "time_range": time_range,
                "status": "success"
            }
                
        else:
            raise ValueError(f"Unsupported memory type for reflection: {memory_type}")

    async def merge_memories(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Merge multiple memories with type safety"""
        if not self.connected or not self.store:
            raise RuntimeError("Memory store not connected")

        if not self.store.semantic:
            raise RuntimeError("Semantic collection not initialized")
            
        try:
            # Get memories safely
            try:
                results = self.store.semantic.get(
                    ids=memory_ids,
                    include=to_include()
                )
            except Exception as e:
                logger.error(f"Failed to retrieve memories: {e}")
                return {"error": f"Failed to retrieve memories: {str(e)}"}
            
            if not results:
                return {"error": "No memories found"}
                
            safe_results = process_results(results)
            if not safe_results['ids']:
                return {"error": "No memories found"}
                
            # Combine content
            merged_text = ""
            merged_meta: Dict[str, str | int | float | bool] = {
                "source_ids": ",".join(memory_ids),  # Convert list to string
                "merged_at": datetime.now().isoformat(),
                "nutrition": 0.0,
                "source_count": len(safe_results['ids'])
            }
            
            # Track nutrition
            nutrition_scores: List[float] = []
            
            # Merge content with metadata safely
            for i in range(len(safe_results['ids'])):
                doc = safe_get_result_value(safe_results, 'documents', i)
                meta = safe_get_result_value(safe_results, 'metadatas', i, {})
                
                if not doc:
                    continue
                    
                # Add separator
                if merged_text:
                    merged_text += "\n\n---\n\n"
                    
                # Add provenance marker
                source = safe_get_metadata_value(meta, 'source', 'unknown')
                created = safe_get_metadata_value(meta, 'created_at', 'unknown time')
                merged_text += f"[Memory from {source} at {created}]:\n"
                
                # Track nutrition
                score = safe_get_metadata_value(meta, 'nutrition')
                if score is not None:
                    nutrition_scores.append(float(score))
                
                # Add content
                merged_text += str(doc)
            
            # Calculate merged nutrition
            if nutrition_scores:
                merged_meta["nutrition"] = sum(nutrition_scores) / len(nutrition_scores)
            
            # Store merged version
            embedding = self.store.embed_text(merged_text)
            merged_id = f"merged_{int(time.time())}"
            
            self.store.semantic.add(
                documents=[merged_text],
                embeddings=embedding,
                metadatas=[merged_meta],
                ids=[merged_id]
            )
            
            return {
                "id": merged_id,
                "content": merged_text,
                "metadata": merged_meta,
                "status": "success"
            }
                
        except Exception as e:
            logger.error(f"Error merging memories: {e}")
            return {
                "error": str(e),
                "status": "error"
            }

    def ping(self) -> bool:
        """Check memory system health"""
        return self.connected
        
    def ingest_text(self, text: str, source: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous wrapper for memory ingestion"""
        meta = metadata or {}
        meta["source"] = source
        return asyncio.run(self.ingest(text, memory_type="semantic", **meta))
        
    def sample_high_energy(self, min_energy: float = 0.7, limit: int = 20) -> List[MemoryResult]:
        """Sample high-energy memories with type safety"""
        if not self.connected or not self.store:
            raise RuntimeError("Memory store not connected")

        if not self.store.semantic:
            raise RuntimeError("Semantic collection not initialized")
            
        try:
            # Query high-energy memories
            try:
                results = self.store.semantic.get(
                    limit=limit,
                    include=to_include()
                )
            except Exception as e:
                logger.error(f"Failed to get high-energy memories: {e}")
                return []
            
            if not results:
                return []
                
            safe_results = process_results(results)
            memories: List[MemoryResult] = []
            
            for i in range(len(safe_results['ids'])):
                memory = safe_format_memory_result(
                    id_=safe_results['ids'][i],
                    content=safe_get_result_value(safe_results, 'documents', i),
                    metadata=safe_get_result_value(safe_results, 'metadatas', i),
                    energy=safe_get_metadata_value(
                        safe_get_result_value(safe_results, 'metadatas', i),
                        'nutrition'
                    )
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error sampling high-energy memories: {e}")
            return []
            
    def merge_memories_sync(self, memory_ids: List[str], reason: str = "", note: str = "") -> Dict[str, Any]:
        """Synchronous wrapper for memory merging"""
        result = asyncio.run(self.merge_memories(memory_ids))
        if reason or note:
            if isinstance(result, dict) and "metadata" in result:
                result["metadata"]["merge_reason"] = reason
                result["metadata"]["merge_note"] = note
        return result
        
    async def close(self) -> None:
        """
        Persist/flush any backend state. Best-effort and idempotent.
        """
        if not self.connected:
            return
        try:
            # Chroma: persist to disk
            info_fn = getattr(self.store, "info", lambda: {})
            info: Dict[str, Any] = info_fn()
            
            if isinstance(info, dict) and info.get("type") == "chroma":
                client = getattr(self.store, "client", None)
                if client and hasattr(client, "persist"):
                    client.persist()
            logger.info("Memory engine closed successfully")
        except Exception as e:
            logger.exception("MemoryEngine close() persist failed: %s", e)
        finally:
            self.connected = False

    def export_manifest(self, output_path: str) -> Dict[str, Any]:
        """Export memory manifest to file with type safety"""
        if not self.connected or not self.store:
            raise RuntimeError("Memory store not connected")

        if not self.store.semantic:
            raise RuntimeError("Semantic collection not initialized")
            
        try:
            # Get all memories
            try:
                results = self.store.semantic.get(
                    include=to_include()
                )
            except Exception as e:
                logger.error(f"Failed to retrieve all memories: {e}")
                return {"error": f"Failed to retrieve memories: {str(e)}"}
            
            if not results:
                return {"error": "No memories found"}
                
            safe_results = process_results(results)
            if not safe_results['ids']:
                return {"error": "No memories found"}
                
            manifest = {
                "timestamp": datetime.now().isoformat(),
                "memory_count": len(safe_results['ids']),
                "items": []
            }
            
            items: List[MemoryItem] = []
            for i in range(len(safe_results['ids'])):
                item = safe_format_memory_item(
                    id_=safe_results['ids'][i],
                    content=safe_get_result_value(safe_results, 'documents', i),
                    metadata=safe_get_result_value(safe_results, 'metadatas', i)
                )
                items.append(item)
            
            manifest["items"] = items
            
            # Write manifest
            output_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                
            return {
                "path": output_path,
                "count": len(items),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error exporting manifest: {e}")
            return {
                "error": str(e),
                "status": "error"
            }