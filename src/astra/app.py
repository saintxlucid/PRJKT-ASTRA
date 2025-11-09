"""
ASTRA FastAPI Application
Created: October 31, 2025

Main FastAPI application with endpoint routing and dependency management.
"""
from typing import Annotated, Optional, Dict, Any, AsyncIterator
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import structlog
import json
from datetime import datetime, UTC
import asyncio
from contextlib import asynccontextmanager

from astra.core.response_template import ResponseTemplate
from astra.core.circuit_breakers import CircuitBreaker, CircuitBreakerError
from astra.core.backpressure import Backpressure
from astra.core.answer_api import AnswerAPI

logger = structlog.get_logger(__name__)

# Initialize components
response_template = ResponseTemplate()
circuit_breaker = CircuitBreaker("answer_service")
backpressure = Backpressure()

# Create mock components for testing
from .test_utils import MockRAGFusionEngine, MockInference
rag_engine = MockRAGFusionEngine()
inference = MockInference()

# Initialize API
answer_api = AnswerAPI(rag_engine=rag_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup/shutdown"""
    # Startup
    logger.info("astra_starting")
    yield
    # Shutdown
    logger.info("astra_shutting_down")
    await asyncio.gather(
        circuit_breaker.shutdown(),
        backpressure.shutdown(),
        answer_api.shutdown()
    )

app = FastAPI(
    title="ASTRA API",
    description="ASTRA intelligent agent API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Add dependencies and routes
app.state.inference = inference
app.state.rag_engine = rag_engine
app.include_router(answer_api.router)

async def get_answer_api() -> AnswerAPI:
    """Dependency for answer API access"""
    try:
        with circuit_breaker():
            pass
    except CircuitBreakerError:
        raise HTTPException(503, "Service temporarily unavailable")
    try:
        await backpressure.acquire()
    except HTTPException as e:
        if e.status_code == 503:
            raise HTTPException(429, "Server is at capacity")
        raise
    return answer_api

# Endpoint dependencies
@app.post("/answer")
async def get_answer(
    query: str,
    conversation_id: Optional[str] = None,
    service: AnswerAPI = Depends(get_answer_api)
) -> Dict[str, Any]:
    """Get an answer to a query
    
    Args:
        query: The user's question
        conversation_id: Optional conversation context
        service: Answer service dependency
        
    Returns:
        Formatted answer response
    """
    try:
        # Get answer with citations
        answer, citations, metadata = await service.get_answer(
            query,
            conversation_id=conversation_id
        )
        
        # Format response
        response = response_template.format_answer(
            response=answer,
            citations=citations,
            conversation_id=conversation_id,
            metadata=metadata,
            model_id=service.model_id
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "answer_error",
            error=str(e),
            query=query,
            conversation_id=conversation_id
        )
        error_response = response_template.format_error(
            status_code=500,
            message="Error generating answer",
            error_type="generation_error",
            metadata={
                "query": query,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail=error_response["error"]
        )

@app.post("/answer/stream")
async def stream_answer(
    query: str,
    conversation_id: Optional[str] = None,
    service: AnswerAPI = Depends(get_answer_api)
) -> EventSourceResponse:
    """Stream an answer to a query
    
    Args:
        query: The user's question 
        conversation_id: Optional conversation context
        service: Answer service dependency
        
    Returns:
        SSE stream of answer chunks
    """
    async def event_generator() -> AsyncIterator[Dict[str, Any]]:
        try:
            chunk_id = 0
            async for chunk, is_final, citations, metadata in service.stream_answer(
                query,
                conversation_id=conversation_id
            ):
                # Format chunk
                response = response_template.format_stream_chunk(
                    chunk=chunk,
                    chunk_id=chunk_id,
                    is_final=is_final,
                    citations=citations,
                    metadata=metadata
                )
                
                yield {
                    "event": "message",
                    "data": json.dumps(response)
                }
                
                chunk_id += 1
                
        except Exception as e:
            logger.error(
                "stream_error",
                error=str(e),
                query=query,
                conversation_id=conversation_id
            )
            error_response = response_template.format_error(
                status_code=500,
                message="Error streaming answer",
                error_type="stream_error",
                metadata={
                    "query": query,
                    "error": str(e)
                }
            )
            yield {
                "event": "error",
                "data": json.dumps(error_response)
            }
            
    return EventSourceResponse(event_generator())

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    circuit_breaker_status = {
        "state": "closed" if not circuit_breaker.open else "open",
        "failures": circuit_breaker.failures,
        "threshold": circuit_breaker.failure_threshold,
        "reset_timeout": circuit_breaker.reset_timeout
    }
    
    backpressure_status = {
        "available_tokens": backpressure.available_tokens,
        "max_tokens": backpressure.max_tokens,
        "queue_size": await backpressure.queue_size()
    }
    
    try:
        return response_template.format_health_check(
            circuit_breaker_status=circuit_breaker_status,
            backpressure_status=backpressure_status
        )
    except Exception as e:
        logger.error("health_check_error", error=str(e))
        error_response = response_template.format_error(
            status_code=500,
            message="Error checking service health",
            error_type="health_check_error"
        )
        raise HTTPException(
            status_code=500,
            detail=error_response["error"]
        )