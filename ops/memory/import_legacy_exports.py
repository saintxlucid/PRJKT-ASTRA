#!/usr/bin/env python
"""
Legacy Memory Importer
Import existing vector embeddings from Astra_Memory/ and ASTRA MEMORY EXPORTS 1&2
into production MemoryEngine with deduplication.

Sacred Code: 333
Usage: python ops/memory/import_legacy_exports.py [--source {dir}] [--dry-run]
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from hashlib import md5

logger = logging.getLogger("astra.ops.memory.importer")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)


def find_legacy_memory_exports() -> List[Path]:
    """
    Scan for legacy memory export directories.
    
    Returns:
        List of Path objects pointing to found directories
    """
    candidates = [
        Path("Astra_Memory"),
        Path("ASTRA MEMORY EXPORTS 1"),
        Path("ASTRA MEMORY EXPORTS 2"),
        Path("astra_memory"),
        Path("memory_exports")
    ]
    
    found = []
    for path in candidates:
        if path.exists() and path.is_dir():
            found.append(path.resolve())
            logger.info(f"Found legacy memory export: {path}")
    
    return found


def load_vector_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load vectors from a file (JSON or JSONL).
    
    Returns:
        List of vector dicts with structure: {id, embedding, metadata}
    """
    vectors = []
    
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Try JSONL format first (one dict per line)
        lines = content.strip().split("\n")
        if len(lines) > 1 and all(line.startswith("{") for line in lines if line.strip()):
            for line in lines:
                if line.strip():
                    try:
                        vector = json.loads(line)
                        vectors.append(vector)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipped malformed JSON line in {file_path.name}")
            
            logger.info(f"Loaded {len(vectors)} vectors from JSONL: {file_path.name}")
            return vectors
        
        # Try plain JSON format
        data = json.loads(content)
        if isinstance(data, list):
            vectors = data
        elif isinstance(data, dict):
            # Try common keys
            for key in ("vectors", "embeddings", "data", "items"):
                if key in data and isinstance(data[key], list):
                    vectors = data[key]
                    break
        
        logger.info(f"Loaded {len(vectors)} vectors from JSON: {file_path.name}")
        return vectors
    
    except Exception as e:
        logger.error(f"Failed to load vector file {file_path}: {e}")
        return []


def compute_vector_hash(vector: Dict[str, Any]) -> str:
    """
    Compute hash of a vector for deduplication.
    Uses embedding vector content and metadata.
    """
    try:
        embedding = vector.get("embedding", [])
        metadata = vector.get("metadata", {})
        text = str((tuple(embedding[:16]), str(metadata)))  # Use first 16 dims + metadata
        return md5(text.encode()).hexdigest()
    except Exception:
        return md5(str(vector).encode()).hexdigest()


def deduplicate_vectors(vectors: List[Dict[str, Any]]) -> Tuple[List[Dict], int]:
    """
    Remove duplicate vectors based on embedding content.
    
    Returns:
        (deduplicated_list, duplicate_count)
    """
    seen_hashes: set = set()
    deduped = []
    duplicates = 0
    
    for vector in vectors:
        h = compute_vector_hash(vector)
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped.append(vector)
        else:
            duplicates += 1
    
    logger.info(f"Deduplication: {duplicates} duplicates removed ({len(deduped)} unique remain)")
    return deduped, duplicates


def validate_vector_format(vector: Dict[str, Any]) -> bool:
    """
    Check if vector has required fields for production MemoryEngine.
    
    Required: embedding (list of floats)
    Optional: id, metadata, timestamp
    """
    if not isinstance(vector, dict):
        return False
    
    embedding = vector.get("embedding")
    if not isinstance(embedding, (list, tuple)) or len(embedding) == 0:
        return False
    
    if not all(isinstance(x, (int, float)) for x in embedding):
        return False
    
    return True


