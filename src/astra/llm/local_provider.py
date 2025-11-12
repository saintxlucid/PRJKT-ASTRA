"""
🚀 ASTRA Local GPT OOS Provider

Fully offline, local-first LLM provider for sovereign AI operations.
No external API dependencies. Streaming, batching, and resource management built-in.

Sacred Code: 333 → ∞
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Optional, Iterator, AsyncIterator, Dict, Any
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class InferenceBackend(str, Enum):
    """Supported inference backends for local LLM execution."""
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    CTRANSFORMERS = "ctransformers"
    VLLM = "vllm"
    GPT_OOS = "gpt_oos"


@dataclass
class InferenceConfig:
    """Configuration for local inference."""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    repetition_penalty: float = 1.0
    stream: bool = True
    echo: bool = False


@dataclass
class InferenceMetrics:
    """Metrics for a single inference."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    first_token_latency_ms: float  # Time to first token
    total_latency_ms: float
    throughput_tokens_per_sec: float
    timestamp: float


class GPTOOSProvider:
    """
    Local GPT OOS Provider: Fully offline LLM inference.
    
    - Loads model from local path (no network required)
    - Streaming support for responsiveness
    - Token counting for budgets
    - Metrics collection (latency, throughput)
    - Graceful degradation if model unavailable
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        backend: InferenceBackend = InferenceBackend.OLLAMA,
        config: Optional[InferenceConfig] = None,
        device: str = "auto",
    ):
        """
        Initialize local GPT OOS provider.
        
        Args:
            model_path: Path to local model (or Ollama model name)
            backend: Inference backend (ollama, llamacpp, ctransformers, vllm, gpt_oos)
            config: Inference configuration
            device: Device to run on (auto, cuda, cpu, mps)
        """
        self.model_path = model_path or "mistral:latest"  # Default to Ollama's Mistral
        self.backend = backend
        self.config = config or InferenceConfig()
        self.device = device
        self.model = None
        self.tokenizer = None
        self.metrics_history = []
        self._initialized = False

        logger.info(
            "gpt_oos_provider_init",
            model_path=self.model_path,
            backend=self.backend.value,
            device=self.device,
        )

        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize the inference backend (lazy load on first use)."""
        try:
            if self.backend == InferenceBackend.OLLAMA:
                self._init_ollama()
            elif self.backend == InferenceBackend.LLAMACPP:
                self._init_llamacpp()
            elif self.backend == InferenceBackend.CTRANSFORMERS:
                self._init_ctransformers()
            elif self.backend == InferenceBackend.VLLM:
                self._init_vllm()
            elif self.backend == InferenceBackend.GPT_OOS:
                self._init_gpt_oos()
            self._initialized = True
            logger.info("backend_initialized", backend=self.backend.value)
        except Exception as e:
            logger.error("backend_initialization_failed", error=str(e), backend=self.backend.value)
            self._initialized = False

    def _init_ollama(self) -> None:
        """Initialize Ollama backend (requires local Ollama server running)."""
        try:
            import ollama
            self.ollama_client = ollama.Client()
            logger.info("ollama_backend_ready", model=self.model_path)
        except ImportError:
            logger.warning("ollama_not_installed", hint="pip install ollama")

    def _init_llamacpp(self) -> None:
        """Initialize llama.cpp backend (local compiled C++ inference)."""
        try:
            from llama_cpp import Llama
            self.model = Llama(
                model_path=self.model_path,
                device=self.device,
                n_ctx=4096,
                n_threads=4,
            )
            logger.info("llamacpp_backend_ready", model_path=self.model_path)
        except ImportError:
            logger.warning("llamacpp_not_installed", hint="pip install llama-cpp-python")

    def _init_ctransformers(self) -> None:
        """Initialize CTransformers backend (optimized C++ transformers)."""
        try:
            from ctransformers import AutoModelForCausalLM
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                model_type="mistral",
                gpu_layers=0 if self.device == "cpu" else 50,
            )
            logger.info("ctransformers_backend_ready", model_path=self.model_path)
        except ImportError:
            logger.warning("ctransformers_not_installed", hint="pip install ctransformers")

    def _init_vllm(self) -> None:
        """Initialize vLLM backend (high-throughput inference engine)."""
        try:
            from vllm import LLM, SamplingParams
            self.model = LLM(model=self.model_path, device=self.device)
            logger.info("vllm_backend_ready", model=self.model_path)
        except ImportError:
            logger.warning("vllm_not_installed", hint="pip install vllm")

    def _init_gpt_oos(self) -> None:
        """Initialize GPT OOS native backend (if available)."""
        try:
            import gpt_oos_core
            self.model = gpt_oos_core.Model(self.model_path)
            logger.info("gpt_oos_backend_ready", model_path=self.model_path)
        except ImportError:
            logger.warning("gpt_oos_not_installed", hint="Include GPT OOS binaries in models/gpt_oos_core/")

    def generate(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> str:
        """
        Synchronous generation (blocking).
        
        Args:
            prompt: Input prompt
            config: Optional override config
            
        Returns:
            Generated text
        """
        if not self._initialized:
            logger.error("backend_not_initialized")
            return ""

        config = config or self.config
        start_time = time.time()

        try:
            if self.backend == InferenceBackend.OLLAMA:
                response = self.ollama_client.generate(
                    model=self.model_path,
                    prompt=prompt,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    num_predict=config.max_tokens,
                    stream=False,
                )
                text = response["response"]
            elif self.backend == InferenceBackend.LLAMACPP:
                response = self.model(
                    prompt,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    echo=config.echo,
                )
                text = response["choices"][0]["text"]
            elif self.backend == InferenceBackend.CTRANSFORMERS:
                text = self.model(
                    prompt,
                    max_new_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                )
            elif self.backend == InferenceBackend.VLLM:
                from vllm import SamplingParams
                sampling_params = SamplingParams(
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_tokens=config.max_tokens,
                )
                outputs = self.model.generate([prompt], sampling_params)
                text = outputs[0].outputs[0].text
            else:
                text = ""

            latency_ms = (time.time() - start_time) * 1000
            tokens = len(text.split())

            logger.info(
                "inference_complete",
                backend=self.backend.value,
                latency_ms=latency_ms,
                tokens=tokens,
            )

            return text

        except Exception as e:
            logger.error("inference_failed", error=str(e), backend=self.backend.value)
            return ""

    async def generate_async(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> str:
        """
        Asynchronous generation (non-blocking).
        
        Args:
            prompt: Input prompt
            config: Optional override config
            
        Returns:
            Generated text
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt, config)

    def stream(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> Iterator[str]:
        """
        Streaming generation (yields tokens as they arrive).
        
        Args:
            prompt: Input prompt
            config: Optional override config
            
        Yields:
            Text chunks
        """
        if not self._initialized:
            logger.error("backend_not_initialized")
            return

        config = config or self.config
        start_time = time.time()
        first_token_time = None
        total_tokens = 0

        try:
            if self.backend == InferenceBackend.OLLAMA:
                response = self.ollama_client.generate(
                    model=self.model_path,
                    prompt=prompt,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    num_predict=config.max_tokens,
                    stream=True,
                )
                for chunk in response:
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                    text = chunk.get("response", "")
                    total_tokens += len(text.split())
                    yield text

            elif self.backend == InferenceBackend.LLAMACPP:
                response = self.model(
                    prompt,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    stream=True,
                )
                for chunk in response:
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                    text = chunk["choices"][0]["text"]
                    total_tokens += len(text.split())
                    yield text

            total_latency_ms = (time.time() - start_time) * 1000
            first_token_latency_ms = (first_token_time * 1000) if first_token_time else total_latency_ms

            metrics = InferenceMetrics(
                prompt_tokens=len(prompt.split()),
                completion_tokens=total_tokens,
                total_tokens=len(prompt.split()) + total_tokens,
                first_token_latency_ms=first_token_latency_ms,
                total_latency_ms=total_latency_ms,
                throughput_tokens_per_sec=total_tokens / (total_latency_ms / 1000) if total_latency_ms > 0 else 0,
                timestamp=time.time(),
            )
            self.metrics_history.append(metrics)

            logger.info(
                "streaming_complete",
                backend=self.backend.value,
                first_token_latency_ms=first_token_latency_ms,
                total_latency_ms=total_latency_ms,
                throughput=metrics.throughput_tokens_per_sec,
            )

        except Exception as e:
            logger.error("streaming_failed", error=str(e), backend=self.backend.value)

    async def stream_async(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Asynchronous streaming generation.
        
        Args:
            prompt: Input prompt
            config: Optional override config
            
        Yields:
            Text chunks
        """
        loop = asyncio.get_event_loop()
        
        # Run generator in thread pool
        def stream_sync():
            for chunk in self.stream(prompt, config):
                yield chunk
        
        for chunk in await loop.run_in_executor(None, lambda: list(stream_sync())):
            yield chunk

    def get_metrics(self) -> Dict[str, Any]:
        """Get inference metrics summary."""
        if not self.metrics_history:
            return {"message": "No metrics available"}

        last_10 = self.metrics_history[-10:]
        avg_first_token_latency = sum(m.first_token_latency_ms for m in last_10) / len(last_10)
        avg_total_latency = sum(m.total_latency_ms for m in last_10) / len(last_10)
        avg_throughput = sum(m.throughput_tokens_per_sec for m in last_10) / len(last_10)

        return {
            "backend": self.backend.value,
            "model": self.model_path,
            "device": self.device,
            "total_inferences": len(self.metrics_history),
            "recent_metrics": {
                "avg_first_token_latency_ms": avg_first_token_latency,
                "avg_total_latency_ms": avg_total_latency,
                "avg_throughput_tokens_per_sec": avg_throughput,
            },
            "last_inference": self.metrics_history[-1].__dict__ if self.metrics_history else None,
        }

    def validate_offline(self) -> bool:
        """
        Validate that the provider can operate offline.
        
        Returns:
            True if all offline validation checks pass
        """
        checks = {
            "initialized": self._initialized,
            "model_loaded": self.model is not None,
            "backend_available": self.backend in [InferenceBackend.LLAMACPP, InferenceBackend.VLLM],
        }

        if all(checks.values()):
            logger.info("offline_validation_passed", checks=checks)
            return True
        else:
            logger.warning("offline_validation_failed", checks=checks)
            return False
