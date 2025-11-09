"""
Qdrant vector store implementation.
"""
from typing import List, Optional, Dict, Any
import numpy as np
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from astra.embed.bge import BGEM3Embedder
from astra.rag.document import Document

class QdrantStore:
    """Qdrant-backed vector store."""
    
    def __init__(
        self,
        embedder: BGEM3Embedder,
        url: str = "http://localhost:6333",
        collection_name: str = "documents",
        distance: str = "Cosine",
        batch_size: int = 100,
        cache_dir: Optional[str] = None,
        vector_size: int = 1024,
        **kwargs
    ):
        """Initialize store."""
        self.embedder = embedder
        self.collection_name = collection_name
        self.batch_size = batch_size
        
        # Set up client
        self.client = QdrantClient(
            url=url,
            **kwargs.get("init_params", {})
        )
        
        # Create collection if needed
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                self._ensure_collection(
                    vector_size=vector_size,
                    distance=distance
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
        
        # Set up cache if enabled
        self.cache_dir = None
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
    def _ensure_collection(
        self,
        vector_size: int,
        distance: str
    ):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections()
        exists = any(
            c.name == self.collection_name
            for c in collections.collections
        )
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            
    def add_documents(
        self,
        documents: List[Document]
    ):
        """Add documents to store."""
        # Prepare points
        points = []
        for doc in documents:
            # Get embedding
            vector = self.embedder.embed_text(doc.text)
            
            # Create point
            point = rest.PointStruct(
                id=doc.id,
                vector=vector.tolist(),
                payload={
                    "text": doc.text,
                    **doc.metadata
                }
            )
            points.append(point)
            
            # Batch insert if needed
            if len(points) >= self.batch_size:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                points = []
                
        # Insert remaining points
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
    def search(
        self,
        query: str,
        k: int = 5
    ) -> List[Document]:
        """Search for similar documents."""
        # Get query embedding
        vector = self.embedder.embed_query(query)
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector.tolist(),
            limit=k
        )
        
        # Convert to documents
        documents = []
        for hit in results:
            doc = Document(
                id=str(hit.id),
                text=hit.payload["text"],
                metadata={
                    k: v for k, v in hit.payload.items()
                    if k != "text"
                }
            )
            documents.append(doc)
            
        return documents