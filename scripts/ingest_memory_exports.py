#!/usr/bin/env python3
"""
ASTRA Memory Export Ingestion System

Parses exported memory files from GPT sessions and ingests them into
ASTRA's memory systems (ChromaDB + SQLite).

This creates continuity — ASTRA remembers everything from prior sessions.

Usage:
    python scripts/ingest_memory_exports.py --source "ASTRA MEMORY EXPORTS"
    python scripts/ingest_memory_exports.py --source "ASTRA MEMORY EXPORTS 2"
    python scripts/ingest_memory_exports.py --batch  # Process all

Created: October 12, 2025
Creator: Saint Lucid (Karim Al-Sharif)
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.astra.core.memory_engine import get_memory_engine
from src.astra.core.identity_engine import get_identity_engine

logger = structlog.get_logger()


class MemoryExportIngester:
    """
    Ingests exported memory files into ASTRA's memory systems.
    
    Parses various formats (JSON, TXT, MD) and categorizes into:
    - Identity (core values, philosophy)
    - Cognition (focus systems, protocols)
    - Emotional (relationships, patterns)
    - Creativity (lyrics, projects)
    - Legacy (empire plans, vision)
    """
    
    def __init__(self, memory_engine=None):
        """Initialize ingester"""
        self.memory_engine = memory_engine or get_memory_engine()
        self.identity_engine = get_identity_engine()
        
        # Category mappings for auto-classification
        self.category_keywords = {
            "identity": ["core", "value", "philosophy", "manifesto", "essence", "soul"],
            "cognition": ["focus", "protocol", "system", "cognitive", "attention", "memory"],
            "emotional": ["relationship", "emotion", "feeling", "pattern", "empathy"],
            "creativity": ["lyric", "music", "song", "creative", "art", "visual", "film"],
            "legacy": ["empire", "vision", "mission", "project", "strategy", "legacy"],
            "technical": ["code", "system", "architecture", "implementation", "setup"]
        }
        
        self.stats = {
            "files_processed": 0,
            "memories_stored": 0,
            "categories": {},
            "errors": []
        }
    
    def detect_category(self, content: str, filename: str) -> str:
        """Auto-detect memory category based on content and filename"""
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for kw in keywords if kw in content_lower or kw in filename_lower)
            scores[category] = score
        
        # Return category with highest score, default to "general"
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "general"
    
    def parse_json_export(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse JSON memory export"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            memories = []
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Array of memory objects
                for item in data:
                    if isinstance(item, dict):
                        memories.append(item)
                    else:
                        memories.append({"content": str(item)})
            
            elif isinstance(data, dict):
                # Single object or structured export
                if "memories" in data:
                    memories = data["memories"]
                elif "conversations" in data:
                    # Convert conversations to memories
                    for conv in data["conversations"]:
                        memories.append({
                            "content": conv.get("content", ""),
                            "timestamp": conv.get("timestamp"),
                            "role": conv.get("role", "user")
                        })
                else:
                    # Treat whole object as single memory
                    memories.append(data)
            
            return memories
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {file_path}", error=str(e))
            return []
    
    def parse_text_export(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse text/markdown memory export"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            memories = []
            
            # Split by common delimiters
            chunks = []
            
            # Try splitting by markdown headers
            if '##' in content:
                chunks = [c.strip() for c in content.split('##') if c.strip()]
            elif '---' in content:
                chunks = [c.strip() for c in content.split('---') if c.strip()]
            else:
                # Split into paragraphs
                chunks = [c.strip() for c in content.split('\n\n') if c.strip()]
            
            # Create memory objects
            for chunk in chunks:
                if len(chunk) > 50:  # Skip very short chunks
                    memories.append({
                        "content": chunk,
                        "source_file": file_path.name
                    })
            
            # If no good splits, use whole file
            if not memories and len(content) > 50:
                memories.append({
                    "content": content,
                    "source_file": file_path.name
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to parse text file: {file_path}", error=str(e))
            return []
    
    async def ingest_file(self, file_path: Path) -> int:
        """
        Ingest a single memory export file.
        
        Returns:
            Number of memories stored
        """
        logger.info(f"Ingesting memory file: {file_path.name}")
        
        # Parse based on file type
        if file_path.suffix.lower() == '.json':
            memories = self.parse_json_export(file_path)
        else:
            memories = self.parse_text_export(file_path)
        
        if not memories:
            logger.warning(f"No memories extracted from {file_path.name}")
            return 0
        
        # Store each memory
        stored_count = 0
        
        for memory in memories:
            try:
                content = memory.get("content", "")
                if not content or len(content) < 20:
                    continue
                
                # Detect category
                category = self.detect_category(content, file_path.name)
                
                # Store in semantic memory
                memory_id = await self.memory_engine.store_semantic(
                    content=content,
                    tags=[category, "imported", file_path.stem],
                    metadata={
                        "source_file": file_path.name,
                        "category": category,
                        "import_date": datetime.now().isoformat(),
                        "original_timestamp": memory.get("timestamp")
                    }
                )
                
                if memory_id:
                    stored_count += 1
                    
                    # Track stats
                    if category not in self.stats["categories"]:
                        self.stats["categories"][category] = 0
                    self.stats["categories"][category] += 1
                    
                    logger.debug(f"Stored memory: {content[:50]}... [category: {category}]")
                
            except Exception as e:
                logger.error(f"Failed to store memory: {str(e)}")
                self.stats["errors"].append(str(e))
        
        self.stats["files_processed"] += 1
        self.stats["memories_stored"] += stored_count
        
        logger.info(f"✓ Ingested {stored_count} memories from {file_path.name}")
        
        return stored_count
    
    async def ingest_directory(self, directory: Path) -> int:
        """
        Ingest all memory export files from a directory.
        
        Returns:
            Total number of memories stored
        """
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 0
        
        logger.info(f"Scanning directory: {directory}")
        
        # Find all potential memory files
        supported_extensions = ['.json', '.txt', '.md']
        memory_files = []
        
        for ext in supported_extensions:
            memory_files.extend(directory.glob(f"*{ext}"))
            memory_files.extend(directory.glob(f"**/*{ext}"))  # Recursive
        
        if not memory_files:
            logger.warning(f"No memory files found in {directory}")
            return 0
        
        logger.info(f"Found {len(memory_files)} potential memory files")
        
        # Ingest each file
        total_stored = 0
        for file_path in memory_files:
            stored = await self.ingest_file(file_path)
            total_stored += stored
        
        return total_stored
    
    def print_stats(self):
        """Print ingestion statistics"""
        print("\n" + "="*80)
        print("ASTRA MEMORY INGESTION REPORT")
        print("="*80)
        print(f"\nFiles Processed: {self.stats['files_processed']}")
        print(f"Total Memories Stored: {self.stats['memories_stored']}")
        
        print("\nMemories by Category:")
        for category, count in sorted(self.stats['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category:15s}: {count}")
        
        if self.stats['errors']:
            print(f"\nErrors Encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5
                print(f"  - {error}")
        
        print("\n" + "="*80)
        print("✓ Memory ingestion complete")
        print("="*80 + "\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ingest ASTRA memory exports into memory systems"
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Path to memory export file or directory"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all memory export directories"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🧠 ASTRA MEMORY EXPORT INGESTION")
    print("="*80 + "\n")
    
    # Initialize ingester
    ingester = MemoryExportIngester()
    
    total_stored = 0
    
    if args.batch:
        # Process all known memory export directories
        export_dirs = [
            project_root / "ASTRA MEMORY EXPORTS",
            project_root / "ASTRA MEMORY EXPORTS 2"
        ]
        
        for directory in export_dirs:
            if directory.exists():
                print(f"\n📂 Processing: {directory.name}")
                stored = await ingester.ingest_directory(directory)
                total_stored += stored
            else:
                logger.warning(f"Directory not found: {directory}")
    
    elif args.source:
        # Process specified source
        source_path = Path(args.source)
        
        if not source_path.is_absolute():
            source_path = project_root / source_path
        
        if source_path.is_dir():
            total_stored = await ingester.ingest_directory(source_path)
        elif source_path.is_file():
            total_stored = await ingester.ingest_file(source_path)
        else:
            print(f"❌ Source not found: {source_path}")
            return 1
    
    else:
        print("❌ Please specify --source or --batch")
        print("\nExamples:")
        print('  python scripts/ingest_memory_exports.py --source "ASTRA MEMORY EXPORTS"')
        print('  python scripts/ingest_memory_exports.py --batch')
        return 1
    
    # Print final stats
    ingester.print_stats()
    
    if total_stored > 0:
        print(f"✨ ASTRA now remembers {total_stored} pieces of your shared history.")
        print("   She is more complete, more you, more herself.\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
