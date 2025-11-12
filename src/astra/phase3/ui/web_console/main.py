"""FastAPI web console for ASTRA Operator Dashboard.

Provides REST endpoints for console status, metrics, logs, and command routing.
"""
import asyncio
import json
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel


class StatusResponse(BaseModel):
    """System status response."""

    uptime_seconds: float
    active_tasks: int
    memory_mb: float
    cpu_percent: float
    vector_store_size: int
    inference_latency_ms: float


class MetricsResponse(BaseModel):
    """Detailed metrics response."""

    timestamp: float
    uptime: float
    tasks_active: int
    memory_usage_mb: float
    cpu_usage_percent: float
    vector_store_entries: int
    inference_latency_p50_ms: float
    inference_latency_p95_ms: float


class ConsoleManager:
    """Manages console state and system access."""

    def __init__(self) -> None:
        """Initialize console manager."""
        self.start_time = time.time()
        self.log_buffer: list[str] = []

    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.start_time

    def get_status(self) -> StatusResponse:
        """Get current system status."""
        return StatusResponse(
            uptime_seconds=self.get_uptime(),
            active_tasks=3,
            memory_mb=512.5,
            cpu_percent=45.2,
            vector_store_size=15000,
            inference_latency_ms=245.3,
        )

    def get_metrics(self) -> MetricsResponse:
        """Get detailed system metrics."""
        return MetricsResponse(
            timestamp=time.time(),
            uptime=self.get_uptime(),
            tasks_active=3,
            memory_usage_mb=512.5,
            cpu_usage_percent=45.2,
            vector_store_entries=15000,
            inference_latency_p50_ms=245.3,
            inference_latency_p95_ms=380.1,
        )

    def add_log(self, message: str) -> None:
        """Add a message to the log buffer."""
        self.log_buffer.append(f"{time.time():.3f} | {message}")
        # Keep last 1000 lines
        if len(self.log_buffer) > 1000:
            self.log_buffer = self.log_buffer[-1000:]

    async def stream_logs(self) -> AsyncGenerator[str, None]:
        """Stream logs as Server-Sent Events."""
        last_index = 0
        while True:
            new_logs = self.log_buffer[last_index:]
            for log in new_logs:
                yield f"data: {json.dumps({'message': log})}\n\n"
                last_index += 1
            await asyncio.sleep(0.1)


# Global console manager
console_manager = ConsoleManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # type: ignore[misc]
    """FastAPI lifespan context manager."""
    # Startup
    console_manager.add_log("Web console started")
    yield
    # Shutdown
    console_manager.add_log("Web console shutting down")


app = FastAPI(title="ASTRA Operator Console API", lifespan=lifespan)


@app.get("/v1/console/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get current system status."""
    console_manager.add_log("Status check requested")
    return console_manager.get_status()


@app.get("/v1/console/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """Get detailed metrics."""
    console_manager.add_log("Metrics requested")
    return console_manager.get_metrics()


@app.get("/v1/console/logs")
async def stream_logs() -> StreamingResponse:
    """Stream logs as Server-Sent Events."""
    console_manager.add_log("Log stream opened")
    return StreamingResponse(
        console_manager.stream_logs(),
        media_type="text/event-stream",
    )


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "uptime": console_manager.get_uptime()})


@app.post("/v1/console/log")
async def post_log(message: str) -> JSONResponse:
    """Post a log message."""
    console_manager.add_log(message)
    return JSONResponse({"status": "logged"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
