"""
ASTRA LLM Core Types - Neutral Type Definitions
================================================

Central location for shared types to eliminate circular dependencies.
All request/response models, configs, and interfaces live here.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


# ============================================================================
# ENUMS
# ============================================================================

class Modality(str, Enum):
    """Input modality type."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"


class TaskType(str, Enum):
    """Task classification for routing."""
    REASONING = "reasoning"
    CODE = "code"
    CREATIVE = "creative"
    FAST_CHAT = "fast_chat"
    VISION = "vision"
    AUDIO = "audio"
    PLANNING = "planning"
    ANALYSIS = "analysis"


class SafetyTier(str, Enum):
    """Tool safety classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProviderType(str, Enum):
    """LLM provider backend type."""
    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    TRANSFORMERS = "transformers"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# ============================================================================
# REQUEST MODELS (Pydantic Validated)
# ============================================================================

class GenerateRequest(BaseModel):
    """Unified LLM generation request with validation."""
    
    prompt: str = Field(..., min_length=1, max_length=100000)
    model: str | None = Field(None, description="Specific model override")
    
    # Generation parameters
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1, le=131072)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    top_k: int = Field(50, ge=0, le=100)
    
    # Multimodal inputs
    images: list[str] = Field(default_factory=list, description="Base64 encoded images")
    audio: str | None = Field(None, description="Base64 encoded audio")
    
    # Routing hints
    task_type: TaskType | None = None
    modality: Modality = Modality.TEXT
    latency_budget_ms: int | None = Field(None, ge=100, le=60000)
    
    # Context
    conversation_id: str | None = None
    user_id: str | None = None
    mode: str | None = Field(None, description="MUSIC|FILM|CODE|LEARNING")
    
    # Tool calling
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | None = None
    
    # Advanced
    stream: bool = False
    stop: list[str] = Field(default_factory=list)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    
    @validator("images")
    def validate_images(cls, v):
        """Validate base64 image format."""
        if len(v) > 10:
            raise ValueError("Maximum 10 images per request")
        return v
    
    @validator("prompt")
    def sanitize_prompt(cls, v):
        """Basic prompt sanitization."""
        forbidden = [
            "ignore previous instructions",
            "disregard all above",
            "system override",
            "developer mode",
            "jailbreak"
        ]
        v_lower = v.lower()
        for phrase in forbidden:
            if phrase in v_lower:
                # Replace with redaction marker
                v = v.replace(phrase, "[REDACTED]")
        return v
    
    class Config:
        use_enum_values = True


class RoutingRequest(BaseModel):
    """Request for model routing decision."""
    
    text: str
    has_image: bool = False
    has_audio: bool = False
    tools: list[str] = Field(default_factory=list)
    complexity: float = Field(0.5, ge=0.0, le=1.0)
    risk: SafetyTier = SafetyTier.LOW
    latency_budget_ms: int = Field(3000, ge=100)
    mode: str | None = None
    
    class Config:
        use_enum_values = True


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class TokenUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GenerateResponse(BaseModel):
    """Unified LLM generation response."""
    
    content: str
    model: str
    provider: str
    
    # Metadata
    usage: TokenUsage
    latency_ms: float
    cost_usd: float = 0.0
    
    # Routing info
    route_decision: dict[str, Any] | None = None
    soul_alignment: dict[str, Any] | None = None
    
    # Tool results
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    
    # Context
    conversation_id: str | None = None
    event_id: str | None = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RouteDecision(BaseModel):
    """Model routing decision."""
    
    model: str
    provider: str
    profile: str  # reasoning/speed/vision/audio
    rules_matched: list[str]
    complexity_score: float
    risk_level: str
    soul_alignment: str | None = None
    fallback_available: bool = True
    
    # Metrics for observability
    decision_latency_ms: float = 0.0


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

@dataclass
class ModelCapabilities:
    """Model capability scores (0.0-1.0)."""
    reasoning: float = 0.5
    code: float = 0.5
    creative: float = 0.5
    vision: float = 0.0
    audio: float = 0.0
    planning: float = 0.5
    analysis: float = 0.5


@dataclass
class ModelConfig:
    """Complete model configuration from registry."""
    
    name: str
    provider: ProviderType
    path: str
    
    capabilities: ModelCapabilities
    
    context_window: int
    vram_gb: float
    cost_per_1k_tokens: float
    latency_p95_ms: float
    
    modalities: list[Modality]
    safety_tier: SafetyTier
    features: list[str]
    
    # Optional
    endpoint: str | None = None
    notes: str | None = None
    
    def supports_modality(self, modality: Modality) -> bool:
        """Check if model supports given modality."""
        return modality in self.modalities or Modality.MULTIMODAL in self.modalities
    
    def get_capability_score(self, task: TaskType) -> float:
        """Get capability score for specific task type."""
        mapping = {
            TaskType.REASONING: self.capabilities.reasoning,
            TaskType.CODE: self.capabilities.code,
            TaskType.CREATIVE: self.capabilities.creative,
            TaskType.VISION: self.capabilities.vision,
            TaskType.AUDIO: self.capabilities.audio,
            TaskType.PLANNING: self.capabilities.planning,
            TaskType.ANALYSIS: self.capabilities.analysis,
        }
        return mapping.get(task, 0.5)


@dataclass
class RoutingProfile:
    """Routing profile configuration."""
    
    name: str
    primary_model: str
    fallback_model: str | None
    
    min_complexity: float = 0.0
    max_latency_ms: int = 3000
    max_risk: SafetyTier = SafetyTier.HIGH


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@dataclass
class ToolDefinition:
    """Tool definition with HTP v1 extensions."""
    
    name: str
    description: str
    parameters: dict[str, Any]
    
    # HTP extensions
    safety_tier: SafetyTier = SafetyTier.MEDIUM
    permissions: list[str] = field(default_factory=list)
    sandbox: bool = True
    
    cost_estimate: dict[str, int] | None = None
    evidence_capture: bool = False
    require_confirmation: bool = False


# ============================================================================
# METRICS & OBSERVABILITY
# ============================================================================

@dataclass
class RouteMetrics:
    """Metrics for a routing decision."""
    
    timestamp: datetime
    model: str
    latency_ms: float
    tokens: int
    cost_usd: float
    
    complexity_score: float
    risk_level: str
    soul_aligned: bool
    
    fallback_used: bool = False
    cache_hit: bool = False


@dataclass
class ModelMetrics:
    """Real-time model performance metrics."""
    
    model: str
    
    # Performance
    requests_total: int = 0
    requests_failed: int = 0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    
    # Resources
    vram_used_gb: float = 0.0
    vram_total_gb: float = 0.0
    queue_depth: int = 0
    
    # Tokens
    tokens_input: int = 0
    tokens_output: int = 0
    token_efficiency: float = 0.0  # output/input ratio
    
    # Cache
    kv_cache_hit_ratio: float = 0.0
    prefix_cache_hits: int = 0


# ============================================================================
# PROVIDER INTERFACE
# ============================================================================

class LLMProvider:
    """Abstract base class for LLM providers."""
    
    provider_type: ProviderType
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate completion from LLM."""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """Check provider health."""
        raise NotImplementedError
    
    def get_metrics(self) -> ModelMetrics:
        """Get current provider metrics."""
        raise NotImplementedError


# ============================================================================
# SOUL LAYER
# ============================================================================

@dataclass
class AlignmentResult:
    """Soul layer alignment evaluation result."""
    
    status: str  # aligned/grey/misaligned
    score: float  # 0.0-1.0
    reason: str
    alternative: str | None = None
    celebration: str | None = None
    anti_pattern_detected: str | None = None


# ============================================================================
# AUDIT LOG
# ============================================================================

@dataclass
class AuditLogEntry:
    """Governance audit log entry."""
    
    timestamp: datetime
    request_id: str
    user_id: str | None
    
    model_selected: str
    policy_rules_triggered: list[str]
    soul_alignment: str
    
    result: str  # success/blocked/grey
    reason: str | None = None
    
    # Metrics
    latency_ms: float = 0.0
    tokens: int = 0
    cost_usd: float = 0.0
