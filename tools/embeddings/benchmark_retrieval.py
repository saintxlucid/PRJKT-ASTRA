#!/usr/bin/env python3
"""
Benchmark retrieval quality (old embeddings vs BGE-M3).

Purpose:
- Validate 15-20% retrieval improvement claim
- Use standard benchmark queries
- Compare old embeddings (MiniLM) vs BGE-M3

Metrics:
- Precision@K (K=1,5,10): Relevant results in top-K
- Recall@K: Fraction of relevant results retrieved
- MRR (Mean Reciprocal Rank): Position of first relevant result
- NDCG@K: Normalized Discounted Cumulative Gain

Usage:
    python tools/embeddings/benchmark_retrieval.py \
        --old-collection data/memory \
        --new-collection data/memory_bge_m3 \
        --queries benchmark_queries.json
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

# ChromaDB
try:
    import chromadb
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb")
    sys.exit(1)


# Benchmark queries with ground truth
DEFAULT_QUERIES = [
    {
        "query": "How does ASTRA's memory signing work?",
        "relevant_docs": ["memory_signing.md", "security/tamper_detection.md"]
    },
    {
        "query": "What is the ASTRA Constitution?",
        "relevant_docs": ["ASTRA_CONSTITUTION.md", "docs/philosophy/*.md"]
    },
    {
        "query": "Explain the prompt guard system",
        "relevant_docs": ["security/prompt_guard.py", "prompt_injection_defense.md"]
    },
    {
        "query": "How does event sourcing work?",
        "relevant_docs": ["domain/events.py", "event_store_sqlite.py"]
    },
    {
        "query": "What is hexagonal architecture?",
        "relevant_docs": ["ARCHITECTURE.md", "domain/interfaces.py"]
    },
]


def load_queries(query_file: Path) -> List[Dict[str, Any]]:
    """Load benchmark queries from JSON file."""
    if query_file.exists():
        return json.loads(query_file.read_text())
    else:
        print(f"Using default queries (no file: {query_file})")
        return DEFAULT_QUERIES


def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Precision@K: Fraction of retrieved docs that are relevant."""
    retrieved_k = retrieved[:k]
    relevant_count = sum(1 for doc in retrieved_k if any(rel in doc for rel in relevant))
    return relevant_count / k if k > 0 else 0.0


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Recall@K: Fraction of relevant docs that are retrieved."""
    retrieved_k = retrieved[:k]
    relevant_count = sum(1 for doc in retrieved_k if any(rel in doc for rel in relevant))
    return relevant_count / len(relevant) if len(relevant) > 0 else 0.0


def mrr(retrieved: List[str], relevant: List[str]) -> float:
    """Mean Reciprocal Rank: 1 / position of first relevant result."""
    for i, doc in enumerate(retrieved):
        if any(rel in doc for rel in relevant):
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain@K."""
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k]):
        if any(rel in doc for rel in relevant):
            dcg += 1.0 / np.log2(i + 2)  # i+2 because positions start at 1
    
    # Ideal DCG (all relevant docs at top)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    
    return dcg / idcg if idcg > 0 else 0.0


