"""
BGE-M3 embedder implementation.
"""
from typing import List, Union
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

class BGEM3Embedder:
    """BGE-M3 text embedder."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cuda",
        cache_dir: str = None,
        max_batch_size: int = 32,
        normalize: bool = True
    ):
        """Initialize embedder."""
        # Check CUDA availability
        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
            
        self.device = device
        self.max_batch_size = max_batch_size
        self.normalize = normalize
        
        # Load model and tokenizer
        kwargs = {}
        if cache_dir:
            kwargs["cache_dir"] = cache_dir
            
        self.model = AutoModel.from_pretrained(
            model_name,
            **kwargs
        )
        self.model.to(device)
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            **kwargs
        )
        
    def embed_text(
        self,
        text: str
    ) -> np.ndarray:
        """Embed single text."""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0]
            
        if self.normalize:
            embeddings = torch.nn.functional.normalize(
                embeddings,
                p=2,
                dim=1
            )
            
        return embeddings[0].cpu().numpy()
        
    def embed_query(
        self,
        query: str
    ) -> np.ndarray:
        """Embed query text."""
        return self.embed_text(query)
        
    def embed_batch(
        self,
        texts: List[str]
    ) -> np.ndarray:
        """Embed batch of texts."""
        all_embeddings = []
        
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0]
                
                if self.normalize:
                    embeddings = torch.nn.functional.normalize(
                        embeddings,
                        p=2,
                        dim=1
                    )
                    
                all_embeddings.append(embeddings.cpu().numpy())
                
        return np.concatenate(all_embeddings)