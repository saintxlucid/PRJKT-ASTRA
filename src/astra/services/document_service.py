# src/astra/services/document_service.py
"""
ASTRA Document Intelligence Service
PDF ingestion, chunking, embedding, and indexing
"""
import os
import json
import hashlib
import argparse
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import structlog

logger = structlog.get_logger()

try:
    import fitz  # pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("pymupdf not installed - PDF extraction disabled")

# ---------- CONFIG ----------
INDEX_DIR = os.environ.get("DOC_INDEX_DIR", "data/document_index")
os.makedirs(INDEX_DIR, exist_ok=True)

# Qdrant configuration
QDRANT_URL = os.environ.get("QDRANT_URL")  # e.g. http://127.0.0.1:6333 or http://qdrant:6333
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "astra_docs")
USE_QDRANT = os.environ.get("USE_QDRANT", "true").lower() in ("1", "true", "yes")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Lazy imports for optional deps
QDRANT_AVAILABLE = False
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False
    logger.info("qdrant-client not installed - vector DB disabled")

# ---------- EXTRACTION ----------
def extract_text_from_pdf(path: str) -> str:
    """
    Extract text from PDF file.
    
    Args:
        path: Path to PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        ImportError: If pymupdf not installed
        Exception: If extraction fails
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("pymupdf required for PDF extraction: pip install pymupdf")
    
    logger.info("extracting_pdf", path=path)
    
    try:
        doc = fitz.open(path)
        pages = []
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text("text")
            if page_text.strip():
                pages.append(f"[Page {page_num}]\n{page_text}")
        doc.close()
        
        full_text = "\n\n".join(pages)
        logger.info("extraction_complete", path=path, pages=len(pages), chars=len(full_text))
        return full_text
        
    except Exception as e:
        logger.error("extraction_failed", path=path, error=str(e))
        raise

def extract_text_with_ocr_fallback(path: str) -> str:
    """
    Extract text with OCR fallback for scanned PDFs.
    
    Args:
        path: Path to PDF file
        
    Returns:
        Extracted text (OCR if needed)
    """
    # Try regular extraction first
    text = extract_text_from_pdf(path)
    
    # If very little text extracted, might be scanned PDF
    if len(text.strip()) < 100:
        logger.warning("low_text_detected", path=path, chars=len(text))
        # TODO: Add pytesseract OCR fallback here
        logger.info("ocr_fallback_not_implemented")
    
    return text

# ---------- CHUNKING ----------
def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100
) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Number of words per chunk
        overlap: Number of overlapping words
        
    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []
    i = 0
    total = len(words)
    
    while i < total:
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        i += chunk_size - overlap
    
    logger.info("chunking_complete", total_chunks=len(chunks), chunk_size=chunk_size)
    return chunks

# ---------- EMBEDDING ----------
def fake_embed(text: str) -> str:
    """
    Placeholder embedding - replace with real vector model.
    
    Args:
        text: Text to embed
        
    Returns:
        Hash string (placeholder for real vector)
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def real_embed(text: str) -> List[float]:
    """
    Real embedding using sentence-transformers (if available).
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector
    """
    try:
        from sentence_transformers import SentenceTransformer
        # Cache model instance
        if not hasattr(real_embed, "_model"):
            model_name = EMBEDDING_MODEL_NAME
            real_embed._model = SentenceTransformer(model_name)
            # get dimension for Qdrant setup
            sample_vec = real_embed._model.encode("hello", convert_to_numpy=True)
            real_embed._dim = int(sample_vec.shape[0])
            logger.info("embedding_model_loaded", model=model_name, dim=real_embed._dim)
        embedding = real_embed._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except ImportError:
        logger.warning("sentence_transformers_not_available_using_fake_embed")
        return [float(ord(c)) for c in fake_embed(text)[:128]]  # Fake vector


# ---------- QDRANT HELPERS ----------
def _qdrant_enabled() -> bool:
    return USE_QDRANT and QDRANT_AVAILABLE and QDRANT_URL is not None

def _get_qdrant_client() -> Optional[QdrantClient]:
    if not _qdrant_enabled():
        return None
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        return client
    except Exception as e:
        logger.error("qdrant_client_init_failed", error=str(e))
        return None

