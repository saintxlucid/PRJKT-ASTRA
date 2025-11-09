"""
ASTRA Answer API
Created: October 31, 2025

Non-streaming answer endpoint with metrics, backpressure, and circuit breakers.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from prometheus_client import Counter, Histogram

from .backpressure import QueueDepthGuard, LatencyTracker
from .circuit_breakers import CircuitBreaker
from ..rag.rag_fusion import RAGFusionEngine
from ..core.response_template import ResponseTemplate

# Metrics
ANSWER_REQUESTS = Counter(
    "astra_answer_requests_total",
    "Total number of /answer requests",
    ["status"]
)
ANSWER_LATENCY = Histogram(
    "astra_answer_latency_seconds",
    "Latency of /answer endpoint",
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0]
)

class AnswerRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    max_tokens: Optional[int] = None

class AnswerResponse(BaseModel):
    answer: str
    citations: list[Dict[str, Any]]
    metadata: Dict[str, Any]

class AnswerAPI:
    """API component for answer endpoints"""
    
    def __init__(self, rag_engine: RAGFusionEngine):
        """Initialize API with dependencies"""
        self.router = APIRouter()
        self.template = ResponseTemplate()
        self.rag_engine = rag_engine
        self.model_id = "mock-model-v1" # For testing
        
        # Initialize circuit breakers
        self.memory_breaker = CircuitBreaker(
            name="memory",
            failure_threshold=5,
            reset_timeout=30
        )
        self.inference_breaker = CircuitBreaker(
            name="inference", 
            failure_threshold=3,
            reset_timeout=60
        )

        # Initialize backpressure guards
        self.queue_guard = QueueDepthGuard(max_depth=100)
        self.latency_tracker = LatencyTracker(slo_threshold=2.5)
        
        # Register routes
        self.router.add_api_route(
            "/answer", 
            self.get_answer,
            methods=["POST"],
            response_model=AnswerResponse
        )
        
    async def shutdown(self):
        """Clean up resources"""
        # Currently nothing to clean up
        pass

    async def get_answer(
        self,
        request: Request,
        query: AnswerRequest,
        background_tasks: BackgroundTasks
    ):
        """Non-streaming answer endpoint with full RAG context"""
        
        # Check backpressure before processing
        if not self.queue_guard.can_accept():
            ANSWER_REQUESTS.labels(status="rejected").inc()
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Service currently at capacity",
                    "retry_after": 5
                }
            )

        # Track request for latency monitoring
        request_tracker = self.latency_tracker.start_request()
        
        try:
            # Get RAG context with circuit breaker protection
            with self.memory_breaker():
                rag_result = await self.rag_engine.fuse(
                    query=query.query
                )
            
            # Generate answer with inference breaker
            with self.inference_breaker():
                response = await request.app.state.inference.complete(
                    context=rag_result["context"],
                    query=query.query,
                    max_tokens=query.max_tokens or 512
                )
            
            # Format response using template
            answer = self.template.format_answer(
                response=response,
                citations=rag_result["citations"],
                conversation_id=query.conversation_id
            )
            
            # Record success metrics
            ANSWER_REQUESTS.labels(status="success").inc()
            ANSWER_LATENCY.observe(request_tracker.elapsed())
            
            # Update latency tracker in background
            background_tasks.add_task(
                self.latency_tracker.record_latency,
                request_tracker.elapsed()
            )
            
            return answer
            
        except Exception as e:
            ANSWER_REQUESTS.labels(status="error").inc()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(e),
                    "error_id": str(id(e)),
                    "request_id": str(request.state.request_id)
                }
            )