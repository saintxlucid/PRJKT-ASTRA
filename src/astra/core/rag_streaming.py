"""
ASTRA RAG Streaming Support
Created: October 25, 2025

Implements streaming response generation for ASTRA's RAG system
using Server-Sent Events (SSE).
"""
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
import structlog
from uuid import uuid4

from astra.core.rag_fusion import RAGFusionEngine

logger = structlog.get_logger()

class StreamingRAG:
    """Streaming RAG response generator"""
    
    def __init__(self, rag_engine: RAGFusionEngine):
        self.rag_engine = rag_engine
        
    async def stream_answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        k: Optional[int] = None,
        context_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response
        
        Yields:
            SSE formatted events containing:
            - start: Initial context and metadata
            - token: Individual response tokens
            - citations: Source citations
            - end: Final metrics
        """
        trace_id = str(uuid4())
        try:
            # 1. Start event with trace ID
            trace_id = str(uuid4())
            yield self._format_sse(
                "start",
                {
                    "trace_id": trace_id,
                    "query": query
                }
            )
            
            # 2. Retrieve and process memories
            memories = await self.rag_engine._retrieve_memories(
                query, k or self.rag_engine.default_k, trace_id
            )
            
            yield self._format_sse(
                "progress",
                {
                    "stage": "retrieval",
                    "memory_count": len(memories)
                }
            )
            
            # 3. Plan context
            context, citations = self.rag_engine._plan_context(
                memories,
                context_tokens or self.rag_engine.max_context_tokens
            )
            
            yield self._format_sse(
                "progress", 
                {
                    "stage": "planning",
                    "context_tokens": len(context.split())
                }
            )
            
            # 4. Get persona and compose prompt
            persona = await self.rag_engine.persona_manager.get_persona(persona_id)
            system_prompt = self.rag_engine._compose_system_prompt(
                persona, context
            )
            
            # 5. Stream generation
            async for chunk in self.rag_engine.inference_queue.stream(
                system_prompt=system_prompt,
                user_prompt=query,
                trace_id=trace_id,
                session_id=session_id
            ):
                yield self._format_sse("token", {"text": chunk})
                
            # 6. Send citations
            yield self._format_sse("citations", citations)
            
            # 7. End with metrics
            yield self._format_sse(
                "end",
                {
                    "memory_ids": [m.id for m in memories],
                    "trace_id": trace_id
                }
            )
            
        except Exception as e:
            logger.exception(
                "streaming_error",
                trace_id=trace_id,
                error=str(e)
            )
            yield self._format_sse(
                "error",
                {
                    "message": str(e),
                    "trace_id": trace_id
                }
            )
            
    def _format_sse(self, event: str, data: Dict[str, Any]) -> str:
        """Format Server-Sent Event message"""
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"