"""
Answer endpoints for non-streaming responses.

Provides endpoints for generating complete answers with citations
and token management.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from starlette.exceptions import HTTPException as StarletteHTTPException  # Both FastAPI and Starlette HTTP exceptions

from astra.core.response_template import ResponseTemplate
from astra.core.backpressure import Backpressure
from astra.core.circuit_breakers import CircuitBreaker, CircuitBreakerError
from astra.services.chat_service import ChatService
from astra.services.memory_service import MemoryService
from astra.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/answer", tags=["answer"])

# Dependencies
response_template = ResponseTemplate()
backpressure = Backpressure(tokens=100)  # Configure token limit
circuit_breaker = CircuitBreaker(
    name="answer_endpoint",
    failure_threshold=5,
    reset_timeout=60.0
)

# Services
chat_service: Optional[ChatService] = None
memory_service: Optional[MemoryService] = None

class AnswerRequest(BaseModel):
    """Request model for /answer endpoint"""
    query: str
    conversation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AnswerResponse(BaseModel):
    """Response model for /answer endpoint"""
    answer: str
    citations: list[Dict[str, Any]]
    metadata: Dict[str, Any]

def set_answer_services(
    chat_svc: ChatService,
    memory_svc: MemoryService
) -> None:
    """Set service dependencies"""
    global chat_service, memory_service
    chat_service = chat_svc
    memory_service = memory_svc

@router.post("/", response_model=AnswerResponse)
async def generate_answer(
    request: AnswerRequest
) -> Dict[str, Any]:
    """Generate a complete answer with citations"""
    
    # Validate services are configured
    if not chat_service or not memory_service:
        raise RuntimeError("Services not configured")
        
    try:
        # Check circuit breaker
        if circuit_breaker.open:
            raise CircuitBreakerError("Service is in circuit breaker state")
            
        # Apply backpressure
        await backpressure.acquire()
        try:
            # Generate answer
            answer = await chat_service.generate_response(
                query=request.query,
                conversation_id=request.conversation_id
            )

            # Retrieve citations
            citations = await memory_service.get_citations(
                query=request.query,
                content=answer
            )

            # Format response
            response = response_template.format_answer(
                response=answer,
                citations=citations,
                conversation_id=request.conversation_id,
                metadata=request.metadata
            )

            # Record success
            circuit_breaker.check_reset()
            return response

        finally:
            await backpressure.release()

    except CircuitBreakerError:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    except (HTTPException, StarletteHTTPException) as e:
        logger.error(
            "answer_generation_error",
            error=f"{e.status_code}: {e.detail}",
            query=request.query
        )
        raise  # Re-raise HTTPException unchanged
    except Exception as e:
        logger.error(
            "answer_generation_error",
            error=str(e),
            query=request.query
        )
        raise HTTPException(
            status_code=500,
            detail="Error generating answer"
        ) from e