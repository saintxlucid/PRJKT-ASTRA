"""
Core ingestion pipeline implementation.
"""
import yaml
import structlog
from pathlib import Path
from typing import List, Dict, Any

from astra.rag.processor.pdf import PDFProcessor
from astra.parse.sliding import VectorSlider, SlidingConfig
from astra.embed.bge import BGEM3Embedder
from astra.rag.indexes import DenseIndex

logger = structlog.get_logger(__name__)

class IngestionPipeline:
    """
    Coordinates the process of parsing, chunking, embedding, and indexing documents.
    """

    def __init__(self, processor, chunker, embedder, index):
        self.processor = processor
        self.chunker = chunker
        self.embedder = embedder
        self.index = index

    @classmethod
    def from_config(cls, config_path: str):
        """
        Creates an IngestionPipeline instance from a YAML configuration file.
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Initialize document processor with config
        logger.debug("Initializing document processor")
        processor_config = config.get('processor', {})
        processor = PDFProcessor(
            min_chunk_chars=processor_config.get('min_chunk_chars', 200),
            max_chunk_chars=processor_config.get('max_chunk_chars', 1000),
            overlap_chars=processor_config.get('overlap_chars', 50),
            merge_threshold=processor_config.get('merge_threshold', 50)
        )
        
        # Initialize vector sliding for reranking
        logger.debug("Loading vector sliding config")
        sliding_config_data = config.get('vector_sliding', {})
        logger.debug(f"Vector sliding config data: {sliding_config_data}")
        sliding_config = SlidingConfig(
            sim_threshold=sliding_config_data.get('similarity_threshold', 0.8),
            max_merge_tokens=sliding_config_data.get('max_merge_tokens', 512)
        )
        
        logger.debug("Initializing embedder")
        embedder = BGEM3Embedder()
        logger.debug("Embedder initialized")
        
        logger.debug("Initializing chunker")
        chunker = VectorSlider(embedder=embedder, config=sliding_config)
        
        # Initialize dense index
        logger.debug("Initializing dense index")
        index = DenseIndex.from_config(config)
        logger.debug("Pipeline initialization complete")

        return cls(processor, chunker, embedder, index)

    async def run(self, file_path: Path) -> bool:
        """
        Runs the full ingestion process for a single file.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            True if ingestion succeeded, False otherwise
            
        Raises:
            ValueError: If file type is unsupported or file is invalid
            RuntimeError: If ingestion fails critically
        """
        logger.info("ingestion_run_started", file=str(file_path))
        
        try:
            # 1. Validate input
            if not file_path.exists():
                raise ValueError(f"File does not exist: {file_path}")
                
            if file_path.suffix.lower() != '.pdf':
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
                
            if file_path.stat().st_size == 0:
                raise ValueError(f"File is empty: {file_path}")

            # 2. Process document with layout-aware parsing
            logger.debug("processing_document", file=str(file_path))
            try:
                initial_chunks = self.processor.process(file_path)
                logger.info("document_processed", 
                           num_chunks=len(initial_chunks),
                           file=str(file_path))
            except Exception as e:
                raise RuntimeError(f"Failed to process document: {e}")

            if not initial_chunks:
                raise ValueError("Document processing produced no chunks")

            # 3. Merge chunks using vector sliding with progress
            logger.debug("merging_chunks", count=len(initial_chunks))
            try:
                # Extract text and keep metadata
                texts = [chunk["text"] for chunk in initial_chunks]
                metadata = [chunk["metadata"] for chunk in initial_chunks]
                
                # Merge text chunks
                merged_text_chunks = self.chunker.merge_chunks(
                    texts,
                    self.embedder
                )
                logger.info("chunks_merged", 
                           input_chunks=len(texts),
                           output_chunks=len(merged_text_chunks))
                           
                # Match merged chunks with metadata
                # For now, use metadata from first chunk that was merged
                chunk_mapping = self.chunker.get_chunk_mapping()
                merged_chunks = []
                
                for i, text in enumerate(merged_text_chunks):
                    source_indices = chunk_mapping[i]
                    merged_metadata = metadata[source_indices[0]]
                    merged_chunks.append({
                        "text": text,
                        "metadata": merged_metadata
                    })
                    
            except Exception as e:
                raise RuntimeError(f"Failed to merge chunks: {e}")

            # 4. Prepare chunk vectors
            logger.debug("preparing_vectors")
            chunk_vectors = []
            chunk_metadata = []
            
            for chunk in merged_chunks:
                # Embed the chunk
                vector = self.embedder.embed_documents([chunk["text"]])[0]
                chunk_vectors.append(vector)
                chunk_metadata.append(chunk["metadata"])

            # 5. Index the chunks with retries
            logger.debug("indexing_chunks", count=len(merged_chunks))
            collection = "documents"  # Could be configurable
            max_retries = 3
            retry = 0
            
            while retry < max_retries:
                try:
                    success = await self.index.upsert(
                        vectors=chunk_vectors,
                        collection=collection,
                        metadata=chunk_metadata
                    )
                    if success:
                        break
                    retry += 1
                except Exception as e:
                    logger.warning("index_retry", 
                                 attempt=retry + 1,
                                 error=str(e))
                    retry += 1
                    if retry == max_retries:
                        raise RuntimeError(f"Failed to index chunks after {max_retries} attempts: {e}")

            logger.info("ingestion_run_complete", 
                       file=str(file_path),
                       chunks_indexed=len(merged_chunks))
            return True

        except ValueError as e:
            # Input validation errors
            logger.error("ingestion_validation_error",
                        file=str(file_path),
                        error=str(e))
            raise
            
        except RuntimeError as e:
            # Processing errors
            logger.error("ingestion_processing_error",
                        file=str(file_path),
                        error=str(e))
            raise
            
        except Exception as e:
            # Unexpected errors
            logger.error("ingestion_unexpected_error",
                        file=str(file_path),
                        error=str(e))
            raise RuntimeError(f"Unexpected error during ingestion: {e}")
            
