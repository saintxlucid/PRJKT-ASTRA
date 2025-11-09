"""Schema definitions for memory validation.

Provides schemas for:
- Memory entries
- Citations
- Memory-aware plans
- Memory queries
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime

from ..core.schema import BaseSchema


class MemoryEntrySchema(BaseModel):
    """Schema for memory entries."""
    content: str = Field(
        ...,
        description="Memory content",
        min_length=1,
        max_length=10000
    )
    source: str = Field(
        ...,
        description="Memory source type",
        regex="^(conversation|tool_use|document|code|plan)$"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    
    @validator("content")
    def validate_content(cls, v):
        """Validate memory content."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class CitationSchema(BaseModel):
    """Schema for memory citations."""
    key: str = Field(
        ...,
        description="Citation key",
        regex="^[a-f0-9]{16}$"  # 16-char hex
    )
    context: str = Field(
        ...,
        description="Citation context",
        min_length=1,
        max_length=1000
    )
    confidence: float = Field(
        ...,
        description="Match confidence",
        ge=0.0,
        le=1.0
    )
    verified: bool = Field(
        False,
        description="Verification status"
    )


class PlanStepSchema(BaseModel):
    """Schema for plan steps."""
    description: str = Field(
        ...,
        description="Step description",
        min_length=1,
        max_length=1000
    )
    citations: List[CitationSchema] = Field(
        ...,
        description="Supporting citations",
        min_items=1
    )
    estimated_confidence: float = Field(
        ...,
        description="Estimated confidence",
        ge=0.0,
        le=1.0
    )
    requires_verification: bool = Field(
        True,
        description="Whether step needs verification"
    )


class PlanSchema(BaseModel):
    """Schema for memory-aware plans."""
    steps: List[PlanStepSchema] = Field(
        ...,
        description="Plan steps",
        min_items=1
    )
    context: Dict[str, str] = Field(
        ...,
        description="Planning context"
    )
    metadata: Dict[str, Union[List[str], float, Dict[str, bool]]] = Field(
        ...,
        description="Plan metadata"
    )
    creation_time: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    validation_status: Dict[str, bool] = Field(
        default_factory=dict,
        description="Citation validation status"
    )


class MemoryQuerySchema(BaseModel):
    """Schema for memory queries."""
    query: str = Field(
        ...,
        description="Search query",
        min_length=1,
        max_length=1000
    )
    k: int = Field(
        5,
        description="Number of results",
        ge=1,
        le=100
    )
    min_confidence: float = Field(
        0.7,
        description="Minimum confidence",
        ge=0.0,
        le=1.0
    )
    source_filter: Optional[List[str]] = Field(
        None,
        description="Optional source filter"
    )
    
    @validator("source_filter")
    def validate_sources(cls, v):
        """Validate memory source types."""
        if v is not None:
            valid_sources = {
                "conversation",
                "tool_use",
                "document",
                "code",
                "plan"
            }
            for source in v:
                if source not in valid_sources:
                    raise ValueError(f"Invalid source type: {source}")
        return v