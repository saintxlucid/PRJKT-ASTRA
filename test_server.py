"""
Test FastAPI server for load testing with full Phase 0 requirements
"""
import logging
import sys
from typing import Dict, Any, Optional, AsyncGenerator, AsyncContextManager
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from datetime import datetime
import random
import asyncio
import json
import traceback
import time

# Local imports
from server.health import health_manager, register_health_endpoints
from server.response_template import create_response, create_stream_chunk
from server.circuit_breakers import memory_circuit, inference_circuit, CircuitBreakerOpen
from server.backpressure import backpressure, handle_request, ThrottleError, QueueFullError
from server.metrics import metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ASTRA Test API",
    version="0.1.0",
    description="ASTRA test server with backpressure and circuit breakers"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling
# Custom exception handlers
@app.exception_handler(CircuitBreakerOpen)
async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpen) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": str(exc), "type": "circuit_breaker_open"}
    )

@app.exception_handler(ThrottleError)
async def throttle_handler(request: Request, exc: ThrottleError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": str(exc), "type": "throttling_active"}
    )

@app.exception_handler(QueueFullError)
async def queue_full_handler(request: Request, exc: QueueFullError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": str(exc), "type": "queue_full"}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Error processing request: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_tb(exc.__traceback__)
        }
    )

# Lifespan events
@app.router.lifespan_context
async def lifespan(app: FastAPI) -> AsyncContextManager[None]:
    """Lifespan events for startup and shutdown"""
    logger.info("Starting ASTRA Load Test Server...")
    
    # Initialize health checks
    await health_manager.start()
    await register_health_endpoints(app)
    
    yield
    
    # Graceful shutdown
    logger.info("Initiating graceful shutdown...")
    await health_manager.begin_drain()
    await asyncio.sleep(5)  # Allow in-flight requests to complete
    await health_manager.stop()
    logger.info("Shutdown complete")

class QueryRequest(BaseModel):
    query: str

