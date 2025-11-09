"""
Memory Consolidation Job

Deduplicates similar memories and applies LLM summarization for
knowledge compression. Runs as async background job.

Usage:
    python scripts/consolidate_memories.py --threshold 0.95 --batch 100

Args:
    --threshold: Similarity threshold for deduplication (default: 0.95)
    --batch: Batch size for processing (default: 100)
    --dry-run: Preview changes without applying
    
Environment Variables:
    ASTRA_VECTOR_STORE_PERSIST_DIRECTORY - ChromaDB path
    ASTRA_VECTOR_COLLECTION - Collection name
    ASTRA_LLM_BASE_URL - LLM server URL for summarization
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections import defaultdict
from typing import List, Dict, Any, Tuple

import chromadb
from chromadb.config import Settings
import httpx
import numpy as np
import structlog

logger = structlog.get_logger()

# Configuration
DB_PATH = os.getenv("ASTRA_VECTOR_STORE_PERSIST_DIRECTORY", "data/chromadb")
COLLECTION = os.getenv("ASTRA_VECTOR_COLLECTION", "astra_memories")
LLM_URL = os.getenv("ASTRA_LLM_BASE_URL", "http://localhost:8081/v1")


class ConsolidationEngine:
    """Memory consolidation with deduplication and summarization"""
    
    def __init__(self, collection_name: str, db_path: str, llm_url: str):
        self.collection_name = collection_name
        self.db_path = db_path
        self.llm_url = llm_url
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(allow_reset=False)
        )
        self.collection = self.client.get_collection(collection_name)
        self.http = httpx.AsyncClient(timeout=120.0)
        
    async def close(self):
        """Close HTTP client"""
        await self.http.aclose()
        
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        np_a = np.array(a)
        np_b = np.array(b)
        return float(np.dot(np_a, np_b) / (np.linalg.norm(np_a) * np.linalg.norm(np_b)))
    
    def find_duplicates(self, threshold: float = 0.95, batch: int = 100) -> Dict[str, List[str]]:
        """
        Find duplicate memories based on embedding similarity.
        
        Args:
            threshold: Similarity threshold (0.95 = 95% similar)
            batch: Processing batch size
            
        Returns:
            Dict mapping canonical ID -> list of duplicate IDs
        """
        print(f"Scanning collection for duplicates (threshold={threshold})...")
        
        # Get all items with embeddings
        all_data = self.collection.get(include=["embeddings", "documents", "metadatas"])
        ids = all_data["ids"]
        embeddings = all_data["embeddings"]
        docs = all_data["documents"]
        metas = all_data.get("metadatas", [{} for _ in ids])
        
        print(f"Loaded {len(ids)} memories")
        
        # Build similarity graph
        duplicates: Dict[str, List[str]] = defaultdict(list)
        processed = set()
        
        for i, (id1, emb1) in enumerate(zip(ids, embeddings)):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(ids)}")
            
            if id1 in processed:
                continue
                
            for j in range(i+1, len(ids)):
                id2 = ids[j]
                if id2 in processed:
                    continue
                    
                emb2 = embeddings[j]
                sim = self.cosine_similarity(emb1, emb2)
                
                if sim >= threshold:
                    duplicates[id1].append(id2)
                    processed.add(id2)
        
        # Filter out empty groups
        duplicates = {k: v for k, v in duplicates.items() if v}
        
        print(f"Found {len(duplicates)} duplicate groups covering {sum(len(v) for v in duplicates.values())} items")
        
        return duplicates
    
    async def summarize_with_llm(self, texts: List[str]) -> str:
        """
        Use LLM to generate consolidated summary of multiple texts.
        
        Args:
            texts: List of similar memory texts
            
        Returns:
            Consolidated summary
        """
        if len(texts) == 1:
            return texts[0]
        
        # Build prompt
        prompt = """You are a memory consolidation assistant. Given similar memories, create a single comprehensive summary that captures all unique information.

