# SPDX-License-Identifier: MIT
# src/services/llm_service.py
"""
LLM Service — Production-ready inference with prompt guard integration.

Supports:
- OpenAI API (gpt-4-turbo-preview, gpt-3.5-turbo)
- Local llama-cpp-python models
- Token counting (tiktoken)
- Cost tracking
- Prometheus metrics
"""
from __future__ import annotations
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge
    LLM_REQUESTS = Counter("llm_requests_total", "Total LLM requests", ["model", "status"])
    LLM_TOKENS = Counter("llm_tokens_total", "Total tokens used", ["model", "type"])
    LLM_LATENCY = Histogram("llm_latency_seconds", "LLM inference latency (s)", ["model"])
    LLM_COST = Counter("llm_cost_usd_total", "Total LLM cost (USD)", ["model"])
    LLM_ACTIVE = Gauge("llm_active_requests", "Active LLM requests")
except ImportError:
    # Fallback no-op metrics
    class NoOpMetric:
        def labels(self, **kwargs): return self
        def inc(self, val=1): pass
        def time(self): return self
        def __enter__(self): pass
        def __exit__(self, *args): pass
    LLM_REQUESTS = LLM_TOKENS = LLM_LATENCY = LLM_COST = LLM_ACTIVE = NoOpMetric()


class LLMProvider(str, Enum):
    OPENAI = "openai"
    LOCAL = "local"
    ANTHROPIC = "anthropic"  # Future


