"""
BAAI General Language Understanding Evaluation (GLUE) model for embeddings.
"""
from typing import List, Optional
import logging
from pathlib import Path
import time

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel, utils
import structlog
from tqdm.auto import tqdm

# Add download progress bar
utils.logging.enable_progress_bar()

from astra.embed.base import BaseEmbedder

logger = structlog.get_logger()

class BGEM3Embedder(BaseEmbedder):
    """Embedder using BGE-M3 model from BAAI."""
    
    def __init__(self, timeout: int = 30):
        """Initialize BGE-M3 embedder."""
        logging.basicConfig(level=logging.DEBUG)
        logger.debug("Initializing BGE embedder...")
        
        self.model_name = "BAAI/bge-base-en"  # Smaller model ~500MB
        self.timeout = timeout
        
        # Create cache dir if it doesn't exist
        cache_dir = Path("data/cache/embeddings")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        # Load tokenizer first to catch any issues early
        try:
            logger.debug("Loading tokenizer...")
            
            # Show progress for tokenizer download
            with tqdm(desc="Loading tokenizer", unit="files") as pbar:
                pbar.set_postfix({"status": "downloading"})
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    cache_dir=cache_dir,
                    local_files_only=False,  # Allow downloading if not in cache
                    use_fast=True  # Use faster tokenizer implementation
                )
                pbar.update(1)
                pbar.set_postfix({"status": "completed"})
            
            logger.debug("Tokenizer loaded successfully")
        except Exception as e:
            logger.error("Failed to load tokenizer", error=str(e))
            raise
        
        try:
            # Check if we've exceeded timeout
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Model initialization exceeded {self.timeout}s timeout")
            
            # Load model with explicit caching and progress bar
            logger.debug("Loading model...")
            with tqdm(desc="Loading model", unit="files") as pbar:
                pbar.set_postfix({"status": "downloading"})
                try:
                    # Try loading with safetensors first
                    self.model = AutoModel.from_pretrained(
                        self.model_name,
                        cache_dir=cache_dir,
                        local_files_only=False,
                        use_safetensors=True,
                        trust_remote_code=False,  # Safety measure
                        torch_dtype=torch.float32  # Use fp32 for CPU
                    )
                    pbar.update(1)
                    pbar.set_postfix({"status": "completed", "format": "safetensors"})
                    logger.debug("Model loaded successfully using safetensors")
                except Exception as e:
                    if "cannot find model.safetensors" in str(e).lower():
                        logger.debug("Retrying without safetensors...")
                        pbar.set_postfix({"status": "retrying", "format": "pytorch"})
                        self.model = AutoModel.from_pretrained(
                            self.model_name,
                            cache_dir=cache_dir,
                            local_files_only=False,
                            use_safetensors=False,
                            trust_remote_code=False,
                            torch_dtype=torch.float32
                        )
                        pbar.update(1)
                        pbar.set_postfix({"status": "completed", "format": "pytorch"})
                        logger.debug("Model loaded successfully using pytorch format")
                    else:
                        raise
        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            raise
        
        # Set up device
        logger.debug("Setting up device...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(
            "initialized_bge_embedder",
            model=self.model_name,
            device=self.device
        )
        self.model.to(self.device)
        logger.debug("Model moved to device successfully")

    def _text_to_tensor(
        self,
        texts: List[str],
        max_length: Optional[int] = 512
    ) -> torch.Tensor:
        """Convert text to input tensors.
        
        Args:
            texts: List of text strings to convert
            max_length: Maximum sequence length
            
        Returns:
            Input tensors for model
        """
        encoded = self.tokenizer.batch_encode_plus(
            texts,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        return encoded.to(self.device)

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """Embed documents using BGE-M3.
        
        Args:
            documents: List of text documents to embed
            
        Returns:
            Array of shape (len(documents), 1024) containing embeddings
        """
        with torch.no_grad():
            tensors = self._text_to_tensor(documents)
            outputs = self.model(**tensors)
            # Get CLS token embedding
            embeddings = outputs.last_hidden_state[:, 0]
            return embeddings.cpu().numpy()