# SPDX-License-Identifier: MIT
"""
LLM Service (Local-Only, Offline Sovereign)
Local-first LLM inference with llama.cpp backend.

NETWORK POLICY: egress_enabled=false (no cloud providers allowed)
This module enforces offline sovereignty - no OpenAI, Anthropic, or any cloud API.

Supports:
- Local models via llama-cpp-python (GGUF format)
- Optimized for GPT-OSS-20B and similar offline models
- CPU-first (GPU offload configurable)

Features:
- Token counting (llama.cpp tokenizer)
- Prometheus metrics (requests, tokens, latency)
- Hard guardrails against accidental cloud usage
- Graceful error handling
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os
import time

# Prometheus metrics
from prometheus_client import Counter, Histogram

# CRITICAL: No cloud SDK imports allowed
# If you need to add cloud providers, they MUST be behind egress_enabled=true check

# Local model support (REQUIRED for offline operation)
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError as e:
    raise RuntimeError(
        "llama-cpp-python is REQUIRED for local-only operation. "
        "Install: pip install llama-cpp-python"
    ) from e


# Prometheus metrics (local-only, no cost tracking)
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model"]  # provider: llamacpp
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    ["direction"]  # direction: prompt, completion
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "LLM inference latency",
    ["provider", "model"]
)


@dataclass
class LLMConfig:
    """Local LLM configuration (llama.cpp)."""
    model_path: str
    n_ctx: int = 8192
    n_threads: int = 8
    n_gpu_layers: int = 0  # 0 = CPU-only (safe for GTX 1650)
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    seed: Optional[int] = None


@dataclass
class LLMResponse:
    """Structured LLM response (local-only, no cost tracking)."""
    text: str
    model: str
    provider: str
    usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y}
    latency_seconds: float
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalLlamaClient:
    """
    Local-only LLM client using llama.cpp backend.
    
    NETWORK POLICY: Enforces offline sovereignty - no cloud API calls.
    Optimized for GPT-OSS-20B and similar GGUF models.
    
    Usage:
        cfg = LLMConfig(model_path="models/gpt-oss-20b.q5_k_m.gguf")
        client = LocalLlamaClient(cfg)
        response = client.chat("What is ASTRA?", system="You are ASTRA Core.")
        print(f"Response: {response['text']}")
        print(f"Tokens: {response['usage']}")
    """
    
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        
        # Validate model exists
        if not os.path.exists(cfg.model_path):
            raise FileNotFoundError(
                f"Model not found: {cfg.model_path}\n"
                f"Download a GGUF model (e.g., GPT-OSS-20B) and place in models/ directory."
            )
        
        # Initialize llama.cpp model
        self.llm = Llama(
            model_path=cfg.model_path,
            n_ctx=cfg.n_ctx,
            n_threads=cfg.n_threads,
            n_gpu_layers=cfg.n_gpu_layers,
            seed=cfg.seed or -1,
            logits_all=False,
            verbose=False,
        )
        
        self.provider = "llamacpp"
        self.model = os.path.basename(cfg.model_path)
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens using llama.cpp tokenizer.
        
        This is accurate for the loaded model's vocabulary.
        """
        try:
            return len(self.llm.tokenize(text.encode("utf-8")))
        except Exception:
            # Fallback to rough estimate if tokenization fails
            return len(text) // 4
    
    def chat(
        self,
        prompt: str,
        system: str = "",
        stop: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Chat completion with local model.
        
        Args:
            prompt: User message
            system: System prompt (optional)
            stop: Stop sequences (e.g., ["<<USER>>", "<<ASSISTANT>>"])
        
        Returns:
            Dict with text, model, provider, usage, latency
        """
        stop = stop or []
        
        # Count tokens
        prompt_tokens = self.count_tokens(prompt)
        if system:
            prompt_tokens += self.count_tokens(system)
        
        # Record request
        LLM_REQUESTS.labels(self.provider, self.model).inc()
        LLM_TOKENS.labels("prompt").inc(prompt_tokens)
        
        # Build chat prompt (Llama-2 style template)
        # Adjust format for your specific model's chat template
        if system:
            full_prompt = f"<<SYS>> {system} <</SYS>>\n\n<<USER>> {prompt} <</USER>>\n<<ASSISTANT>>"
        else:
            full_prompt = f"<<USER>> {prompt} <</USER>>\n<<ASSISTANT>>"
        
        # Generate with latency tracking
        start_time = time.time()
        try:
            with LLM_LATENCY.labels(self.provider, self.model).time():
                output = self.llm(
                    full_prompt,
                    max_tokens=self.cfg.max_tokens,
                    temperature=self.cfg.temperature,
                    top_p=self.cfg.top_p,
                    stop=stop,
                )
            
            text = output["choices"][0]["text"]
            completion_tokens = self.count_tokens(text)
            LLM_TOKENS.labels("completion").inc(completion_tokens)
            
            latency = time.time() - start_time
            
            return {
                "text": text,
                "model": self.model,
                "provider": self.provider,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
                "latency_seconds": latency,
            }
            
        except Exception as e:
            raise RuntimeError(f"Local LLM generation failed: {e}") from e


def build_llm_from_config(conf: Dict[str, Any]) -> LocalLlamaClient:
    """
    Factory: Build local LLM client from config dictionary.
    
    NETWORK POLICY: Enforces offline sovereignty.
    - If egress_enabled=false (default), only llamacpp provider allowed.
    - If egress_enabled=true, raises error (cloud providers disabled).
    
    Args:
        conf: Configuration dictionary (from astra.yaml)
    
    Returns:
        LocalLlamaClient instance
    
    Raises:
        RuntimeError: If egress enabled or non-local provider specified
    """
    # Check network policy
    egress_enabled = conf.get("network", {}).get("egress_enabled", False)
    if egress_enabled:
        raise RuntimeError(
            "Network egress is DISABLED for ASTRA Core.\n"
            "Set network.egress_enabled=false in astra.yaml to enforce offline sovereignty."
        )
    
    # Check provider
    llm_conf = conf.get("llm", {})
    provider = (llm_conf.get("provider") or "llamacpp").lower()
    
    if provider != "llamacpp":
        raise RuntimeError(
            f"Offline mode: only 'llamacpp' provider is permitted (got '{provider}').\n"
            "Cloud providers (openai, anthropic) are disabled for sovereignty."
        )
    
    # Validate model_path
    model_path = llm_conf.get("model_path")
    if not model_path:
        raise ValueError(
            "llm.model_path is required in astra.yaml.\n"
            "Example: models/gpt-oss-20b.q5_k_m.gguf"
        )
    
    # Build config
    cfg = LLMConfig(
        model_path=model_path,
        n_ctx=llm_conf.get("n_ctx", 8192),
        n_threads=llm_conf.get("n_threads", 8),
        n_gpu_layers=llm_conf.get("n_gpu_layers", 0),
        temperature=llm_conf.get("temperature", 0.7),
        top_p=llm_conf.get("top_p", 0.9),
        max_tokens=llm_conf.get("max_tokens", 512),
        seed=llm_conf.get("seed"),
    )
    
    return LocalLlamaClient(cfg)
