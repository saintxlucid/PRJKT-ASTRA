"""
Unified response templates and schemas for ASTRA API
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class Citation(BaseModel):
    """Source citation with relevant metadata"""
    text: str = Field(..., description="The cited text")
    source: str = Field(..., description="Source identifier")
    score: float = Field(default=1.0, description="Relevance score")
    
class ResponseMetadata(BaseModel):
    """Common response metadata"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str = Field(..., description="Model identifier")
    version: str = Field(..., description="API version")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    token_count: Optional[int] = Field(None, description="Total tokens used")
    
class StreamChunk(BaseModel):
    """Individual stream response chunk"""
    chunk: str = Field(..., description="Text chunk")
    chunk_id: int = Field(..., description="Sequence number")
    is_final: bool = Field(default=False, description="Final chunk flag")
    citations: List[Citation] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

class ApiResponse(BaseModel):
    """Base API response template"""
    answer: str = Field(..., description="Generated response")
    citations: List[Citation] = Field(default_factory=list)
    metadata: ResponseMetadata

def create_response(
    answer: str,
    model: str,
    version: str,
    citations: List[Dict[str, Any]] = None,
    processing_time: float = 0.0,
    token_count: Optional[int] = None
) -> Dict[str, Any]:
    """Create a unified API response"""
    return ApiResponse(
        answer=answer,
        citations=[Citation(**c) for c in (citations or [])],
        metadata=ResponseMetadata(
            model=model,
            version=version,
            processing_time=processing_time,
            token_count=token_count
        )
    ).dict()

def create_stream_chunk(
    chunk: str,
    chunk_id: int,
    is_final: bool = False,
    citations: List[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a stream chunk response"""
    return StreamChunk(
        chunk=chunk,
        chunk_id=chunk_id,
        is_final=is_final,
        citations=[Citation(**c) for c in (citations or [])],
        metadata=metadata
    ).dict()