def _ensure_collection(client: QdrantClient, vector_size: int) -> None:
    try:
        collections = client.get_collections()
        names = [c.name for c in collections.collections]
        if QDRANT_COLLECTION not in names:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            logger.info("qdrant_collection_created", name=QDRANT_COLLECTION, dim=vector_size)
        else:
            logger.info("qdrant_collection_exists", name=QDRANT_COLLECTION)
    except Exception as e:
        logger.error("qdrant_collection_setup_failed", error=str(e))
        raise

# ---------- INGESTION ----------
def ingest_pdf(
    path: str,
    index_name: str = "default.jsonl",
    chunk_size: int = 800,
    overlap: int = 100,
    use_real_embeddings: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Ingest PDF into JSONL index.
    
    Args:
        path: Path to PDF file
        index_name: Name of index file
        chunk_size: Words per chunk
        overlap: Overlapping words
        use_real_embeddings: Use sentence-transformers (slow but accurate)
        metadata: Additional metadata to store
        
    Returns:
        Number of chunks ingested
    """
    logger.info("ingesting_pdf", path=path, index=index_name)
    
    # Extract and chunk
    text = extract_text_from_pdf(path)
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    
    # Build index path
    index_path = os.path.join(INDEX_DIR, index_name)
    
    # Write chunks
    count = 0
    embed_fn = real_embed if use_real_embeddings or _qdrant_enabled() else fake_embed

    # Prepare Qdrant if enabled
    qdrant_client = _get_qdrant_client()
    if qdrant_client is not None:
        # Ensure collection with correct dimension
        # Compute a sample embedding to get vector size
        sample_vec = real_embed("sample for dim")
        _ensure_collection(qdrant_client, vector_size=len(sample_vec))

    with open(index_path, "a", encoding="utf-8") as idx:
        points_batch: list = []
        for i, chunk in enumerate(chunks):
            emb = embed_fn(chunk)
            record = {
                "id": f"{os.path.basename(path)}::{i}",
                "text": chunk,
                "embed": emb,
                "source": path,
                "chunk_index": i,
                "metadata": metadata or {}
            }
            idx.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

            # Upsert to Qdrant if enabled with real vectors
            if qdrant_client is not None and isinstance(emb, list) and all(isinstance(x, (int, float)) for x in emb):
                points_batch.append(
                    PointStruct(
                        id=f"{os.path.basename(path)}::{i}",
                        vector=emb,
                        payload={
                            "text": chunk,
                            "source": path,
                            "chunk_index": i,
                            "metadata": metadata or {}
                        }
                    )
                )

        # Flush batch to Qdrant
        if qdrant_client is not None and points_batch:
            try:
                qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points_batch)
                logger.info("qdrant_upserted", points=len(points_batch))
            except Exception as e:
                logger.error("qdrant_upsert_failed", error=str(e))
    
    logger.info("ingestion_complete", document=path, chunks=count, index=index_name)
    return count

# ---------- SEARCH ----------
def simple_keyword_search(
    index_name: str,
    keyword: str,
    top: int = 5
) -> List[Dict[str, Any]]:
    """
    Simple keyword-based search (naive implementation).
    
    Args:
        index_name: Index file name
        keyword: Search keyword
        top: Number of results to return
        
    Returns:
        List of matching records
    """
    index_path = os.path.join(INDEX_DIR, index_name)
    results = []
    
    if not os.path.exists(index_path):
        logger.warning("index_not_found", index=index_name)
        return results
    
    logger.info("searching", index=index_name, keyword=keyword)
    
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            # Simple keyword count as score
            score = record["text"].lower().count(keyword.lower())
            if score > 0:
                results.append((score, record))
    
    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    
    final_results = [rec for _, rec in results[:top]]
    logger.info("search_complete", results=len(final_results))
    
    return final_results

def semantic_search(
    index_name: str,
    query: str,
    top: int = 5
) -> List[Dict[str, Any]]:
    """Semantic search using Qdrant vector DB if enabled, otherwise fallback to keyword search."""
    if not _qdrant_enabled():
        logger.info("semantic_search_fallback_keyword")
        return simple_keyword_search(index_name, query, top)

    client = _get_qdrant_client()
    if client is None:
        logger.info("semantic_search_client_none_fallback")
        return simple_keyword_search(index_name, query, top)

    # Embed the query
    query_vec = real_embed(query)
    try:
        search_res = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vec,
            limit=top
        )
        # Each result: ScoredPoint with payload
        results: List[Dict[str, Any]] = []
        for sp in search_res:
            payload = sp.payload or {}
            # Normalize to match keyword search record shape
            results.append({
                "text": payload.get("text", ""),
                "source": payload.get("source", "unknown"),
                "chunk_index": payload.get("chunk_index", -1),
                "score": float(sp.score)
            })
        logger.info("semantic_search_results", count=len(results))
        return results
    except Exception as e:
        logger.error("semantic_search_failed", error=str(e))
        return simple_keyword_search(index_name, query, top)

# ---------- INDEX MANAGEMENT ----------
def list_indexes() -> List[str]:
    """List all available indexes."""
    if not os.path.exists(INDEX_DIR):
        return []
    return [f for f in os.listdir(INDEX_DIR) if f.endswith(".jsonl")]

def get_index_stats(index_name: str) -> Dict[str, Any]:
    """Get statistics for an index."""
    index_path = os.path.join(INDEX_DIR, index_name)
    
    if not os.path.exists(index_path):
        return {"error": "Index not found"}
    
    count = 0
    total_chars = 0
    sources = set()
    
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            count += 1
            total_chars += len(record.get("text", ""))
            sources.add(record.get("source", "unknown"))
    
    return {
        "index": index_name,
        "chunks": count,
        "total_chars": total_chars,
        "sources": list(sources),
        "avg_chunk_size": total_chars // count if count > 0 else 0
    }

# ---------- CLI ----------
def main():
    """Command-line interface for document ingestion."""
    parser = argparse.ArgumentParser(description="ASTRA Document Intelligence CLI")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a PDF")
    ingest_parser.add_argument("pdf", help="PDF file to ingest")
    ingest_parser.add_argument("--index", default="default.jsonl", help="Index filename")
    ingest_parser.add_argument("--chunk", type=int, default=800, help="Chunk size (words)")
    ingest_parser.add_argument("--overlap", type=int, default=100, help="Overlap size (words)")
    ingest_parser.add_argument("--real-embeddings", action="store_true", help="Use real embeddings")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search an index")
    search_parser.add_argument("keyword", help="Search keyword")
    search_parser.add_argument("--index", default="default.jsonl", help="Index filename")
    search_parser.add_argument("--top", type=int, default=5, help="Number of results")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all indexes")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.add_argument("index", help="Index filename")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        n = ingest_pdf(
            args.pdf,
            index_name=args.index,
            chunk_size=args.chunk,
            overlap=args.overlap,
            use_real_embeddings=args.real_embeddings
        )
        print(f"✅ Ingested {n} chunks into {args.index}")
        
    elif args.command == "search":
        results = simple_keyword_search(args.index, args.keyword, args.top)
        print(f"\n🔍 Found {len(results)} results for '{args.keyword}':\n")
        for i, rec in enumerate(results, 1):
            print(f"{i}. {rec['source']} (chunk {rec['chunk_index']})")
            print(f"   {rec['text'][:200]}...\n")
            
    elif args.command == "list":
        indexes = list_indexes()
        print(f"\n📚 Available indexes ({len(indexes)}):\n")
        for idx in indexes:
            stats = get_index_stats(idx)
            print(f"  • {idx}: {stats['chunks']} chunks from {len(stats['sources'])} sources")
            
    elif args.command == "stats":
        stats = get_index_stats(args.index)
        if "error" in stats:
            print(f"❌ {stats['error']}")
        else:
            print(f"\n📊 Index Statistics: {args.index}\n")
            print(f"  Chunks: {stats['chunks']}")
            print(f"  Total characters: {stats['total_chars']:,}")
            print(f"  Average chunk size: {stats['avg_chunk_size']} chars")
            print(f"  Sources: {len(stats['sources'])}")
            for src in stats['sources']:
                print(f"    • {src}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
