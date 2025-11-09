#!/usr/bin/env python3
"""
ASTRA Test Server - Core API Spine

Handles:
- Request lifecycle management
- Health and readiness probes
- Graceful shutdown
- Backpressure monitoring
- Circuit breakers
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import uvicorn
import httpx
import asyncio
import time
import structlog
from typing import Dict, Any, List, AsyncIterator, Optional
from datetime import datetime
import json
import signal
from collections import defaultdict
from threading import Lock

# Configure structured logging
logger = structlog.get_logger()

# Rate limiter using token bucket algorithm
class RateLimiter:
    """Token bucket rate limiter per endpoint"""
    def __init__(self, default_rps: int = 100):
        self.default_rps = default_rps
        self.endpoint_limits = {
            "/answer": 50,           # Lower limit for expensive operations
            "/answer/stream": 30,    # Even lower for streaming
            "/health": 1000,         # High limit for health checks
            "/live": 1000,
            "/ready": 1000,
            "/metrics": 100,
        }
        self.buckets = defaultdict(lambda: {"tokens": 0.0, "last_refill": time.time()})
        self.lock = Lock()
    
    def get_limit(self, endpoint: str) -> int:
        """Get rate limit for endpoint in requests per second"""
        return self.endpoint_limits.get(endpoint, self.default_rps)
    
    def allow_request(self, endpoint: str) -> bool:
        """Check if request is allowed (token bucket algorithm)"""
        with self.lock:
            limit = self.get_limit(endpoint)
            bucket = self.buckets[endpoint]
            
            # Refill bucket based on time passed
            now = time.time()
            time_passed = now - bucket["last_refill"]
            tokens_to_add = time_passed * limit
            
            bucket["tokens"] = min(limit, bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = now
            
            # Check if we have tokens
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            return False

rate_limiter = RateLimiter()

# Prometheus-style metrics collector
class MetricsCollector:
    def __init__(self):
        self.request_count = defaultdict(int)  # by endpoint
        self.request_duration = defaultdict(list)  # by endpoint
        self.request_in_progress = defaultdict(int)  # by endpoint
        self.error_count = defaultdict(int)  # by endpoint and status
        self.circuit_breaker_trips = defaultdict(int)  # by component
        self.queue_depth_samples = []
        self.start_time = time.time()
        
    def record_request_start(self, endpoint: str):
        self.request_count[endpoint] += 1
        self.request_in_progress[endpoint] += 1
        
    def record_request_end(self, endpoint: str, duration: float, status_code: int):
        self.request_duration[endpoint].append(duration)
        self.request_in_progress[endpoint] -= 1
        if status_code >= 400:
            self.error_count[f"{endpoint}_{status_code}"] += 1
            
    def record_circuit_breaker_trip(self, component: str):
        self.circuit_breaker_trips[component] += 1
        
    def record_queue_depth(self, depth: int):
        self.queue_depth_samples.append(depth)
        # Keep only last 1000 samples
        if len(self.queue_depth_samples) > 1000:
            self.queue_depth_samples = self.queue_depth_samples[-1000:]
    
    def get_metrics_text(self) -> str:
        """Generate Prometheus-compatible metrics"""
        lines = []
        
        # Process info
        lines.append("# HELP astra_info ASTRA Core information")
        lines.append("# TYPE astra_info gauge")
        lines.append(f'astra_info{{version="1.0.0"}} 1')
        
        # Uptime
        uptime = time.time() - self.start_time
        lines.append("# HELP astra_uptime_seconds Uptime in seconds")
        lines.append("# TYPE astra_uptime_seconds counter")
        lines.append(f"astra_uptime_seconds {uptime:.2f}")
        
        # Request counts
        lines.append("# HELP astra_requests_total Total requests by endpoint")
        lines.append("# TYPE astra_requests_total counter")
        for endpoint, count in self.request_count.items():
            lines.append(f'astra_requests_total{{endpoint="{endpoint}"}} {count}')
        
        # Requests in progress
        lines.append("# HELP astra_requests_in_progress Current requests in progress")
        lines.append("# TYPE astra_requests_in_progress gauge")
        for endpoint, count in self.request_in_progress.items():
            if count > 0:
                lines.append(f'astra_requests_in_progress{{endpoint="{endpoint}"}} {count}')
        
        # Request duration percentiles
        lines.append("# HELP astra_request_duration_seconds Request duration in seconds")
        lines.append("# TYPE astra_request_duration_seconds summary")
        for endpoint, durations in self.request_duration.items():
            if durations:
                sorted_durations = sorted(durations)
                count = len(sorted_durations)
                total = sum(sorted_durations)
                p50 = sorted_durations[int(count * 0.5)] if count > 0 else 0
                p95 = sorted_durations[int(count * 0.95)] if count > 0 else 0
                p99 = sorted_durations[int(count * 0.99)] if count > 0 else 0
                
                lines.append(f'astra_request_duration_seconds{{endpoint="{endpoint}",quantile="0.5"}} {p50:.4f}')
                lines.append(f'astra_request_duration_seconds{{endpoint="{endpoint}",quantile="0.95"}} {p95:.4f}')
                lines.append(f'astra_request_duration_seconds{{endpoint="{endpoint}",quantile="0.99"}} {p99:.4f}')
                lines.append(f'astra_request_duration_seconds_sum{{endpoint="{endpoint}"}} {total:.4f}')
                lines.append(f'astra_request_duration_seconds_count{{endpoint="{endpoint}"}} {count}')
        
        # Error counts
        lines.append("# HELP astra_errors_total Total errors by endpoint and status")
        lines.append("# TYPE astra_errors_total counter")
        for key, count in self.error_count.items():
            lines.append(f'astra_errors_total{{error="{key}"}} {count}')
        
        # Circuit breaker trips
        lines.append("# HELP astra_circuit_breaker_trips_total Circuit breaker trips by component")
        lines.append("# TYPE astra_circuit_breaker_trips_total counter")
        for component, count in self.circuit_breaker_trips.items():
            lines.append(f'astra_circuit_breaker_trips_total{{component="{component}"}} {count}')
        
        # Queue depth
        if self.queue_depth_samples:
            avg_depth = sum(self.queue_depth_samples) / len(self.queue_depth_samples)
            max_depth = max(self.queue_depth_samples)
            lines.append("# HELP astra_queue_depth Queue depth statistics")
            lines.append("# TYPE astra_queue_depth gauge")
            lines.append(f"astra_queue_depth_avg {avg_depth:.2f}")
            lines.append(f"astra_queue_depth_max {max_depth}")
        
        return "\n".join(lines) + "\n"

metrics = MetricsCollector()

# Global state
class ServerState:
    def __init__(self):
        self.is_ready = True  # Server ready for traffic
        self.is_draining = False  # Server in drain mode
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.queue_depth = 0
        self.max_queue_depth = 100  # Backpressure threshold
        self.circuit_breakers = {
            "llm": {"failures": 0, "last_failure": 0, "threshold": 5},
            "memory": {"failures": 0, "last_failure": 0, "threshold": 5},
        }
        self.last_health_check = {
            "llm": True,
            "memory": True,
            "identity": True
        }
        
state = ServerState()

# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("server_starting", time=datetime.utcnow().isoformat())
    yield
    # Shutdown
    logger.info("server_stopping", time=datetime.utcnow().isoformat())
    state.is_ready = False
    state.is_draining = True
    await asyncio.sleep(2)  # Allow in-flight requests to complete

# Create FastAPI app
app = FastAPI(
    title="ASTRA Core",
    description="ASTRA Core API Spine",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class Query(BaseModel):
    query: str
    max_tokens: Optional[int] = Field(default=1024, gt=0, le=4096)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    stream: Optional[bool] = Field(default=False)

class Answer(BaseModel):
    answer: str
    latency_ms: int
    tokens_used: int
    queue_time_ms: int
    citations: List[Dict[str, Any]] = []
    warnings: List[str] = []

class HealthStatus(BaseModel):
    status: str
    components: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]
# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    # Skip metrics endpoint from tracking to avoid recursion
    if request.url.path == "/metrics":
        return await call_next(request)
    
    # Check rate limiting
    if not rate_limiter.allow_request(request.url.path):
        metrics.record_request_start(request.url.path)
        metrics.record_request_end(request.url.path, 0, 429)
        limit = rate_limiter.get_limit(request.url.path)
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "limit": limit, "window": "1s"}
        )
    
    # Check backpressure
    if state.queue_depth >= state.max_queue_depth:
        metrics.record_request_start(request.url.path)
        metrics.record_request_end(request.url.path, 0, 503)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Server under high load", "retry_after": 30}
        )
        
    # Track request
    state.request_count += 1
    state.queue_depth += 1
    start_time = time.time()
    
    # Record metrics
    metrics.record_request_start(request.url.path)
    metrics.record_queue_depth(state.queue_depth)
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        metrics.record_request_end(request.url.path, duration, response.status_code)
        return response
    except Exception as e:
        state.error_count += 1
        duration = time.time() - start_time
        metrics.record_request_end(request.url.path, duration, 500)
        logger.error("request_failed", error=str(e))
        raise
    finally:
        state.queue_depth -= 1
        logger.info(
            "request_complete",
            path=request.url.path,
            duration_ms=int((time.time() - start_time) * 1000),
            queue_depth=state.queue_depth
        )

# Metrics Endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint"""
    return Response(
        content=metrics.get_metrics_text(),
        media_type="text/plain; version=0.0.4"
    )

