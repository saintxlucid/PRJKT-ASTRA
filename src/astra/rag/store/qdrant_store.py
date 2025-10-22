"""
Hardened Qdrant vector store with idempotent upserts and HNSW tuning.

Features:
1. Idempotent upserts with SHA256 checksum tracking
2. Optimized HNSW parameters for performance/quality tradeoff 
3. Circuit breakers for backend protection
4. Consistent hash sharding for caching
5. Read replica support for scaling
"""
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import json
import time
from pathlib import Path
import structlog
from functools import partial
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from qdrant_client import QdrantClient, models as qm
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from astra.cache import ConsistentHashRing, Cache

logger = structlog.get_logger(__name__)

class CircuitBreaker:
    """Circuit breaker for backend protection."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 5.0
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            reset_timeout: Seconds before resetting to closed
            half_open_timeout: Seconds to wait in half-open
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"
        
    def record_failure(self):
        """Record a failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("circuit_opened",
                         failures=self.failure_count)
                         
    def record_success(self):
        """Record success and potentially close circuit."""
        self.failure_count = 0
        if self.state == "half-open":
            self.state = "closed"
            logger.info("circuit_closed")
            
    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        now = time.time()
        
        if self.state == "closed":
            return True
            
        if self.state == "open":
            # Check if enough time has passed
            if now - self.last_failure_time >= self.reset_timeout:
                self.state = "half-open"
                logger.info("circuit_half_open")
                return True
            return False
            
        if self.state == "half-open":
            # Only allow one request per half_open_timeout
            if now - self.last_failure_time >= self.half_open_timeout:
                return True
            return False
            
        return True

