from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

from astra.core.rag_streaming import StreamingRAG
from astra.core.rag_fusion import RAGFusionEngine
from astra.dependencies import get_rag_engine

router = APIRouter()

@router.get("/stream")
async def stream_answer(
    query: str,
    session_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    k: Optional[int] = None,
    context_tokens: Optional[int] = None,
    rag_engine: RAGFusionEngine = Depends(get_rag_engine)
):
    """Stream a RAG-enhanced answer
    
    Args:
        query: The user's question
        session_id: Optional session identifier for context
        persona_id: Optional persona to use for response
        k: Number of memories to retrieve
        context_tokens: Max context tokens to use
        rag_engine: RAG engine dependency
        
    Returns:
        Streaming response with SSE events
    """
    try:
        streamer = StreamingRAG(rag_engine)
        return StreamingResponse(
            streamer.stream_answer(
                query=query,
                session_id=session_id,
                persona_id=persona_id,
                k=k,
                context_tokens=context_tokens
            ),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))