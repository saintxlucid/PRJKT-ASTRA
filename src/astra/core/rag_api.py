"""
ASTRA RAG API Router
Created: October 25, 2025

Provides endpoints for RAG-based question answering and
memory interaction in the ASTRA system.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from astra.core.rag_fusion import RAGFusionEngine

# Initialize router
router = APIRouter(prefix="/astra/rag", tags=["rag"])

# Request/response models
class AnswerRequest(BaseModel):
    """Request model for RAG-based answers"""
    query: str = Field(..., description="User question or prompt")
    session_id: Optional[str] = Field(None, description="Session ID for context continuity")
    persona_id: Optional[str] = Field(None, description="Specific persona to use")
    k: Optional[int] = Field(None, description="Number of memories to retrieve")
    context_tokens: Optional[int] = Field(None, description="Max tokens for context")

class AnswerResponse(BaseModel):
    """Response model for RAG answers"""
    text: str = Field(..., description="Generated response text")
    memory_ids: list[str] = Field(..., description="Memory IDs used in response")
    adapter_ids: list[str] = Field(..., description="Adapter IDs applied")
    citations: Dict[str, Any] = Field(..., description="Source citations")
    metrics: Dict[str, Any] = Field(..., description="Performance metrics")
    trace_id: str = Field(..., description="Trace ID for request correlation")

# Global RAG engine instance
_rag_engine: Optional[RAGFusionEngine] = None

def init_rag_router(rag_engine: RAGFusionEngine) -> None:
    """Initialize router with RAG engine instance"""
    global _rag_engine
    _rag_engine = rag_engine

@router.post("/answer", response_model=AnswerResponse)
async def generate_answer(request: AnswerRequest) -> Dict[str, Any]:
    """Generate an answer using RAG fusion
    
    Args:
        request: Answer request parameters
        
    Returns:
        Response containing answer text and metadata
        
    Raises:
        HTTPException: If RAG engine not initialized or processing fails
    """
    if not _rag_engine:
        raise HTTPException(
            status_code=503,
            detail="RAG engine not initialized"
        )
        
    try:
        response = await _rag_engine.answer(
            query=request.query,
            session_id=request.session_id,
            persona_id=request.persona_id,
            k=request.k,
            context_tokens=request.context_tokens
        )
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating answer: {str(e)}"
        )