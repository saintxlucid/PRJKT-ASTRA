"""
Load test suite for ASTRA server
"""
import asyncio
import pytest
import aiohttp
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class LoadTestSession:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics: Dict[str, Any] = {
            "requests": 0,
            "errors": 0,
            "latencies": []
        }
        
    async def __aenter__(self) -> 'LoadTestSession':
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    def _track_request(self, success: bool, latency: float):
        """Track request metrics"""
        self.metrics["requests"] += 1
        if not success:
            self.metrics["errors"] += 1
        self.metrics["latencies"].append(latency)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get test statistics"""
        latencies = sorted(self.metrics["latencies"])
        return {
            "requests": self.metrics["requests"],
            "errors": self.metrics["errors"],
            "error_rate": self.metrics["errors"] / max(1, self.metrics["requests"]),
            "latency": {
                "p50": latencies[len(latencies) // 2] if latencies else 0,
                "p95": latencies[int(len(latencies) * 0.95)] if latencies else 0,
                "p99": latencies[int(len(latencies) * 0.99)] if latencies else 0
            }
        }
            
    async def check_health(self) -> Dict[str, Any]:
        """Check server health status"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        start = time.time()
        success = False
        
        try:
            async with self.session.get(f"{self.base_url}/health/full") as response:
                data = await response.json()
                success = response.status == 200
                return data
        finally:
            self._track_request(success, time.time() - start)
            
    async def make_request(self, query: str) -> Dict[str, Any]:
        """Make a request to the answer endpoint"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        start = time.time()
        success = False
        
        try:
            async with self.session.post(
                f"{self.base_url}/answer",
                json={"query": query}
            ) as response:
                data = await response.json()
                success = response.status == 200
                return data
        finally:
            self._track_request(success, time.time() - start)
            
    async def stream_request(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a request and yield chunks"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        start = time.time()
        success = False
        chunks = []
        
        try:
            async with self.session.post(
                f"{self.base_url}/answer/stream",
                json={"query": query}
            ) as response:
                async for line in response.content:
                    if line.startswith(b'data:'):
                        chunk = json.loads(line.decode('utf-8').replace('data: ', ''))
                        chunks.append(chunk)
                        yield chunk
                success = response.status == 200
        finally:
            self._track_request(success, time.time() - start)

@pytest.mark.asyncio
async def test_health_checks():
    """Test health check endpoints"""
    async with LoadTestSession() as session:
        # Check liveness
        async with session.session.get("http://localhost:8001/live") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "live"
            
        # Check readiness
        async with session.session.get("http://localhost:8001/ready") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "ready"
            
        # Check full health
        health = await session.check_health()
        assert health["status"] in ["healthy", "degraded"]
        assert "components" in health
        assert "metrics" in health
        
@pytest.mark.asyncio
async def test_basic_load():
    """Test basic load handling"""
    async with LoadTestSession() as session:
        tasks = []
        for i in range(10):
            tasks.append(session.make_request(f"Test query {i}"))
            
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        
        stats = session.get_stats()
        assert stats["error_rate"] < 0.1  # Less than 10% errors
        assert stats["latency"]["p95"] < 2.5  # p95 under 2.5s
        
@pytest.mark.asyncio
async def test_streaming_load():
    """Test streaming load handling"""
    async with LoadTestSession() as session:
        async def stream_and_collect(query: str):
            chunks = []
            async for chunk in session.stream_request(query):
                chunks.append(chunk)
            return chunks
            
        tasks = []
        for i in range(5):
            tasks.append(stream_and_collect(f"Stream query {i}"))
            
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(len(chunks) > 0 for chunks in results)
        
        stats = session.get_stats()
        assert stats["error_rate"] < 0.1
        
@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling under load"""
    async with LoadTestSession() as session:
        # Trigger memory errors
        tasks = []
        for i in range(20):
            tasks.append(session.make_request("error " * 100))  # Large input
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check circuit breaker behavior
        health = await session.check_health()
        assert any(comp["status"] == "degraded" for comp in health["components"].values())
        
        # Verify metrics tracking
        stats = session.get_stats()
        assert "error_rate" in stats
        
@pytest.mark.asyncio
async def test_graceful_shutdown():
    """Test graceful shutdown behavior"""
    async with LoadTestSession() as session:
        # Start some long-running requests
        long_tasks = []
        for i in range(5):
            long_tasks.append(session.stream_request("long query"))
            
        # Initiate drain
        async with session.session.post("http://localhost:8001/drain") as response:
            assert response.status == 200
            
        # Try new requests - should be rejected
        async with session.session.get("http://localhost:8001/ready") as response:
            assert response.status == 503
            data = await response.json()
            assert data["status"] == "draining"
            
        # Verify in-flight requests complete
        results = await asyncio.gather(*long_tasks, return_exceptions=True)
        assert len(results) == 5

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pytest.main([__file__, "-v"])