class QdrantStore:
    """
    Hardened Qdrant vector store with advanced features.
    """
    
    def __init__(
        self,
        hosts: List[str],
        collection: str,
        dim: int = 768,
        distance: Distance = Distance.COSINE,
        read_only: bool = False,
        cache_size: int = 10000,
        num_shards: int = 3,
        circuit_breaker_config: Optional[Dict] = None,
        prefer_grpc: bool = True
    ):
        """Initialize store with replicas.
        
        Args:
            hosts: List of Qdrant host URLs
            collection: Collection name
            dim: Vector dimension
            distance: Distance metric
            read_only: Whether to allow writes
            cache_size: Max cached items per shard
            num_shards: Number of cache shards
            circuit_breaker_config: Circuit breaker settings
            prefer_grpc: Whether to prefer gRPC over HTTP
        """
        self.logger = logger.bind(component="qdrant_store")
        
        # Connect to hosts
        self.clients = []
        for host in hosts:
            try:
                client = QdrantClient(
                    url=host,
                    prefer_grpc=prefer_grpc,
                    timeout=10.0
                )
                self.clients.append(client)
                self.logger.info("connected_to_host", host=host)
            except Exception as e:
                self.logger.error("host_connection_failed",
                                host=host,
                                error=str(e))
                
        if not self.clients:
            raise RuntimeError("No Qdrant hosts available")
            
        # Initialize collection
        self.collection = collection
        self.dim = dim
        self.distance = distance
        self.read_only = read_only
        
        try:
            self._init_collection()
        except Exception as e:
            self.logger.error("collection_init_failed",
                            error=str(e))
            raise
            
        # Setup cache sharding
        self.cache = ConsistentHashRing(num_shards=num_shards)
        for i in range(num_shards):
            self.cache.add_node(
                f"shard_{i}",
                Cache(maxsize=cache_size)
            )
            
        # Setup circuit breaker
        if circuit_breaker_config is None:
            circuit_breaker_config = {}
        self.circuit_breaker = CircuitBreaker(
            **circuit_breaker_config
        )
        
        # Setup thread pool for parallel ops
        self.thread_pool = ThreadPoolExecutor(
            max_workers=min(32, len(self.clients) * 4)
        )
        
        # Track document checksums
        self.checksums = {}
        
    def _init_collection(self):
        """Initialize Qdrant collection with optimized settings."""
        # HNSW config optimized for performance/quality
        hnsw_config = qm.HnswConfigDiff(
            m=32,  # Higher connectivity, better recall
            ef_construct=256,  # Higher accuracy during index
            ef_runtime=128,  # Better recall during search
            on_disk=True  # Enable on-disk storage
        )
        
        # Optimize for write vs read
        write_mode = "roi" if self.read_only else "latency"
        
        # Create collection if needed
        for client in self.clients:
            try:
                collections = client.get_collections()
                exists = any(c.name == self.collection
                           for c in collections.collections)
                           
                if not exists:
                    client.create_collection(
                        collection_name=self.collection,
                        vectors_config=VectorParams(
                            size=self.dim,
                            distance=self.distance,
                            hnsw_config=hnsw_config,
                            on_disk=True
                        ),
                        optimizers_config=models.OptimizersConfigDiff(
                            deleted_threshold=0.2,
                            vacuum_min_vector_number=1000,
                            default_segment_number=2,
                            memmap_threshold=10000,
                            indexing_threshold=20000,
                            flush_interval_sec=30,
                            max_optimization_threads=2
                        ),
                        write_consistency_factor=2,
                        on_disk_payload=True,
                        timeout=30
                    )
                    
                    self.logger.info("collection_created",
                                   name=self.collection)
                                   
            except Exception as e:
                self.logger.error("collection_init_failed",
                                host=client._client.hosts,
                                error=str(e))
                raise
                
    def _get_checksum(self, payload: Dict) -> str:
        """Generate SHA256 checksum of payload."""
        # Sort keys for consistent hash
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(
            serialized.encode()
        ).hexdigest()
        
    async def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict]
    ) -> bool:
        """
        Idempotent upsert of vectors and payloads.
        
        Args:
            ids: List of unique IDs
            vectors: List of vectors to store
            payloads: List of payload dicts
            
        Returns:
            bool indicating success
        """
        if self.read_only:
            self.logger.warning("write_rejected_read_only")
            return False
            
        if not self.circuit_breaker.allow_request():
            self.logger.warning("write_rejected_circuit_open")
            return False
            
        try:
            # Check if changed
            changed_idx = []
            for i, (id_, payload) in enumerate(zip(ids, payloads)):
                checksum = self._get_checksum(payload)
                if id_ not in self.checksums or self.checksums[id_] != checksum:
                    changed_idx.append(i)
                    self.checksums[id_] = checksum
                    
            if not changed_idx:
                return True
                
            # Prepare points for changed docs
            points = []
            for i in changed_idx:
                points.append(
                    models.PointStruct(
                        id=ids[i],
                        vector=vectors[i],
                        payload=payloads[i]
                    )
                )
                
            # Parallel upsert to all replicas
            tasks = []
            for client in self.clients:
                task = asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    partial(
                        client.upsert,
                        collection_name=self.collection,
                        points=points,
                        wait=True
                    )
                )
                tasks.append(task)
                
            # Wait for completion
            await asyncio.gather(*tasks)
            
            self.circuit_breaker.record_success()
            self.logger.debug("upsert_complete",
                            num_points=len(points))
            return True
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.logger.error("upsert_failed", error=str(e))
            return False
            
    async def search(
        self,
        vector: List[float],
        k: int = 10,
        filter: Optional[Dict] = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        score_threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Search for similar vectors with caching.
        
        Args:
            vector: Query vector
            k: Number of results
            filter: Optional filters
            with_payload: Include payloads
            with_vectors: Include vectors
            score_threshold: Minimum score threshold
            
        Returns:
            List of search results
        """
        if not self.circuit_breaker.allow_request():
            self.logger.warning("search_rejected_circuit_open")
            return []
            
        # Generate cache key
        key_parts = [
            str(vector),
            str(k),
            str(filter),
            str(with_payload),
            str(with_vectors),
            str(score_threshold)
        ]
        cache_key = hashlib.md5(
            "".join(key_parts).encode()
        ).hexdigest()
        
        # Check cache
        shard = self.cache.get_node(cache_key)
        cached = shard.get(cache_key)
        if cached is not None:
            return cached
            
        try:
            # Round-robin between clients
            client = self.clients[
                hash(cache_key) % len(self.clients)
            ]
            
            results = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                partial(
                    client.search,
                    collection_name=self.collection,
                    query_vector=vector,
                    query_filter=filter,
                    limit=k,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold
                )
            )
            
            # Convert to dicts
            results = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                    "vector": hit.vector if with_vectors else None
                }
                for hit in results
            ]
            
            # Cache results
            shard.set(cache_key, results)
            
            self.circuit_breaker.record_success()
            return results
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.logger.error("search_failed", error=str(e))
            return []
            
    async def get_nearest(
        self,
        ids: List[str],
        k: int = 10
    ) -> List[Dict]:
        """
        Get nearest neighbors for existing points.
        
        Args:
            ids: List of point IDs
            k: Number of neighbors per point
            
        Returns:
            List of nearest neighbors per ID
        """
        if not self.circuit_breaker.allow_request():
            self.logger.warning("recommend_rejected_circuit_open")
            return []
            
        try:
            client = self.clients[0]  # Use primary for consistency
            
            results = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                partial(
                    client.recommend,
                    collection_name=self.collection,
                    positive=ids,
                    limit=k,
                    with_payload=True
                )
            )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.logger.error("recommend_failed", error=str(e))
            return []
            
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        stats = {
            "num_points": 0,
            "num_vectors": 0,
            "points_deleted": 0
        }
        
        try:
            client = self.clients[0]
            collection_info = client.get_collection(
                collection_name=self.collection
            )
            
            if collection_info:
                stats.update({
                    "num_points": collection_info.points_count,
                    "num_vectors": collection_info.vectors_count,
                    "points_deleted": collection_info.status.deleted_count
                })
                
        except Exception as e:
            self.logger.error("stats_failed", error=str(e))
            
        return stats