@dataclass
class LLMResponse:
    """Structured LLM response with metadata."""
    text: str
    model: str
    tokens_used: int
    cost_usd: float
    latency_seconds: float
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMService:
    """
    Unified LLM inference service with prompt guard integration.
    
    Usage:
        llm = LLMService(provider="openai", model="gpt-4-turbo-preview")
        resp = llm.generate("Hello world", max_tokens=512)
        print(f"Response: {resp.text}, Cost: ${resp.cost_usd:.4f}")
    """
    
    # Token pricing (USD per 1K tokens)
    PRICING = {
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    }
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4-turbo-preview",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ):
        self.provider = LLMProvider(provider)
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt or "You are ASTRA, a helpful AI assistant."
        
        # Initialize provider client
        if self.provider == LLMProvider.OPENAI:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            except ImportError:
                raise RuntimeError("OpenAI not installed: pip install openai")
        elif self.provider == LLMProvider.LOCAL:
            try:
                from llama_cpp import Llama
                model_path = os.getenv("LOCAL_MODEL_PATH", "models/llama-2-7b-chat.Q4_K_M.gguf")
                self.client = Llama(model_path=model_path, n_ctx=2048, n_threads=4)
            except ImportError:
                raise RuntimeError("llama-cpp-python not installed: pip install llama-cpp-python")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        """
        Generate LLM response with metrics tracking.
        
        Args:
            prompt: User prompt (should already be validated by prompt guard)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (overrides default)
            stop: Stop sequences
        
        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        temp = temperature if temperature is not None else self.temperature
        start_time = time.time()
        
        with LLM_ACTIVE.track_inprogress():
            try:
                if self.provider == LLMProvider.OPENAI:
                    resp = self._generate_openai(prompt, max_tokens, temp, stop)
                elif self.provider == LLMProvider.LOCAL:
                    resp = self._generate_local(prompt, max_tokens, temp, stop)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                
                # Track metrics
                LLM_REQUESTS.labels(model=self.model, status="success").inc()
                LLM_TOKENS.labels(model=self.model, type="input").inc(resp.metadata.get("prompt_tokens", 0))
                LLM_TOKENS.labels(model=self.model, type="output").inc(resp.metadata.get("completion_tokens", 0))
                LLM_COST.labels(model=self.model).inc(resp.cost_usd)
                
                resp.latency_seconds = time.time() - start_time
                with LLM_LATENCY.labels(model=self.model).time():
                    pass  # Record latency
                
                return resp
            
            except Exception as e:
                LLM_REQUESTS.labels(model=self.model, status="error").inc()
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


# ARCHIVE: OpenAI provider (disabled for offline sovereignty)
# To re-enable cloud providers:
# 1. Set network.egress_enabled=true in astra.yaml
# 2. Uncomment cloud provider code below
# 3. Add egress_enabled check in build_llm_from_config()

def _generate_openai_DISABLED(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list]
    ) -> Dict[str, Any]:
        """Generate using OpenAI API."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        
        # Calculate cost
        pricing = self.PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        cost_usd = (
            (prompt_tokens / 1000.0) * pricing["input"] +
            (completion_tokens / 1000.0) * pricing["output"]
        )
        
        return LLMResponse(
            text=response.choices[0].message.content,
            model=self.model,
            tokens_used=response.usage.total_tokens,
            cost_usd=cost_usd,
            latency_seconds=0.0,  # Set by caller
            finish_reason=response.choices[0].finish_reason,
            metadata={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "response_id": response.id,
            },
        )
    
    def _generate_local(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]],
    ) -> LLMResponse:
        """Generate using local llama-cpp model."""
        # Format prompt for chat template (Llama-2 style)
        formatted_prompt = f"<s>[INST] <<SYS>>\n{self.system_prompt}\n<</SYS>>\n\n{prompt} [/INST]"
        
        response = self.client(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or ["</s>", "[INST]"],
            echo=False,
        )
        
        text = response["choices"][0]["text"].strip()
        tokens_used = response["usage"]["total_tokens"]
        
        return LLMResponse(
            text=text,
            model=self.model,
            tokens_used=tokens_used,
            cost_usd=0.0,  # Local models are free
            latency_seconds=0.0,  # Set by caller
            finish_reason=response["choices"][0]["finish_reason"],
            metadata={
                "prompt_tokens": response["usage"]["prompt_tokens"],
                "completion_tokens": response["usage"]["completion_tokens"],
            },
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximate for local models).
        
        Uses tiktoken for OpenAI, rough estimate for local.
        """
        if self.provider == LLMProvider.OPENAI:
            try:
                import tiktoken
                enc = tiktoken.encoding_for_model(self.model)
                return len(enc.encode(text))
            except Exception:
                # Fallback: ~4 chars per token
                return len(text) // 4
        else:
            # Rough estimate for local models
            return len(text) // 4


# Convenience factory
def create_llm_service(config: Dict[str, Any]) -> LLMService:
    """
    Create LLM service from config dict.
    
    Example config:
        {
            "provider": "openai",
            "model": "gpt-4-turbo-preview",
            "temperature": 0.7,
            "system_prompt": "You are ASTRA..."
        }
    """
    return LLMService(
        provider=config.get("provider", "openai"),
        model=config.get("model", "gpt-4-turbo-preview"),
        api_key=config.get("api_key"),
        temperature=config.get("temperature", 0.7),
        system_prompt=config.get("system_prompt"),
    )


# Example usage
if __name__ == "__main__":
    import sys
    
    # Test OpenAI
    if os.getenv("OPENAI_API_KEY"):
        print("Testing OpenAI API...")
        llm = LLMService(provider="openai", model="gpt-3.5-turbo")
        resp = llm.generate("What is 2+2?", max_tokens=50)
        print(f"Response: {resp.text}")
        print(f"Tokens: {resp.tokens_used}, Cost: ${resp.cost_usd:.4f}, Latency: {resp.latency_seconds:.2f}s")
    else:
        print("OPENAI_API_KEY not set, skipping OpenAI test")
    
    # Test local (if model exists)
    local_model_path = os.getenv("LOCAL_MODEL_PATH", "models/llama-2-7b-chat.Q4_K_M.gguf")
    if os.path.exists(local_model_path):
        print("\nTesting local model...")
        llm = LLMService(provider="local", model=local_model_path)
        resp = llm.generate("What is 2+2?", max_tokens=50)
        print(f"Response: {resp.text}")
        print(f"Tokens: {resp.tokens_used}, Latency: {resp.latency_seconds:.2f}s")
    else:
        print(f"\nLocal model not found at {local_model_path}, skipping local test")