Memories to consolidate:
"""
        for i, text in enumerate(texts, 1):
            prompt += f"{i}. {text}\n"
        
        prompt += "\nProvide a concise consolidated summary:"
        
        # Call LLM
        try:
            response = await self.http.post(
                f"{self.llm_url}/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": 256,
                    "temperature": 0.3,
                    "stop": ["\n\n"]
                }
            )
            response.raise_for_status()
            data = response.json()
            summary = data["choices"][0]["text"].strip()
            return summary
        except Exception as e:
            logger.error("summarization_failed", error=str(e))
            # Fallback: concatenate with separator
            return " | ".join(texts)
    
    async def consolidate_group(self, canonical_id: str, duplicate_ids: List[str], dry_run: bool = False) -> Dict[str, Any]:
        """
        Consolidate a group of duplicate memories.
        
        Args:
            canonical_id: ID of the memory to keep
            duplicate_ids: IDs of duplicates to merge
            dry_run: If True, don't actually modify the database
            
        Returns:
            Consolidation result summary
        """
        # Get all items
        all_ids = [canonical_id] + duplicate_ids
        data = self.collection.get(ids=all_ids, include=["documents", "metadatas", "embeddings"])
        
        docs = data["documents"]
        metas = data.get("metadatas", [{} for _ in docs])
        emb = data["embeddings"][0]  # Use canonical embedding
        
        # Generate consolidated text
        summary = await self.summarize_with_llm(docs)
        
        # Merge metadata (collect unique values)
        merged_meta = {}
        for meta in metas:
            for k, v in meta.items():
                if k not in merged_meta:
                    merged_meta[k] = v
                elif merged_meta[k] != v:
                    # Handle conflicts by concatenating
                    if not isinstance(merged_meta[k], list):
                        merged_meta[k] = [merged_meta[k]]
                    if v not in merged_meta[k]:
                        merged_meta[k].append(v)
        
        # Add consolidation metadata
        merged_meta["consolidated_from"] = duplicate_ids
        merged_meta["consolidation_timestamp"] = int(time.time())
        
        if not dry_run:
            # Update canonical memory
            self.collection.update(
                ids=[canonical_id],
                documents=[summary],
                metadatas=[merged_meta],
                embeddings=[emb]
            )
            
            # Delete duplicates
            self.collection.delete(ids=duplicate_ids)
        
        return {
            "canonical_id": canonical_id,
            "merged_count": len(duplicate_ids),
            "original_texts": docs,
            "consolidated_text": summary,
            "dry_run": dry_run
        }
    
    async def run_consolidation(self, threshold: float = 0.95, batch: int = 100, dry_run: bool = False):
        """
        Main consolidation workflow.
        
        Args:
            threshold: Similarity threshold
            batch: Processing batch size
            dry_run: Preview mode
        """
        t0 = time.time()
        
        logger.info("consolidation_started", 
                    threshold=threshold,
                    batch=batch,
                    dry_run=dry_run)
        
        # Find duplicates
        duplicates = self.find_duplicates(threshold=threshold, batch=batch)
        
        if not duplicates:
            print("No duplicates found. Exiting.")
            return
        
        # Process each group
        results = []
        total_groups = len(duplicates)
        
        print(f"\nConsolidating {total_groups} duplicate groups...")
        
        for i, (canonical_id, duplicate_ids) in enumerate(duplicates.items(), 1):
            print(f"[{i}/{total_groups}] Processing group {canonical_id} ({len(duplicate_ids)} duplicates)")
            
            result = await self.consolidate_group(canonical_id, duplicate_ids, dry_run=dry_run)
            results.append(result)
            
            logger.info("group_consolidated",
                        group=i,
                        canonical=canonical_id,
                        merged=len(duplicate_ids))
        
        # Generate summary
        elapsed = time.time() - t0
        total_removed = sum(r["merged_count"] for r in results)
        
        summary = {
            "threshold": threshold,
            "total_groups": total_groups,
            "total_removed": total_removed,
            "duration_seconds": round(elapsed, 2),
            "dry_run": dry_run,
            "status": "completed"
        }
        
        # Save report
        report_path = f"data/logs/consolidation_report_{int(time.time())}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump({
                "summary": summary,
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*80)
        print("CONSOLIDATION COMPLETE" if not dry_run else "DRY RUN COMPLETE")
        print("="*80)
        print(json.dumps(summary, indent=2))
        print("="*80)
        print(f"\nReport saved to: {report_path}")
        
        if dry_run:
            print("\nThis was a dry run. No changes were made.")
            print("Run without --dry-run to apply consolidation.")
        
        logger.info("consolidation_completed", **summary)


async def main():
    """Main async entry point"""
    parser = argparse.ArgumentParser(description="Consolidate duplicate memories")
    parser.add_argument("--threshold", type=float, default=0.95, help="Similarity threshold")
    parser.add_argument("--batch", type=int, default=100, help="Batch size")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    args = parser.parse_args()
    
    engine = ConsolidationEngine(COLLECTION, DB_PATH, LLM_URL)
    
    try:
        await engine.run_consolidation(
            threshold=args.threshold,
            batch=args.batch,
            dry_run=args.dry_run
        )
    finally:
        await engine.close()


if __name__ == "__main__":
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )
    
    asyncio.run(main())