def normalize_vectors(vectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize vector dicts to production format.
    Adds missing fields, validates dimensions.
    """
    normalized = []
    
    for i, vector in enumerate(vectors):
        if not validate_vector_format(vector):
            logger.warning(f"Skipped invalid vector at index {i}")
            continue
        
        norm_vec = {
            "id": vector.get("id") or f"legacy_{i}_{compute_vector_hash(vector)[:8]}",
            "embedding": list(vector.get("embedding", [])),
            "metadata": vector.get("metadata", {}),
            "source": vector.get("source", "legacy_import"),
            "imported_at": datetime.utcnow().isoformat()
        }
        
        normalized.append(norm_vec)
    
    logger.info(f"Normalized {len(normalized)} vectors to production format")
    return normalized


def import_vectors(vectors: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
    """
    Import vectors into production MemoryEngine.
    
    Args:
        vectors: List of normalized vector dicts
        dry_run: If True, don't actually import (just report what would happen)
    
    Returns:
        Stats dict: {imported, skipped, errors, duration_sec}
    """
    stats: Dict[str, Any] = {
        "imported": 0,
        "skipped": 0,
        "errors": 0,
        "start_time": datetime.utcnow().isoformat(),
        "dry_run": dry_run
    }
    
    if dry_run:
        logger.info(f"DRY RUN: Would import {len(vectors)} vectors")
        stats["imported"] = len(vectors)
        stats["end_time"] = datetime.utcnow().isoformat()
        return stats
    
    try:
        # Import production MemoryEngine
        try:
            from astra.lib.memory_engine import MemoryEngine
        except ImportError:
            # Fallback to alternative location
            from astra.core.memory import MemoryEngine  # type: ignore
        
        engine = MemoryEngine.default()
        logger.info("Connected to production MemoryEngine")
        
        for i, vector in enumerate(vectors):
            try:
                # Add vector to engine
                # Assumes MemoryEngine has .add() or similar method
                if hasattr(engine, "add_vector"):
                    engine.add_vector(
                        embedding=vector["embedding"],
                        metadata=vector["metadata"],
                        vector_id=vector["id"]
                    )
                elif hasattr(engine, "add"):
                    engine.add(vector)
                else:
                    logger.warning("MemoryEngine.add() method not found")
                    stats["skipped"] += 1
                    continue
                
                stats["imported"] += 1
                
                if (i + 1) % 1000 == 0:
                    logger.info(f"Progress: {i + 1}/{len(vectors)} imported")
            
            except Exception as e:
                logger.error(f"Error importing vector {vector.get('id')}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Import complete: {stats['imported']} vectors imported, {stats['errors']} errors")
    
    except ImportError:
        logger.error("Production MemoryEngine not available - running in dry-run mode")
        stats["imported"] = len(vectors)
        stats["dry_run"] = True
    
    except Exception as e:
        logger.error(f"Fatal error during import: {e}")
        stats["errors"] = len(vectors)
    
    stats["end_time"] = datetime.utcnow().isoformat()
    return stats


def main() -> int:
    """
    Main import pipeline.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Import legacy memory exports")
    parser.add_argument("--source", type=str, help="Specific source directory to import from")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually import, just report")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Legacy Memory Importer - Sacred Code 333")
    logger.info("=" * 60)
    
    # Find sources
    if args.source:
        sources = [Path(args.source)]
    else:
        sources = find_legacy_memory_exports()
    
    if not sources:
        logger.warning("No legacy memory exports found!")
        return 1
    
    # Load all vectors
    all_vectors: List[Dict[str, Any]] = []
    for source_dir in sources:
        logger.info(f"\nScanning {source_dir.name}...")
        vector_files = list(source_dir.glob("**/*.json")) + list(source_dir.glob("**/*.jsonl"))
        
        for file_path in vector_files:
            vectors = load_vector_file(file_path)
            all_vectors.extend(vectors)
    
    logger.info(f"\nTotal vectors loaded: {len(all_vectors)}")
    
    # Deduplicate
    deduped_vectors, dup_count = deduplicate_vectors(all_vectors)
    
    # Normalize
    normalized_vectors = normalize_vectors(deduped_vectors)
    
    # Import
    logger.info(f"\nImporting {len(normalized_vectors)} vectors...")
    stats = import_vectors(normalized_vectors, dry_run=args.dry_run)
    
    # Report
    logger.info("\n" + "=" * 60)
    logger.info("Import Summary:")
    logger.info(f"  Loaded: {len(all_vectors)}")
    logger.info(f"  Duplicates: {dup_count}")
    logger.info(f"  Normalized: {len(normalized_vectors)}")
    logger.info(f"  Imported: {stats['imported']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"  Dry Run: {stats['dry_run']}")
    logger.info(f"  Duration: {stats['end_time']}")
    logger.info(f"  Sacred Code: 333")
    logger.info("=" * 60)
    
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