def benchmark_collection(
    collection_path: Path,
    queries: List[Dict[str, Any]],
    collection_name: str,
    top_k: int = 10
) -> Dict[str, float]:
    """Benchmark retrieval quality for a collection."""
    
    client = chromadb.PersistentClient(path=str(collection_path))
    
    # Find collection
    collections = client.list_collections()
    if not collections:
        print(f"ERROR: No collections found in {collection_path}")
        return {}
    
    collection = collections[0]  # Use first collection
    print(f"  Using collection: {collection.name}")
    
    # Run queries
    metrics = {
        "precision@1": [],
        "precision@5": [],
        "precision@10": [],
        "recall@5": [],
        "recall@10": [],
        "mrr": [],
        "ndcg@5": [],
        "ndcg@10": []
    }
    
    for query_data in queries:
        query = query_data["query"]
        relevant_docs = query_data["relevant_docs"]
        
        # Search
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # Extract source files
        retrieved = []
        if results and "metadatas" in results and results["metadatas"]:
            retrieved = [
                meta.get("source_file", "")
                for meta in results["metadatas"][0]
            ]
        
        # Calculate metrics
        metrics["precision@1"].append(precision_at_k(retrieved, relevant_docs, 1))
        metrics["precision@5"].append(precision_at_k(retrieved, relevant_docs, 5))
        metrics["precision@10"].append(precision_at_k(retrieved, relevant_docs, 10))
        metrics["recall@5"].append(recall_at_k(retrieved, relevant_docs, 5))
        metrics["recall@10"].append(recall_at_k(retrieved, relevant_docs, 10))
        metrics["mrr"].append(mrr(retrieved, relevant_docs))
        metrics["ndcg@5"].append(ndcg_at_k(retrieved, relevant_docs, 5))
        metrics["ndcg@10"].append(ndcg_at_k(retrieved, relevant_docs, 10))
    
    # Average metrics
    avg_metrics = {
        key: np.mean(values) if values else 0.0
        for key, values in metrics.items()
    }
    
    return avg_metrics


def main():
    parser = argparse.ArgumentParser(description="Benchmark retrieval quality")
    parser.add_argument(
        "--old-collection",
        type=Path,
        default=Path("data/memory"),
        help="Old collection directory (MiniLM or similar)"
    )
    parser.add_argument(
        "--new-collection",
        type=Path,
        default=Path("data/memory_bge_m3"),
        help="New collection directory (BGE-M3)"
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("benchmark_queries.json"),
        help="Benchmark queries JSON file"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results to retrieve"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("  Retrieval Quality Benchmark")
    print("=" * 80)
    print()
    
    # Load queries
    queries = load_queries(args.queries)
    print(f"Loaded {len(queries)} benchmark queries\n")
    
    # Benchmark old collection
    print("[1/2] Benchmarking old collection (baseline)...")
    old_metrics = benchmark_collection(
        args.old_collection,
        queries,
        "old",
        args.top_k
    )
    
    # Benchmark new collection
    print("\n[2/2] Benchmarking new collection (BGE-M3)...")
    new_metrics = benchmark_collection(
        args.new_collection,
        queries,
        "new",
        args.top_k
    )
    
    # Compare
    print("\n" + "=" * 80)
    print("  Results")
    print("=" * 80)
    print(f"{'Metric':<20} {'Old':<15} {'New (BGE-M3)':<15} {'Improvement':<15}")
    print("-" * 80)
    
    for metric in ["precision@1", "precision@5", "precision@10", "recall@5", "recall@10", "mrr", "ndcg@5", "ndcg@10"]:
        old_val = old_metrics.get(metric, 0.0)
        new_val = new_metrics.get(metric, 0.0)
        
        if old_val > 0:
            improvement = ((new_val - old_val) / old_val) * 100
            improvement_str = f"+{improvement:.1f}%"
        else:
            improvement_str = "N/A"
        
        print(f"{metric:<20} {old_val:<15.3f} {new_val:<15.3f} {improvement_str:<15}")
    
    # Summary
    print("\n" + "=" * 80)
    print("  Summary")
    print("=" * 80)
    
    avg_improvement = np.mean([
        ((new_metrics[m] - old_metrics[m]) / old_metrics[m]) * 100
        for m in ["precision@5", "recall@10", "mrr", "ndcg@10"]
        if old_metrics.get(m, 0) > 0
    ])
    
    print(f"Average improvement: {avg_improvement:.1f}%")
    
    if avg_improvement >= 15:
        print("✅ PASS: Improvement meets 15-20% target")
    else:
        print(f"⚠️  WARNING: Improvement below 15% target (got {avg_improvement:.1f}%)")


if __name__ == "__main__":
    main()
