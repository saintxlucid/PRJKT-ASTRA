#!/usr/bin/env python3
"""
ASTRA Persona Memory Ingestion System

Extracts, chunks, and embeds content from ASTRA MEMORY EXPORTS 
into the semantic memory system with proper metadata tagging.

Usage:
    python scripts/ingest_persona_memories.py [--dry-run] [--verbose]
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

import chromadb
from sentence_transformers import SentenceTransformer
import structlog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

class PersonaIngester:
    """Handles ingestion of persona memories from export directories"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent
        self.export_dirs = [
            self.project_root / "ASTRA MEMORY EXPORTS",
            self.project_root / "ASTRA MEMORY EXPORTS 2"
        ]
        
        # Initialize components
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        
        # Stats tracking
        self.stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "memories_ingested": 0,
            "errors": 0,
            "skipped": 0
        }

    def initialize_components(self):
        """Initialize embedding model and vector store"""
        logger.info("Initializing components...")
        
        try:
            # Load embedding model
            model_name = os.getenv("ASTRA_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            logger.info(f"Loading embedding model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            
            # Initialize ChromaDB
            chroma_dir = self.project_root / "data" / "chromadb"
            chroma_dir.mkdir(parents=True, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
            
            # Get or create collection
            collection_name = os.getenv("ASTRA_VECTOR_COLLECTION", "astra_memory")
            try:
                self.collection = self.chroma_client.get_collection(collection_name)
                logger.info(f"Using existing collection: {collection_name}")
            except Exception:
                # Create collection if it doesn't exist
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    def extract_text_content(self, file_path: Path) -> Optional[str]:
        """Extract plain text from various file formats"""
        try:
            suffix = file_path.suffix.lower()
            
            if suffix in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
                    
            elif suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Handle various JSON structures
                if isinstance(data, list):
                    # Array of conversation entries
                    text_parts = []
                    for item in data:
                        if isinstance(item, str):
                            text_parts.append(item)
                        elif isinstance(item, dict):
                            # Extract text from common keys
                            for key in ['content', 'message', 'text', 'body']:
                                if key in item and isinstance(item[key], str):
                                    text_parts.append(item[key])
                    return '\n\n'.join(text_parts)
                    
                elif isinstance(data, dict):
                    # Single object - extract text fields
                    text_parts = []
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) > 20:
                            text_parts.append(f"{key}: {value}")
                    return '\n\n'.join(text_parts)
                    
            elif suffix == '.html':
                # Basic HTML stripping
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
                # Remove script and style elements
                html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
                # Remove HTML tags
                text_content = re.sub(r'<[^>]+>', '', html_content)
                # Clean up whitespace
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                return text_content
                
            else:
                logger.warning(f"Unsupported file type: {suffix} for {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            self.stats["errors"] += 1
            return None

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the boundary
                for i in range(min(100, end - start), 0, -1):
                    if text[start + i - 1] in '.!?\n':
                        end = start + i
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - overlap)
            
        return chunks

    def normalize_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common boilerplate patterns
        patterns_to_remove = [
            r'Generated by.*?on \d{4}-\d{2}-\d{2}',
            r'Last updated:.*?\d{4}',
            r'Copyright.*?\d{4}',
            r'Page \d+ of \d+',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()

    def create_memory_id(self, content: str, source: str) -> str:
        """Generate deterministic ID for memory chunk"""
        combined = f"{source}::{content[:100]}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def ingest_file(self, file_path: Path, source_dir: str) -> int:
        """Ingest a single file into memory"""
        logger.info(f"Processing: {file_path}")
        
        # Extract text content
        raw_text = self.extract_text_content(file_path)
        if not raw_text:
            self.stats["skipped"] += 1
            return 0
            
        # Normalize text
        normalized_text = self.normalize_text(raw_text)
        if len(normalized_text) < 50:  # Skip very short content
            logger.debug(f"Skipping short content in {file_path}")
            self.stats["skipped"] += 1
            return 0
            
        # Create chunks
        chunks = self.chunk_text(normalized_text)
        logger.debug(f"Created {len(chunks)} chunks from {file_path}")
        
        memories_added = 0
        
        for i, chunk in enumerate(chunks):
            try:
                # Create memory metadata
                memory_id = self.create_memory_id(chunk, str(file_path))
                
                metadata = {
                    "namespace": "persona",
                    "source": source_dir,
                    "file": file_path.name,
                    "author": "Saint Lucid",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "ingested_at": datetime.now().isoformat(),
                    "file_type": file_path.suffix.lower(),
                    "char_count": len(chunk)
                }
                
                # Tag based on content patterns
                tags = self._extract_tags(chunk, file_path.name)
                if tags:
                    metadata["tags"] = ",".join(tags)
                
                if not self.dry_run:
                    # Generate embedding
                    embedding = self.embedding_model.encode(chunk).tolist()
                    
                    # Upsert to ChromaDB
                    self.collection.upsert(
                        ids=[memory_id],
                        documents=[chunk],
                        embeddings=[embedding],
                        metadatas=[metadata]
                    )
                
                memories_added += 1
                self.stats["chunks_created"] += 1
                
            except Exception as e:
                logger.error(f"Failed to ingest chunk {i} from {file_path}: {e}")
                self.stats["errors"] += 1
        
        self.stats["files_processed"] += 1
        return memories_added

    def _extract_tags(self, content: str, filename: str) -> List[str]:
        """Extract semantic tags from content"""
        tags = []
        
        # Filename-based tags
        if 'conversation' in filename.lower():
            tags.append('conversation')
        if 'user' in filename.lower():
            tags.append('profile')
        if 'config' in filename.lower():
            tags.append('configuration')
            
        # Content-based tags
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['prefer', 'like', 'want', 'need']):
            tags.append('preference')
        if any(word in content_lower for word in ['value', 'principle', 'believe']):
            tags.append('values')
        if any(word in content_lower for word in ['instruction', 'guide', 'how to']):
            tags.append('instruction')
        if any(word in content_lower for word in ['decision', 'chose', 'decided']):
            tags.append('decision')
        if any(word in content_lower for word in ['saint lucid', 'karim', 'creator']):
            tags.append('creator')
        if any(word in content_lower for word in ['astra', 'assistant', 'ai']):
            tags.append('identity')
            
        return tags

    def scan_export_directories(self) -> List[Path]:
        """Scan export directories for files to process"""
        files_to_process = []
        
        for export_dir in self.export_dirs:
            if not export_dir.exists():
                logger.warning(f"Export directory not found: {export_dir}")
                continue
                
            logger.info(f"Scanning: {export_dir}")
            
            # Recursively find files
            for file_path in export_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.json', '.html']:
                    files_to_process.append(file_path)
                    
        logger.info(f"Found {len(files_to_process)} files to process")
        return files_to_process

    def create_manifest(self, files_processed: List[Path]):
        """Create ingestion manifest for rollback/replay"""
        manifest_path = self.project_root / "data" / f"persona_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(manifest_path, 'w') as f:
            for file_path in files_processed:
                entry = {
                    "file_path": str(file_path),
                    "relative_path": str(file_path.relative_to(self.project_root)),
                    "ingested_at": datetime.now().isoformat(),
                    "stats": self.stats
                }
                f.write(json.dumps(entry) + '\n')
        
        logger.info(f"Created manifest: {manifest_path}")

    def run(self) -> Dict[str, Any]:
        """Run the complete ingestion process"""
        logger.info("Starting persona memory ingestion...")
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        try:
            # Initialize components
            self.initialize_components()
            
            # Scan for files
            files_to_process = self.scan_export_directories()
            
            if not files_to_process:
                logger.warning("No files found to process")
                return self.stats
            
            # Process each file
            for file_path in files_to_process:
                try:
                    memories_added = self.ingest_file(
                        file_path, 
                        file_path.parent.parent.name  # Export directory name
                    )
                    self.stats["memories_ingested"] += memories_added
                    
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    self.stats["errors"] += 1
            
            # Create manifest
            if not self.dry_run:
                self.create_manifest(files_to_process)
                
                # Create completion marker
                marker_path = self.project_root / "data" / ".astra_persona_loaded"
                with open(marker_path, 'w') as f:
                    f.write(json.dumps({
                        "loaded_at": datetime.now().isoformat(),
                        "stats": self.stats
                    }, indent=2))
                
            # Log final stats
            logger.info("Ingestion complete!", **self.stats)
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            self.stats["errors"] += 1
            raise


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest ASTRA persona memories")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run ingestion
    ingester = PersonaIngester(dry_run=args.dry_run)
    stats = ingester.run()
    
    print(f"\n✅ Ingestion Summary:")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Chunks created: {stats['chunks_created']}")
    print(f"Memories ingested: {stats['memories_ingested']}")
    print(f"Errors: {stats['errors']}")
    print(f"Skipped: {stats['skipped']}")


if __name__ == "__main__":
    main()