@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get server metrics and SLO status"""
    return {
        "metrics": metrics.get_metrics(),
        "slos": metrics.check_slos(),
        "backpressure": backpressure.get_stats(),
        "circuit_breakers": {
            "memory": {
                "state": memory_circuit.state.value,
                "failures": memory_circuit.failure_count
            },
            "inference": {
                "state": inference_circuit.state.value,
                "failures": inference_circuit.failure_count
            }
        }
    }

@app.post("/answer")
async def get_answer(request: QueryRequest) -> Dict[str, Any]:
    """Simulated answer endpoint with full safety controls"""
    async def process_answer() -> Dict[str, Any]:
        start_time = time.time()
        success = False
        token_count = 0
        
        try:
            # Simulate memory operation with circuit breaker
            async with memory_circuit:
                await asyncio.sleep(random.uniform(0.05, 0.2))
                if random.random() < 0.05:
                    raise Exception("Simulated memory error")
                    
                # Simulate cache hit/miss
                cache_hit = random.random() > 0.3
                metrics.track_memory(cache_hit=cache_hit)
            
            # Simulate inference with circuit breaker
            async with inference_circuit:
                await asyncio.sleep(random.uniform(0.1, 0.3))
                if random.random() < 0.03:
                    raise Exception("Simulated inference error")
                
                token_count = random.randint(50, 200)
                metrics.track_tokens(token_count)
            
            processing_time = time.time() - start_time
            success = True
            
            response = create_response(
                answer=f"This is a test response for: {request.query}",
                model="test-model",
                version="0.1.0",
                citations=[
                    {"text": "Sample citation", "source": "test-doc-1", "score": 0.95},
                    {"text": "Another citation", "source": "test-doc-2", "score": 0.85}
                ],
                processing_time=processing_time,
                token_count=token_count
            )
            
            # Track successful request
            metrics.track_request(
                duration=processing_time,
                success=True
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            # Track failed request
            metrics.track_request(
                duration=processing_time,
                success=False,
                timeout=isinstance(e, asyncio.TimeoutError)
            )
            raise
    
    # Handle request with backpressure
    return await handle_request(process_answer)
    
@app.post("/answer/stream")
async def stream_answer(request: QueryRequest) -> EventSourceResponse:
    """Simulated streaming answer endpoint with safety controls"""
    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        # Check backpressure first
        if backpressure.should_throttle():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "Service is throttling requests",
                    "error_type": "throttling"
                })
            }
            return
            
        if not await backpressure.acquire():
            yield {
                "event": "error", 
                "data": json.dumps({
                    "error": "Request queue is full",
                    "error_type": "queue_full"
                })
            }
            return
            
        start_time = time.time()
        success = True
        total_tokens = 0
        
        try:
            chunks = [
                "This ", "is ", "a ", "test ", "streaming ",
                "response ", "for: ", request.query
            ]
            
            # Verify memory circuit first
            async with memory_circuit:
                await asyncio.sleep(0.1)  # Simulate memory check
                # Track cache operation
                cache_hit = random.random() > 0.3
                metrics.track_memory(cache_hit=cache_hit)
            
            for i, chunk in enumerate(chunks):
                try:
                    # Use inference circuit per chunk
                    async with inference_circuit:
                        await asyncio.sleep(random.uniform(0.05, 0.2))
                        
                        # Random error injection (1% chance per chunk)
                        if random.random() < 0.01:
                            raise Exception("Simulated streaming error")
                            
                        # Track tokens for this chunk
                        chunk_tokens = len(chunk.split())
                        total_tokens += chunk_tokens
                        metrics.track_tokens(chunk_tokens)
                        
                        # Create chunk response
                        response = create_stream_chunk(
                            chunk=chunk,
                            chunk_id=i,
                            is_final=i == len(chunks) - 1,
                            citations=[
                                {"text": "Stream citation", "source": "test-doc-1", "score": 0.9}
                            ] if i == len(chunks) - 1 else [],
                            metadata={
                                "model": "test-model-stream",
                                "chunk_time": random.uniform(0.05, 0.2)
                            }
                        )
                        
                        # Convert response to JSON
                        json_response = json.dumps(response)
                        logger.debug(f"Sending chunk {i}: {json_response[:100]}...")
                        
                        yield {
                            "event": "message",
                            "data": json_response
                        }
                        
                except CircuitBreakerOpen as circuit_error:
                    success = False
                    logger.error(f"Circuit breaker opened: {str(circuit_error)}")
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": str(circuit_error),
                            "error_type": "circuit_breaker",
                            "chunk_id": i
                        })
                    }
                    break
                    
                except Exception as chunk_error:
                    success = False
                    logger.error(f"Error processing chunk {i}: {str(chunk_error)}")
                    logger.error(traceback.format_exc())
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": str(chunk_error),
                            "error_type": "chunk_error",
                            "chunk_id": i
                        })
                    }
                    break
                    
        except Exception as e:
            success = False
            logger.error(f"Stream generator error: {str(e)}")
            logger.error(traceback.format_exc())
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "error_type": "stream_error"
                })
            }
        finally:
            processing_time = time.time() - start_time
            # Track request metrics
            metrics.track_request(
                duration=processing_time,
                success=success,
                timeout=False
            )
            # Always release backpressure
            backpressure.release(processing_time)

    # Create and return EventSourceResponse with proper content type
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

async def run_server():
    """Run the test server"""
    import uvicorn
    from uvicorn.config import Config
    from uvicorn.server import Server
    import signal
    import sys
    import asyncio
    
    # Get a logger for this function
    server_logger = logging.getLogger(__name__)
    
    # Single process configuration for testing
    config = Config(
        app=app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        workers=1,
        limit_concurrency=100,
        timeout_keep_alive=30,
        access_log=True
    )
    
    server = Server(config=config)
    
    # Track server state
    running = True
    
    def signal_handler(signum):
        nonlocal running
        server_logger.info(f"Received signal {signum}, initiating shutdown...")
        running = False
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: signal_handler(s)
        )
    
    # Start server
    server_logger.info("Starting ASTRA Load Test Server on port 8001...")
    try:
        await server.serve()
    except Exception as e:
        server_logger.error(f"Server error: {str(e)}")
        server_logger.error(traceback.format_exc())
        return 1
    
    server_logger.info("Server shutdown complete")
    return 0

if __name__ == "__main__":
    # Run with asyncio
    import asyncio
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Main error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)