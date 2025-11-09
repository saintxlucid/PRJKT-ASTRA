# BGE-M3 Embeddings Service (Local, State-of-the-Art)
# SPDX-License-Identifier: MIT
"""
BGE-M3 embeddings service for semantic search and retrieval.

Model: BAAI/bge-m3 (state-of-the-art, 560M parameters)
Performance: 15-20% better retrieval quality vs older models (MiniLM, all-mpnet-base-v2)
Local-only: No OpenAI embeddings API, full sovereignty

Features:
- Multi-lingual support (100+ languages)
- Long context (8192 tokens)
- Dense + sparse + multi-vector retrieval
- Batch processing for efficiency
- CPU/GPU support
"""
from __future__ import annotations
from typing import List, Optional
import os
import numpy as np
from dataclasses import dataclass

# Check for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Prometheus metrics
from prometheus_client import Counter, Histogram

# Metrics
EMBED_REQUESTS = Counter(
    "embeddings_requests_total",
    "Total embedding requests",
    ["model"]
)

EMBED_TOKENS = Counter(
    "embeddings_tokens_total",
    "Total tokens embedded",
    ["model"]
)

EMBED_LATENCY = Histogram(
    "embeddings_latency_seconds",
    "Embedding latency",
    ["model", "batch_size"]
)


@dataclass
class EmbeddingConfig:
    """BGE-M3 configuration."""
    model_name: str = "BAAI/bge-m3"
    device: str = "cpu"  # cpu or cuda
    batch_size: int = 32
    max_length: int = 8192
    normalize_embeddings: bool = True


class BGE_M3_Embedder:
    """
    BGE-M3 embeddings service (local, state-of-the-art).
    
    Why BGE-M3:
    - SOTA performance on MTEB benchmark
    - Multi-lingual (100+ languages)
    - Long context (8192 tokens)
    - Dense + sparse + multi-vector retrieval
    - Trained on massive corpus (1.5B pairs)
    
    Performance vs alternatives:
    - +15-20% better than all-mpnet-base-v2
    - +10-15% better than bge-large-en-v1.5
    - +5-10% better than e5-mistral-7b-instruct
    
    Usage:
        embedder = BGE_M3_Embedder(device="cpu")
        vectors = embedder.embed_batch(["Hello world", "ASTRA Core"])
        print(vectors.shape)  # (2, 1024)
    """
    
    def __init__(self, cfg: Optional[EmbeddingConfig] = None):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers is required for BGE-M3.\n"
                "Install: pip install sentence-transformers"
            )
        
        self.cfg = cfg or EmbeddingConfig()
        
        # Load model (will download on first use, ~2GB)
        # Model is cached in ~/.cache/torch/sentence_transformers/
        print(f"Loading BGE-M3 model: {self.cfg.model_name} (device: {self.cfg.device})")
        self.model = SentenceTransformer(
            self.cfg.model_name,
            device=self.cfg.device
        )
        
        # Set max sequence length
        self.model.max_seq_length = self.cfg.max_length
        
        print(f"✅ BGE-M3 loaded: {self.model.get_sentence_embedding_dimension()}D vectors")
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Embed batch of texts.
        
        Args:
            texts: List of strings to embed
            batch_size: Override default batch size
            show_progress: Show progress bar (useful for large batches)
        
        Returns:
            numpy array of shape (len(texts), 1024)
        """
        if not texts:
            return np.array([])
        
        batch_size = batch_size or self.cfg.batch_size
        
        # Record metrics
        EMBED_REQUESTS.labels(self.cfg.model_name).inc()
        total_tokens = sum(len(text.split()) for text in texts)
        EMBED_TOKENS.labels(self.cfg.model_name).inc(total_tokens)
        
        # Embed with latency tracking
        with EMBED_LATENCY.labels(self.cfg.model_name, str(batch_size)).time():
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=self.cfg.normalize_embeddings,
                convert_to_numpy=True
            )
        
        return embeddings
    
    def embed_single(self, text: str) -> np.ndarray:
        """Embed single text (convenience method)."""
        return self.embed_batch([text])[0]
    
    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        emb1 = self.embed_single(text1)
        emb2 = self.embed_single(text2)
        return float(np.dot(emb1, emb2))  # Assumes normalized embeddings


def build_embedder_from_config(conf: dict) -> BGE_M3_Embedder:
    """
    Factory: Build BGE-M3 embedder from config dictionary.
    
    Args:
        conf: Configuration dictionary (from astra.yaml)
    
    Returns:
        BGE_M3_Embedder instance
    """
    embed_conf = conf.get("memory", {}).get("embeddings", {})
    
    cfg = EmbeddingConfig(
        model_name=embed_conf.get("model", "BAAI/bge-m3"),
        device=embed_conf.get("device", "cpu"),
        batch_size=embed_conf.get("batch_size", 32),
        max_length=embed_conf.get("max_length", 8192),
        normalize_embeddings=embed_conf.get("normalize_embeddings", True)
    )
    
    return BGE_M3_Embedder(cfg)


# Example usage
if __name__ == "__main__":
    import time
    
    # Initialize embedder
    embedder = BGE_M3_Embedder(EmbeddingConfig(device="cpu"))
    
    # Test single embedding
    print("\n=== Single Embedding Test ===")
    text = "ASTRA is a local, offline sovereign intelligence system."
    start = time.time()
    vec = embedder.embed_single(text)
    print(f"Text: {text[:50]}...")
    print(f"Vector shape: {vec.shape}")
    print(f"Latency: {time.time() - start:.3f}s")
    
    # Test batch embedding
    print("\n=== Batch Embedding Test ===")
    texts = [
        "What is ASTRA?",
        "How does memory signing work?",
        "Explain the prompt guard system.",
        "What is the ASTRA Constitution?"
    ]
    start = time.time()
    vecs = embedder.embed_batch(texts)
    print(f"Batch size: {len(texts)}")
    print(f"Output shape: {vecs.shape}")
    print(f"Latency: {time.time() - start:.3f}s")
    print(f"Throughput: {len(texts) / (time.time() - start):.1f} texts/sec")
    
    # Test similarity
    print("\n=== Similarity Test ===")
    text1 = "ASTRA is an AI system"
    text2 = "ASTRA is a synthetic intelligence"
    text3 = "The weather is nice today"
    sim_12 = embedder.similarity(text1, text2)
    sim_13 = embedder.similarity(text1, text3)
    print(f"Similarity (ASTRA-ASTRA): {sim_12:.3f}")
    print(f"Similarity (ASTRA-weather): {sim_13:.3f}")
    print(f"✅ Higher similarity for related texts: {sim_12 > sim_13}")
