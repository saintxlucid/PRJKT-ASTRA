"""
ASTRA LLM Metadata Schema and Handler
Manages GGUF metadata parsing and validation.
Created: October 16, 2025
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field
from enum import Enum

class AstraPersona(str, Enum):
    """ASTRA personality profiles"""
    GUARDIAN_ENGINEER = "GuardianEngineer"
    RESEARCHER = "Researcher"
    BUILDER = "Builder"
    OPERATOR = "Operator"

class PersonalityTraits(BaseModel):
    """Core personality trait weights"""
    warmth: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    candor: float = Field(ge=0.0, le=1.0)
    prudence: float = Field(ge=0.0, le=1.0)

class SamplingParams(BaseModel):
    """LLM sampling parameters"""
    temperature: float = Field(ge=0.0, le=2.0)
    top_p: float = Field(ge=0.0, le=1.0)
    repeat_penalty: float = Field(ge=1.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=0)
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None

class RoPEParams(BaseModel):
    """RoPE (Rotary Position Embedding) parameters"""
    scaling: Optional[str] = Field(None, pattern="^(yarn|ntk-linear|none)$")
    freq_base: Optional[int] = Field(None, ge=1)
    freq_scale: Optional[float] = None
    alpha_value: Optional[float] = None

class AstraMetadata(BaseModel):
    """Complete ASTRA metadata schema"""
    identity_version: str
    persona: AstraPersona
    traits: PersonalityTraits
    consent_rules: Dict[str, str]
    sampling: SamplingParams
    rope: Optional[RoPEParams] = None

class MetadataHandler:
    """Handles GGUF metadata parsing and validation"""
    
    def __init__(self, model_path: Path):
        """Initialize with path to GGUF model"""
        self.model_path = model_path
        self._metadata: Optional[AstraMetadata] = None
    
    def load_metadata(self) -> AstraMetadata:
        """
        Load and validate ASTRA metadata from GGUF.
        For now, simulates metadata until we implement GGUF reading.
        """
        # TODO: Implement actual GGUF metadata reading
        # For now return default/test metadata
        return AstraMetadata(
            identity_version="2.5",
            persona=AstraPersona.GUARDIAN_ENGINEER,
            traits=PersonalityTraits(
                warmth=0.85,
                precision=0.90,
                candor=0.95,
                prudence=0.70
            ),
            consent_rules={
                "network_write": "explicit",
                "destructive": "explicit_with_backup"
            },
            sampling=SamplingParams(
                temperature=0.7,
                top_p=0.95,
                repeat_penalty=1.15
            )
        )
    
    @property
    def metadata(self) -> AstraMetadata:
        """Get cached metadata, loading if needed"""
        if self._metadata is None:
            self._metadata = self.load_metadata()
        return self._metadata
    
    def get_sampling_args(self) -> Dict[str, Any]:
        """Get sampling parameters as kwargs dict"""
        return self.metadata.sampling.dict(
            exclude_none=True,
            exclude_unset=True
        )
    
    def get_rope_args(self) -> Dict[str, Any]:
        """Get RoPE parameters as kwargs dict"""
        if not self.metadata.rope:
            return {}
        return self.metadata.rope.dict(
            exclude_none=True,
            exclude_unset=True
        )

    def to_json(self) -> str:
        """Export metadata as JSON string"""
        return self.metadata.json(indent=2)

    def get_consent_level(self, operation: str) -> str:
        """Get required consent level for operation"""
        return self.metadata.consent_rules.get(
            operation, "implicit"
        )