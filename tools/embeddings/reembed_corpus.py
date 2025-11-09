#!/usr/bin/env python3
"""
Re-embed corpus with BGE-M3 (state-of-the-art local embeddings).

Purpose:
- Replace older embeddings (MiniLM, all-mpnet-base-v2) with BGE-M3
- 15-20% better retrieval quality (MTEB benchmark)
- Preserves document metadata and structure
- Adds provenance tracking for citations

Expected Runtime: ~3 hours for 21K documents (CPU, batch_size=32)

Usage:
    python tools/embeddings/reembed_corpus.py --source data/docs --batch-size 32 --device cpu

Options:
    --source: Source directory with documents (default: data/docs)
    --output: Output ChromaDB directory (default: data/memory_bge_m3)
    --batch-size: Embedding batch size (default: 32)
    --device: cpu or cuda (default: cpu)
    --dry-run: Preview only, don't embed
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.embeddings_bge_m3 import BGE_M3_Embedder, EmbeddingConfig

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb")
    sys.exit(1)


def load_documents(source_dir: Path) -> List[Dict[str, Any]]:
    """
    Load documents from source directory.
    
    Expected format:
    - .txt files: Plain text
    - .json files: {"text": "...", "metadata": {...}}
    - .md files: Markdown
    """
    docs = []
    
    for file_path in source_dir.rglob("*"):
        if file_path.suffix not in [".txt", ".json", ".md"]:
            continue
        
        try:
            if file_path.suffix == ".json":
                data = json.loads(file_path.read_text(encoding="utf-8"))
                text = data.get("text", "")
                metadata = data.get("metadata", {})
            else:
                text = file_path.read_text(encoding="utf-8")
                metadata = {}
            
            # Add file metadata
            metadata["source_file"] = str(file_path.relative_to(source_dir))
            metadata["file_type"] = file_path.suffix[1:]  # Remove leading dot
            
            docs.append({
                "text": text,
                "metadata": metadata,
                "id": str(len(docs))
            })
        
        except Exception as e:
            print(f"WARNING: Failed to load {file_path}: {e}")
    
    return docs


def reembed_corpus(
    source_dir: Path,
    output_dir: Path,
    batch_size: int = 32,
    device: str = "cpu",
    dry_run: bool = False
):
    """Re-embed corpus with BGE-M3."""
    
    print("=" * 80)
    print("  BGE-M3 Corpus Re-Embedding")
    print("=" * 80)
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print(f"Device: {device}")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Load documents
    print("[1/4] Loading documents...")
    docs = load_documents(source_dir)
    print(f"✅ Loaded {len(docs)} documents")
    
    if len(docs) == 0:
        print("ERROR: No documents found in source directory")
        return
    
    if dry_run:
        print("\n=== DRY RUN: Preview ===")
        for i, doc in enumerate(docs[:5]):
            print(f"\nDocument {i+1}:")
            print(f"  Text: {doc['text'][:100]}...")
            print(f"  Metadata: {doc['metadata']}")
        print(f"\n... and {len(docs) - 5} more documents")
        print("\n✅ Dry run complete. Run without --dry-run to embed.")
        return
    
    # Initialize embedder
    print("\n[2/4] Initializing BGE-M3 embedder...")
    cfg = EmbeddingConfig(device=device, batch_size=batch_size)
    embedder = BGE_M3_Embedder(cfg)
    print(f"✅ Model loaded: {embedder.model.get_sentence_embedding_dimension()}D vectors")
    
    # Initialize ChromaDB
    print("\n[3/4] Initializing ChromaDB...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(
        path=str(output_dir),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Create collection (delete if exists)
    collection_name = "astra_memories_bge_m3"
    try:
        client.delete_collection(collection_name)
        print(f"✅ Deleted old collection: {collection_name}")
    except:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"model": "BAAI/bge-m3", "dimension": 1024}
    )
    print(f"✅ Created collection: {collection_name}")
    
    # Embed and store
    print("\n[4/4] Embedding documents...")
    start_time = time.time()
    
    # Process in batches
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        batch_texts = [doc["text"] for doc in batch]
        batch_ids = [doc["id"] for doc in batch]
        batch_metadata = [doc["metadata"] for doc in batch]
        
        # Embed batch
        batch_start = time.time()
        embeddings = embedder.embed_batch(batch_texts, batch_size=batch_size)
        batch_time = time.time() - batch_start
        
        # Store in ChromaDB
        collection.add(
            ids=batch_ids,
            embeddings=embeddings.tolist(),
            documents=batch_texts,
            metadatas=batch_metadata
        )
        
        # Progress
        progress = (i + len(batch)) / len(docs) * 100
        throughput = len(batch) / batch_time
        print(f"  Progress: {progress:.1f}% ({i+len(batch)}/{len(docs)}) | "
              f"Throughput: {throughput:.1f} docs/sec")
    
    elapsed = time.time() - start_time
    avg_throughput = len(docs) / elapsed
    
    print(f"\n✅ Re-embedding complete!")
    print(f"  Total documents: {len(docs)}")
    print(f"  Total time: {elapsed/60:.1f} minutes")
    print(f"  Average throughput: {avg_throughput:.1f} docs/sec")
    print(f"  Collection: {collection_name} in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Re-embed corpus with BGE-M3")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/docs"),
        help="Source directory with documents"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/memory_bge_m3"),
        help="Output ChromaDB directory"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size"
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Device for embeddings (cpu or cuda)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't embed"
    )
    
    args = parser.parse_args()
    
    # Validate source directory
    if not args.source.exists():
        print(f"ERROR: Source directory not found: {args.source}")
        print(f"Create it and add documents (.txt, .json, .md files)")
        sys.exit(1)
    
    reembed_corpus(
        source_dir=args.source,
        output_dir=args.output,
        batch_size=args.batch_size,
        device=args.device,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
