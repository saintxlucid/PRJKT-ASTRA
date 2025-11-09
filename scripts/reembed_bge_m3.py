"""
BGE-M3 Re-embedding Migration Script

Migrates existing ChromaDB embeddings from all-MiniLM-L6-v2 to BGE-M3
for better multilingual support (English + Egyptian Arabic).

Usage:
    python scripts/reembed_bge_m3.py
    
Environment Variables:
    ASTRA_VECTOR_STORE_PERSIST_DIRECTORY - ChromaDB path (default: data/chromadb)
    ASTRA_VECTOR_COLLECTION - Source collection (default: astra_memories)
    ASTRA_VECTOR_COLLECTION_NEW - Destination collection (default: astra_memories_m3)
    ASTRA_EMBEDDINGS_MODEL_PATH - Model name or path (default: BAAI/bge-m3)
    ASTRA_EMBEDDINGS_BATCH - Batch size (default: 64)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
from typing import List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger()

# Configuration
DB_PATH = os.getenv("ASTRA_VECTOR_STORE_PERSIST_DIRECTORY", "data/chromadb")
SRC_COLLECTION = os.getenv("ASTRA_VECTOR_COLLECTION", "astra_memories")
DST_COLLECTION = os.getenv("ASTRA_VECTOR_COLLECTION_NEW", "astra_memories_m3")
MODEL_PATH = os.getenv("ASTRA_EMBEDDINGS_MODEL_PATH") or "BAAI/bge-m3"
BATCH = int(os.getenv("ASTRA_EMBEDDINGS_BATCH", "64"))

# Notes: BGE-M3 is multilingual and strong for Arabic/English.
# Dimensions: 1024 (vs 384 for all-MiniLM-L6-v2)
# Languages: 100+ including Arabic, English, French, etc.


class BGEEmbedder:
    """BGE-M3 embedder with normalization and memory optimization"""
    
    def __init__(self, model_name: str, device: str = "cpu"):
        logger.info("loading_bge_model", model=model_name, device=device)
        # Load with memory-efficient settings for CPU
        self.model = SentenceTransformer(
            model_name, 
            trust_remote_code=True,
            device=device,
            # Memory optimizations
            model_kwargs={
                "torch_dtype": "auto",  # Use smaller precision if possible
                "low_cpu_mem_usage": True,  # Enable memory-efficient loading
            }
        )
        logger.info("model_loaded", dimensions=self.model.get_sentence_embedding_dimension())
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors (normalized)
        """
        return self.model.encode(
            texts,
            batch_size=BATCH,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=False,
        ).tolist()


def main():
    """Main migration function"""
    t0 = time.time()
    
    logger.info("migration_started", 
                source=SRC_COLLECTION,
                destination=DST_COLLECTION,
                model=MODEL_PATH)
    
    # Connect to ChromaDB
    print(f"Connecting to ChromaDB at {DB_PATH}...")
    client = chromadb.PersistentClient(
        path=DB_PATH,
        settings=Settings(allow_reset=False)
    )
    
    # Get collections
    src = client.get_or_create_collection(SRC_COLLECTION)
    dst = client.get_or_create_collection(DST_COLLECTION)
    
    # Initialize embedder
    print(f"Loading BGE-M3 model from {MODEL_PATH}...")
    embedder = BGEEmbedder(MODEL_PATH)
    
    # Stream through all points to avoid OOM
    print("Scanning source collection...")
    all_ids: List[str] = []
    cursor = 0
    page = 1000
    
    while True:
        # ChromaDB 0.5.x - use documents to get IDs (no "ids" in include)
        batch = src.get(limit=page, offset=cursor, include=["documents"])
        ids = batch.get("ids", [])
        if not ids:
            break
        all_ids.extend(ids)
        cursor += len(ids)
        logger.info("scanned_batch", offset=cursor, total=len(all_ids))
        if len(ids) < page:
            break
    
    print(f"Found {len(all_ids)} items to re-embed")
    
    if len(all_ids) == 0:
        print("No items found in source collection. Exiting.")
        return
    
    # Re-embed in chunks
    CHUNK = 256
    total_processed = 0
    
    for i in range(0, len(all_ids), CHUNK):
        chunk_start = time.time()
        ids = all_ids[i:i+CHUNK]
        
        # Get original data
        data = src.get(ids=ids, include=["documents", "metadatas"])
        docs = data["documents"]
        metas = data.get("metadatas", [{} for _ in docs])
        
        # Generate new embeddings
        print(f"Embedding batch {i//CHUNK + 1}/{(len(all_ids)-1)//CHUNK + 1}...")
        emb = embedder.encode(docs)
        
        # Write to new collection preserving IDs
        dst.upsert(
            ids=ids,
            documents=docs,
            metadatas=metas,
            embeddings=emb
        )
        
        total_processed += len(ids)
        chunk_time = time.time() - chunk_start
        items_per_sec = len(ids) / chunk_time if chunk_time > 0 else 0
        
        print(f"Progress: {total_processed}/{len(all_ids)} "
              f"({100*total_processed/len(all_ids):.1f}%) "
              f"[{items_per_sec:.1f} items/sec]")
        
        logger.info("chunk_processed",
                    chunk=i//CHUNK + 1,
                    processed=total_processed,
                    total=len(all_ids),
                    items_per_sec=round(items_per_sec, 2))
    
    # Generate summary
    elapsed = time.time() - t0
    summary = {
        "source_collection": SRC_COLLECTION,
        "destination_collection": DST_COLLECTION,
        "model": MODEL_PATH,
        "total_items": len(all_ids),
        "duration_seconds": round(elapsed, 2),
        "items_per_second": round(len(all_ids) / elapsed, 2) if elapsed > 0 else 0,
        "embedding_dimension": 1024,  # BGE-M3
        "status": "completed"
    }
    
    # Save summary
    summary_path = f"data/logs/reembed_summary_{int(time.time())}.json"
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "="*80)
    print("MIGRATION COMPLETE")
    print("="*80)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("="*80)
    print(f"\nSummary saved to: {summary_path}")
    print(f"\nNext steps:")
    print(f"1. Verify new collection: {DST_COLLECTION}")
    print(f"2. Test semantic search quality")
    print(f"3. Update config to use: {DST_COLLECTION}")
    print(f"4. Optional: Delete old collection: {SRC_COLLECTION}")
    
    logger.info("migration_completed", **summary)


if __name__ == "__main__":
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )
    
    try:
        main()
    except Exception as e:
        print("\n" + "="*80, file=sys.stderr)
        print("ERROR: Re-embedding failed", file=sys.stderr)
        print("="*80, file=sys.stderr)
        traceback.print_exc()
        print("\nCommon issues:", file=sys.stderr)
        print("  1. Disk space full (check C: and X: drives)", file=sys.stderr)
        print("  2. ChromaDB collection not found", file=sys.stderr)
        print("  3. Missing dependencies (chromadb, sentence-transformers, torch)", file=sys.stderr)
        print("  4. Model download failed (network/cache permissions)", file=sys.stderr)
        sys.exit(1)
