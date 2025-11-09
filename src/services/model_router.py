# SPDX-License-Identifier: MIT
"""
Multi-Model Router for ASTRA Core
==================================

Intelligent routing layer that dispatches requests to specialized models based on:
- Input modality (text, image, audio, video)
- Task type (reasoning, vision, fast-chat, ASR)
- Resource constraints (CPU, GPU, latency requirements)

Architecture:
    Gateway (vLLM OpenAI-compatible) + Sidecars (llama.cpp, TensorRT-LLM)
    → Policy-based routing with fallbacks
    → Telemetry & cost tracking per model

Models Supported:
- DeepSeek-V3.1 (reasoning, agentic planning, 128K context)
- Llama-3.2-Vision (11B/90B vision-language)
- Qwen2.5-VL (7B vision-language, GPU-optimized)
- Gemma-3 (multimodal, single-GPU)
- Mistral-Large-2 (reasoning, multilingual, tool calling)
- Phi-4-mini (3.8B-14B, fast routing, edge)
- Qwen2.5 (0.5B-72B, instruct + VL)
- Llama-3.2 (1B/3B, edge text models)
- Whisper-large-v3 (ASR, multilingual)
- GPT-OSS-20B (legacy/fallback)
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
ROUTER_REQUESTS = Counter(
    "router_requests_total",
    "Total routing requests",
    ["task_type", "modality", "selected_model"]
)

ROUTER_LATENCY = Histogram(
    "router_latency_seconds",
    "Routing decision latency",
    ["task_type"]
)

MODEL_HEALTH = Gauge(
    "model_health_status",
    "Model health (1=healthy, 0=unhealthy)",
    ["model_name", "backend"]
)

MODEL_TOKENS_PER_SEC = Gauge(
    "model_tokens_per_second",
    "Throughput (tokens/sec)",
    ["model_name"]
)


class Modality(str, Enum):
    """Input modality types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"


class TaskType(str, Enum):
    """Task categories for routing."""
    REASONING = "reasoning"           # Multi-step planning, CoT
    VISION_QA = "vision_qa"           # Visual question answering
    VISION_ANALYSIS = "vision_analysis"  # Image/chart/screenshot analysis
    CODE_GEN = "code_generation"      # Code writing, refactoring
    FAST_CHAT = "fast_chat"           # Quick responses, edge
    LONG_CONTEXT = "long_context"     # >32K tokens
    TOOL_CALLING = "tool_calling"     # Function/API invocation
    ASR = "asr"                       # Speech-to-text
    SUMMARIZATION = "summarization"   # Doc/transcript summary
    EDGE = "edge"                     # Low-latency, resource-constrained


class Backend(str, Enum):
    """Model serving backends."""
    VLLM = "vllm"                     # Primary: OpenAI-compatible
    LLAMACPP = "llamacpp"             # GGUF, CPU/low-VRAM
    TENSORRT = "tensorrt"             # High-throughput GPU
    WHISPER = "whisper"               # Faster-Whisper server
    TRANSFORMERS = "transformers"     # PyTorch direct (VLM)


@dataclass
class ModelSpec:
    """Model specification and capabilities."""
    name: str
    display_name: str
    backend: Backend
    endpoint: str
    
    # Capabilities
    modalities: List[Modality]
    task_types: List[TaskType]
    
    # Performance characteristics
    context_window: int
    max_tokens_per_sec: float
    avg_latency_ms: float
    
    # Resource requirements
    min_vram_gb: float
    supports_tool_calling: bool
    supports_streaming: bool
    
    # Quantization/precision
    quantization: Optional[str] = None  # "GGUF-Q5_K_M", "FP16", "INT4", etc.
    
    # Metadata
    priority: int = 50  # Higher = prefer in ties (0-100)
    health_score: float = 1.0  # 0.0-1.0, updated by health checks
    enabled: bool = True
    
    # Cost tracking (for telemetry)
    estimated_cost_per_1k_tokens: float = 0.0  # Local models = 0.0