# Health Check Endpoints
@app.get("/live", response_model=Dict[str, str])
async def live():
    """Basic liveness check"""
    return {"status": "live"}

@app.get("/ready", response_model=Dict[str, str])
async def ready():
    """Readiness check - considers drain state"""
    if state.is_draining:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "draining"}
        )
    return {"status": "ready" if state.is_ready else "not_ready"}

@app.get("/health/full", response_model=HealthStatus)
async def health_full():
    """Detailed health check with component status"""
    # Update component health
    for component in ["llm", "memory"]:
        if state.circuit_breakers[component]["failures"] >= state.circuit_breakers[component]["threshold"]:
            state.last_health_check[component] = False
            
    uptime = int(time.time() - state.start_time)
    error_rate = state.error_count / max(state.request_count, 1)
    
    return {
        "status": "healthy" if all(state.last_health_check.values()) else "degraded",
        "components": {
            "llm": {
                "status": "healthy" if state.last_health_check["llm"] else "failing",
                "failures": state.circuit_breakers["llm"]["failures"]
            },
            "memory": {
                "status": "healthy" if state.last_health_check["memory"] else "failing",
                "failures": state.circuit_breakers["memory"]["failures"]
            },
            "identity": {
                "status": "healthy" if state.last_health_check["identity"] else "failing"
            }
        },
        "metrics": {
            "uptime_seconds": uptime,
            "request_count": state.request_count,
            "error_rate": error_rate,
            "queue_depth": state.queue_depth,
            "latency_p95": 120,  # TODO: Implement real p95 tracking
            "memory_usage_mb": 256  # TODO: Implement real memory tracking
        }
    }


