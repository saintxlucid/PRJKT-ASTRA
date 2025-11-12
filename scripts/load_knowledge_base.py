"""
Load knowledge base from various sources (Hugging Face, GitHub, local files).
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from tqdm import tqdm

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Load documents from multiple sources for vector store ingestion."""
    
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
    
    async def load_from_local_files(
        self,
        directory: Path,
        extensions: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Load documents from local files."""
        if extensions is None:
            extensions = [".md", ".txt"]
        
        documents = []
        directory = Path(directory)
        
        for ext in extensions:
            for file_path in directory.glob(f"**/*{ext}"):
                try:
                    with open(file_path) as f:
                        content = f.read()
                        documents.append({
                            "text": content,
                            "source": str(file_path.relative_to(directory)),
                            "category": file_path.parent.name,
                        })
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
        
        logger.info(f"Loaded {len(documents)} documents from {directory}")
        return documents
    
    async def load_from_huggingface(
        self,
        dataset_name: str,
        text_column: str = "text",
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Load documents from Hugging Face datasets."""
        try:
            from datasets import load_dataset
        except ImportError:
            logger.error("datasets package required. Install with: pip install datasets")
            return []
        
        try:
            dataset = load_dataset(dataset_name, split="train")
            
            documents = []
            for i, example in enumerate(tqdm(dataset, desc=f"Loading {dataset_name}")):
                if limit and i >= limit:
                    break
                
                documents.append({
                    "text": example[text_column],
                    "source": dataset_name,
                    "category": "huggingface",
                })
            
            logger.info(f"Loaded {len(documents)} documents from Hugging Face")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to load from Hugging Face: {e}")
            return []
    
    async def load_from_github(
        self,
        repo_url: str,
        file_extensions: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Load documents from GitHub repository (via raw.githubusercontent.com)."""
        if file_extensions is None:
            file_extensions = [".py", ".md"]

        documents = []

        # Parse repo URL
        try:
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
        except Exception as e:
            logger.error(f"Invalid GitHub URL: {e}")
            return []

        logger.info(f"Loading from GitHub: {owner}/{repo}")

        # Note: In production, implement recursive GitHub API traversal
        # For now, return empty with log
        logger.warning("GitHub loading not fully implemented - use local files or Hugging Face")

        return documents
    
    async def batch_process(
        self,
        documents: list[dict[str, Any]],
        chunk_size: int = 1000  # Characters per chunk
    ) -> list[dict[str, Any]]:
        """Split large documents into chunks."""
        chunked = []
        
        for doc in documents:
            text = doc["text"]
            
            # Split by paragraphs first
            paragraphs = text.split("\n\n")
            
            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) < chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunked.append({
                            **doc,
                            "text": current_chunk.strip(),
                        })
                    current_chunk = para + "\n\n"
            
            if current_chunk:
                chunked.append({
                    **doc,
                    "text": current_chunk.strip(),
                })
        
        logger.info(f"Chunked {len(documents)} documents into {len(chunked)} chunks")
        return chunked
    
    async def load_and_prepare(
        self,
        sources: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Load from multiple sources and prepare for ingestion."""
        all_documents = []
        
        # Load from local files
        if "local_files" in sources:
            docs = await self.load_from_local_files(**sources["local_files"])
            all_documents.extend(docs)
        
        # Load from Hugging Face
        if "huggingface" in sources:
            for dataset in sources["huggingface"]:
                docs = await self.load_from_huggingface(**dataset)
                all_documents.extend(docs)
        
        # Batch process
        all_documents = await self.batch_process(all_documents)
        
        logger.info(f"Total documents prepared: {len(all_documents)}")
        return all_documents


async def main():
    """Example usage."""
    loader = KnowledgeBaseLoader()
    
    # Load from local project docs
    sources = {
        "local_files": {
            "directory": Path("./docs"),
            "extensions": [".md", ".txt"]
        }
    }
    
    documents = await loader.load_and_prepare(sources)
    
    # Print sample
    if documents:
        print(f"Loaded {len(documents)} documents")
        print(f"First doc: {documents[0]['text'][:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