@dataclass
class RoutingRequest:
    """Request to router."""
    prompt: str
    system: str = ""
    modality: Modality = Modality.TEXT
    task_type: Optional[TaskType] = None
    
    # Optional inputs for multimodal
    image_data: Optional[Any] = None  # PIL.Image, path, base64
    audio_data: Optional[Any] = None  # Path, bytes
    
    # Constraints
    max_tokens: int = 512
    require_tool_calling: bool = False
    require_streaming: bool = False
    max_latency_ms: Optional[float] = None
    prefer_edge: bool = False  # Prefer small/fast models
    
    # Context
    context_length: int = 0  # Estimated tokens in prompt
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingResult:
    """Router decision output."""
    selected_model: ModelSpec
    fallback_models: List[ModelSpec]
    routing_reason: str
    decision_latency_ms: float
    estimated_inference_latency_ms: float


class ModelClient(Protocol):
    """Protocol for model inference clients."""
    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 512,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response. Returns dict with 'text' key."""
        ...


class ModelRouter:
    """
    Intelligent multi-model router for ASTRA.
    
    Usage:
        router = ModelRouter(config)
        await router.initialize()
        
        # Route text reasoning task
        req = RoutingRequest(
            prompt="Analyze this codebase...",
            task_type=TaskType.REASONING
        )
        result = await router.route(req)
        
        # Route vision task
        req = RoutingRequest(
            prompt="What's in this image?",
            modality=Modality.IMAGE,
            task_type=TaskType.VISION_QA,
            image_data=image
        )
        result = await router.route(req)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models: Dict[str, ModelSpec] = {}
        self.clients: Dict[str, ModelClient] = {}
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Load model registry and start health checks."""
        await self._load_models()
        await self._initialize_clients()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _load_models(self):
        """Load model specifications from config."""
        model_configs = self.config.get("models", {})
        
        # DeepSeek-V3.1 (Primary reasoning/agentic)
        if model_configs.get("deepseek_v3_1", {}).get("enabled", False):
            self.models["deepseek-v3.1"] = ModelSpec(
                name="deepseek-v3.1",
                display_name="DeepSeek-V3.1",
                backend=Backend.VLLM,
                endpoint=model_configs["deepseek_v3_1"]["endpoint"],
                modalities=[Modality.TEXT],
                task_types=[TaskType.REASONING, TaskType.TOOL_CALLING, TaskType.LONG_CONTEXT, TaskType.CODE_GEN],
                context_window=131072,  # 128K
                max_tokens_per_sec=50.0,
                avg_latency_ms=500.0,
                min_vram_gb=40.0,
                supports_tool_calling=True,
                supports_streaming=True,
                quantization="FP16",
                priority=95  # Highest for reasoning
            )
        
        # Llama-3.2-Vision-11B (Vision-language, balanced)
        if model_configs.get("llama_3_2_vision_11b", {}).get("enabled", False):
            self.models["llama-3.2-vision-11b"] = ModelSpec(
                name="llama-3.2-vision-11b",
                display_name="Llama-3.2-Vision-11B",
                backend=Backend.VLLM,
                endpoint=model_configs["llama_3_2_vision_11b"]["endpoint"],
                modalities=[Modality.IMAGE, Modality.TEXT, Modality.MULTIMODAL],
                task_types=[TaskType.VISION_QA, TaskType.VISION_ANALYSIS],
                context_window=8192,
                max_tokens_per_sec=30.0,
                avg_latency_ms=800.0,
                min_vram_gb=24.0,
                supports_tool_calling=False,
                supports_streaming=True,
                quantization="FP16",
                priority=90
            )
        
        # Qwen2.5-VL-7B (Vision-language, GPU-optimized)
        if model_configs.get("qwen_2_5_vl_7b", {}).get("enabled", False):
            self.models["qwen-2.5-vl-7b"] = ModelSpec(
                name="qwen-2.5-vl-7b",
                display_name="Qwen2.5-VL-7B",
                backend=Backend.VLLM,
                endpoint=model_configs["qwen_2_5_vl_7b"]["endpoint"],
                modalities=[Modality.IMAGE, Modality.TEXT, Modality.MULTIMODAL],
                task_types=[TaskType.VISION_QA, TaskType.VISION_ANALYSIS],
                context_window=8192,
                max_tokens_per_sec=35.0,
                avg_latency_ms=700.0,
                min_vram_gb=16.0,
                supports_tool_calling=True,
                supports_streaming=True,
                quantization="FP16",
                priority=85
            )
        
        # Gemma-3 (Multimodal, single-GPU)
        if model_configs.get("gemma_3", {}).get("enabled", False):
            self.models["gemma-3"] = ModelSpec(
                name="gemma-3",
                display_name="Gemma-3",
                backend=Backend.VLLM,
                endpoint=model_configs["gemma_3"]["endpoint"],
                modalities=[Modality.IMAGE, Modality.TEXT, Modality.VIDEO, Modality.MULTIMODAL],
                task_types=[TaskType.VISION_QA, TaskType.VISION_ANALYSIS, TaskType.FAST_CHAT],
                context_window=8192,
                max_tokens_per_sec=40.0,
                avg_latency_ms=600.0,
                min_vram_gb=24.0,
                supports_tool_calling=False,
                supports_streaming=True,
                quantization="FP16",
                priority=80
            )
        
        # Mistral-Large-2 (Reasoning, multilingual, tool calling)
        if model_configs.get("mistral_large_2", {}).get("enabled", False):
            self.models["mistral-large-2"] = ModelSpec(
                name="mistral-large-2",
                display_name="Mistral-Large-2",
                backend=Backend.VLLM,
                endpoint=model_configs["mistral_large_2"]["endpoint"],
                modalities=[Modality.TEXT],
                task_types=[TaskType.REASONING, TaskType.TOOL_CALLING, TaskType.CODE_GEN, TaskType.LONG_CONTEXT],
                context_window=32768,
                max_tokens_per_sec=45.0,
                avg_latency_ms=450.0,
                min_vram_gb=32.0,
                supports_tool_calling=True,
                supports_streaming=True,
                quantization="FP16",
                priority=90
            )
        
        # Phi-4-mini (Fast, edge, routing)
        if model_configs.get("phi_4_mini", {}).get("enabled", False):
            self.models["phi-4-mini"] = ModelSpec(
                name="phi-4-mini",
                display_name="Phi-4-mini",
                backend=Backend.LLAMACPP,
                endpoint=model_configs["phi_4_mini"]["endpoint"],
                modalities=[Modality.TEXT],
                task_types=[TaskType.FAST_CHAT, TaskType.EDGE, TaskType.TOOL_CALLING],
                context_window=4096,
                max_tokens_per_sec=60.0,
                avg_latency_ms=200.0,
                min_vram_gb=4.0,
                supports_tool_calling=True,
                supports_streaming=True,
                quantization="GGUF-Q5_K_M",
                priority=70
            )
        
        # Qwen2.5-1.5B (Edge, fast)
        if model_configs.get("qwen_2_5_1_5b", {}).get("enabled", False):
            self.models["qwen-2.5-1.5b"] = ModelSpec(
                name="qwen-2.5-1.5b",
                display_name="Qwen2.5-1.5B",
                backend=Backend.LLAMACPP,
                endpoint=model_configs["qwen_2_5_1_5b"]["endpoint"],
                modalities=[Modality.TEXT],
                task_types=[TaskType.FAST_CHAT, TaskType.EDGE],
                context_window=32768,
                max_tokens_per_sec=80.0,
                avg_latency_ms=150.0,
                min_vram_gb=2.0,
                supports_tool_calling=False,
                supports_streaming=True,
                quantization="GGUF-Q4_K_M",
                priority=65
            )
        
        # Llama-3.2-3B (Edge text)
        if model_configs.get("llama_3_2_3b", {}).get("enabled", False):
            self.models["llama-3.2-3b"] = ModelSpec(
                name="llama-3.2-3b",
                display_name="Llama-3.2-3B",
                backend=Backend.LLAMACPP,
                endpoint=model_configs["llama_3_2_3b"]["endpoint"],
                modalities=[Modality.TEXT],
                task_types=[TaskType.FAST_CHAT, TaskType.EDGE],
                context_window=8192,
                max_tokens_per_sec=75.0,
                avg_latency_ms=180.0,
                min_vram_gb=3.0,
                supports_tool_calling=False,
                supports_streaming=True,
                quantization="GGUF-Q5_K_M",
                priority=68
            )
        
        # Whisper-large-v3 (ASR)
        if model_configs.get("whisper_large_v3", {}).get("enabled", False):
            self.models["whisper-large-v3"] = ModelSpec(
                name="whisper-large-v3",
                display_name="Whisper-Large-V3",
                backend=Backend.WHISPER,
                endpoint=model_configs["whisper_large_v3"]["endpoint"],
                modalities=[Modality.AUDIO],
                task_types=[TaskType.ASR],
                context_window=30,  # 30 seconds max
                max_tokens_per_sec=0.0,  # N/A for ASR
                avg_latency_ms=1000.0,
                min_vram_gb=8.0,
                supports_tool_calling=False,
                supports_streaming=False,
                quantization="INT8",
                priority=100  # Only choice for ASR
            )
        
        # GPT-OSS-20B (Legacy/fallback)
        if model_configs.get("gpt_oss_20b", {}).get("enabled", True):
            self.models["gpt-oss-20b"] = ModelSpec(
                name="gpt-oss-20b",
                display_name="GPT-OSS-20B",
                backend=Backend.LLAMACPP,
                endpoint=model_configs.get("gpt_oss_20b", {}).get("endpoint", "local"),
                modalities=[Modality.TEXT],
                task_types=[TaskType.REASONING, TaskType.FAST_CHAT, TaskType.CODE_GEN],
                context_window=8192,
                max_tokens_per_sec=12.0,
                avg_latency_ms=1500.0,
                min_vram_gb=0.0,  # CPU-only
                supports_tool_calling=True,  # Via adapters
                supports_streaming=False,
                quantization="GGUF-Q5_K_M",
                priority=50  # Fallback
            )
    
    async def _initialize_clients(self):
        """Initialize model clients for each backend."""
        # TODO: Implement actual clients
        # For now, placeholder
        for model_name in self.models:
            self.clients[model_name] = None  # type: ignore
    
    async def _health_check_loop(self):
        """Periodic health checks for all models."""
        while True:
            try:
                await asyncio.sleep(30.0)  # Check every 30s
                await self._run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health check error: {e}")
    
    async def _run_health_checks(self):
        """Check health of all enabled models."""
        for model_name, model_spec in self.models.items():
            if not model_spec.enabled:
                continue
            
            try:
                # TODO: Implement actual health check (ping endpoint)
                # For now, assume healthy
                model_spec.health_score = 1.0
                MODEL_HEALTH.labels(model_name, model_spec.backend.value).set(1)
            except Exception:
                model_spec.health_score = 0.0
                MODEL_HEALTH.labels(model_name, model_spec.backend.value).set(0)
    
    async def route(self, request: RoutingRequest) -> RoutingResult:
        """
        Route request to best model based on policy.
        
        Routing Policy:
        1. Filter by modality (image → vision models only)
        2. Filter by task type
        3. Apply constraints (tool calling, latency, edge)
        4. Rank by: health_score * priority * perf_score
        5. Select top + N fallbacks
        """
        start_time = time.time()
        
        # Step 1: Filter by modality
        candidates = [
            m for m in self.models.values()
            if m.enabled and request.modality in m.modalities
        ]
        
        if not candidates:
            raise RuntimeError(f"No models support modality: {request.modality}")
        
        # Step 2: Filter by task type (if specified)
        if request.task_type:
            candidates = [
                m for m in candidates
                if request.task_type in m.task_types
            ]
            
            if not candidates:
                # Fallback: allow any modality-compatible model
                candidates = [
                    m for m in self.models.values()
                    if m.enabled and request.modality in m.modalities
                ]
        
        # Step 3: Apply constraints
        if request.require_tool_calling:
            candidates = [m for m in candidates if m.supports_tool_calling]
        
        if request.require_streaming:
            candidates = [m for m in candidates if m.supports_streaming]
        
        if request.max_latency_ms:
            candidates = [m for m in candidates if m.avg_latency_ms <= request.max_latency_ms]
        
        if request.prefer_edge:
            # Prioritize small models
            candidates = [m for m in candidates if m.min_vram_gb <= 8.0]
        
        if request.context_length > 32768:
            # Long context
            candidates = [m for m in candidates if m.context_window >= 32768]
        
        if not candidates:
            raise RuntimeError("No models satisfy constraints")
        
        # Step 4: Rank candidates
        def score_model(model: ModelSpec) -> float:
            # Weighted score: health * priority * perf
            health_weight = model.health_score
            priority_weight = model.priority / 100.0
            
            # Perf: prefer faster models for fast_chat, slower OK for reasoning
            if request.task_type == TaskType.FAST_CHAT or request.prefer_edge:
                perf_weight = min(1.0, model.max_tokens_per_sec / 60.0)
            else:
                perf_weight = 0.8  # Neutral
            
            return health_weight * priority_weight * perf_weight
        
        candidates_scored = [(score_model(m), m) for m in candidates]
        candidates_scored.sort(key=lambda x: x[0], reverse=True)
        
        # Step 5: Select top + fallbacks
        selected = candidates_scored[0][1]
        fallbacks = [m for _, m in candidates_scored[1:4]]  # Top 3 fallbacks
        
        decision_latency_ms = (time.time() - start_time) * 1000.0
        
        # Build routing reason
        reason_parts = [
            f"modality={request.modality.value}",
            f"task={request.task_type.value if request.task_type else 'auto'}",
            f"candidates={len(candidates)}",
            f"selected={selected.name}",
        ]
        routing_reason = "; ".join(reason_parts)
        
        # Metrics
        ROUTER_REQUESTS.labels(
            request.task_type.value if request.task_type else "auto",
            request.modality.value,
            selected.name
        ).inc()
        
        ROUTER_LATENCY.labels(
            request.task_type.value if request.task_type else "auto"
        ).observe(decision_latency_ms / 1000.0)
        
        return RoutingResult(
            selected_model=selected,
            fallback_models=fallbacks,
            routing_reason=routing_reason,
            decision_latency_ms=decision_latency_ms,
            estimated_inference_latency_ms=selected.avg_latency_ms
        )
    
    async def generate(self, request: RoutingRequest) -> Dict[str, Any]:
        """
        Route + generate in one call.
        
        Returns:
            Dict with keys: text, model, backend, routing_info, latency_seconds
        """
        # Route
        routing = await self.route(request)
        
        # Generate
        client = self.clients.get(routing.selected_model.name)
        if not client:
            raise RuntimeError(f"No client for model: {routing.selected_model.name}")
        
        start_time = time.time()
        try:
            response = await client.generate(
                prompt=request.prompt,
                system=request.system,
                max_tokens=request.max_tokens
            )
            latency = time.time() - start_time
            
            # Enrich response with routing metadata
            response["model"] = routing.selected_model.name
            response["backend"] = routing.selected_model.backend.value
            response["routing_info"] = {
                "reason": routing.routing_reason,
                "decision_latency_ms": routing.decision_latency_ms,
                "fallbacks": [m.name for m in routing.fallback_models]
            }
            response["latency_seconds"] = latency
            
            return response
            
        except Exception as e:
            # TODO: Implement fallback logic
            raise RuntimeError(f"Generation failed: {e}") from e
    
    async def shutdown(self):
        """Clean shutdown."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass


def build_router_from_config(config: Dict[str, Any]) -> ModelRouter:
    """Factory: build router from config dict."""
    router_conf = config.get("model_router", {})
    return ModelRouter(router_conf)