# Circuit breaker check
async def check_circuit_breakers(components: List[str]) -> bool:
    """Check if any required components have tripped circuit breakers"""
    for component in components:
        if component in state.circuit_breakers:
            breaker = state.circuit_breakers[component]
            if breaker["failures"] >= breaker["threshold"]:
                # Check if enough time has passed to retry
                if time.time() - breaker["last_failure"] > 60:  # 1 minute retry
                    breaker["failures"] = 0  # Reset and retry
                else:
                    return False
    return True

@app.post("/drain")
async def drain():
    """Initiate graceful shutdown"""
    state.is_draining = True
    state.is_ready = False
    logger.info("drain_initiated", queue_depth=state.queue_depth)
    return {"status": "draining", "queue_depth": state.queue_depth}

@app.post("/answer", response_model=Answer)
async def answer(query: Query, request: Request):
    """
    Process query and return answer with metrics
    
    Implements:
    - Queue depth monitoring
    - Circuit breaker pattern
    - Response envelope with metrics
    - Citation tracking
    """
    start_time = time.time()
    query_id = str(state.request_count)
    
    # Check circuit breakers
    if not await check_circuit_breakers(["llm", "memory"]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily degraded"
        )
    
    try:
        # Simulate processing with backpressure awareness
        await asyncio.sleep(0.1 * min(5, state.queue_depth))  # Increased latency under load
        
        # Process query
        answer_text = f"Processed query: {query.query}"
        citations = [{"source": "memory_1", "relevance": 0.95}]
        
        return Answer(
            answer=answer_text,
            latency_ms=int((time.time() - start_time) * 1000),
            tokens_used=len(answer_text.split()),
            queue_time_ms=10,
            citations=citations
        )
        
    except Exception as e:
        # Update circuit breaker state
        state.circuit_breakers["llm"]["failures"] += 1
        state.circuit_breakers["llm"]["last_failure"] = time.time()
        metrics.record_circuit_breaker_trip("llm")
        logger.error("answer_failed", error=str(e), query_id=query_id)
        raise HTTPException(status_code=500, detail="Internal processing error")

async def stream_generator(query: str, query_id: str) -> AsyncIterator[str]:
    """
    Generate streaming response with proper SSE formatting
    """
    try:
        chunks = [
            {"type": "start", "text": "Starting response...", "query_id": query_id},
            {"type": "content", "text": f"Processing query: {query}", "query_id": query_id},
            {"type": "citation", "text": "Source: memory_1", "query_id": query_id},
            {"type": "content", "text": "Here is more content...", "query_id": query_id},
            {"type": "end", "text": "Response complete", "query_id": query_id}
        ]
        
        for chunk in chunks:
            yield f"data: {json.dumps(chunk)}\n\n"
            # Simulate varying processing time with backpressure
            await asyncio.sleep(0.1 * min(3, state.queue_depth))
            
    except Exception as e:
        error_chunk = {
            "type": "error",
            "text": "Stream processing error",
            "query_id": query_id
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        state.error_count += 1
        logger.error("stream_failed", error=str(e), query_id=query_id)

@app.post("/answer/stream")
async def stream_answer(query: Query):
    """
    Streaming answer endpoint with SSE
    """
    if not await check_circuit_breakers(["llm", "memory"]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily degraded"
        )
    
    query_id = str(state.request_count)
    return StreamingResponse(
        stream_generator(query.query, query_id),
        media_type='text/event-stream'
    )


# Signal handlers
def handle_sigterm(*args):
    """Handle SIGTERM for graceful shutdown"""
    logger.info("sigterm_received")
    state.is_draining = True
    state.is_ready = False

if __name__ == "__main__":
    try:
        # Configure structured logging first
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ]
        )
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, handle_sigterm)
        
        # Configure uvicorn logging
        uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
        uvicorn_log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
        
        logger.info("server_initializing", 
                   host="127.0.0.1",
                   port=8001,
                   mode="production")
        
        # Run server with enhanced error handling - use app object directly to avoid reload issues on Windows
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8001,
            reload=False,  # Disable reload on Windows to avoid signal handling issues
            log_config=uvicorn_log_config,
            log_level="debug",
            timeout_keep_alive=65,
            limit_concurrency=100
        )
    except KeyboardInterrupt:
        logger.info("server_interrupted")
    except Exception as e:
        logger.error("server_failed_to_start",
                    error=str(e),
                    exc_info=True)
        raise
