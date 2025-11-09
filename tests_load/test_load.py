"""
Synthetic load testing for ASTRA API
Created: October 31, 2025

Tests concurrent user load, backpressure, and circuit breaker behavior.
"""
import asyncio
import aiohttp
import pytest
import json
import time
import structlog
from typing import List, Dict, Any
from datetime import datetime, UTC
from statistics import mean, median, stdev
from dataclasses import dataclass
import uvicorn
import multiprocessing
from pathlib import Path
import sys

# Add src to path for importing ASTRA modules
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from astra.app import app

logger = structlog.get_logger(__name__)

@dataclass
class LoadTestConfig:
    """Configuration for load test parameters"""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 10
    requests_per_user: int = 50
    think_time_min: float = 0.1
    think_time_max: float = 0.5
    test_duration: int = 60  # seconds

@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    endpoint: str
    status_code: int
    response_time: float
    timestamp: str
    is_error: bool = False
    error_message: str = ""

class LoadTestRunner:
    """Executes synthetic load tests against ASTRA API"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.metrics: List[RequestMetrics] = []
        self.server_process = None
        
    async def simulate_user(self, user_id: int, session: aiohttp.ClientSession):
        """Simulate a single user's behavior
        
        Args:
            user_id: Unique user identifier
            session: aiohttp client session
        """
        logger.info("user_started", user_id=user_id)
        
        for i in range(self.config.requests_per_user):
            # Simulate user think time
            think_time = self.config.think_time_min + (
                self.config.think_time_max - self.config.think_time_min
            ) * (i / self.config.requests_per_user)
            await asyncio.sleep(think_time)
            
            # Send request
            start_time = time.time()
            try:
                async with session.post(
                    f"{self.config.base_url}/answer",
                    params={
                        "query": f"Test query from user {user_id}, request {i}",
                        "conversation_id": f"test-{user_id}-{i}"
                    }
                ) as response:
                    status_code = response.status
                    response_time = time.time() - start_time
                    response_data = await response.json()
                    
                    metrics = RequestMetrics(
                        endpoint="/answer",
                        status_code=status_code,
                        response_time=response_time,
                        timestamp=datetime.now(UTC).isoformat(),
                        is_error=status_code >= 400,
                        error_message=response_data.get("error", {}).get("message", "") if status_code >= 400 else ""
                    )
                    self.metrics.append(metrics)
                    
            except Exception as e:
                logger.error(
                    "request_failed",
                    user_id=user_id,
                    request_num=i,
                    error=str(e)
                )
                self.metrics.append(
                    RequestMetrics(
                        endpoint="/answer",
                        status_code=500,
                        response_time=time.time() - start_time,
                        timestamp=datetime.now(UTC).isoformat(),
                        is_error=True,
                        error_message=str(e)
                    )
                )
                
        logger.info("user_completed", user_id=user_id)
    
    def start_server(self):
        """Start ASTRA server in separate process"""
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=8000)
            
        self.server_process = multiprocessing.Process(target=run_server)
        self.server_process.start()
        time.sleep(2)  # Wait for server startup
        
    def stop_server(self):
        """Stop ASTRA server"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.join()
    
    async def run(self):
        """Execute load test with concurrent users"""
        try:
            # Start test server
            self.start_server()
            
            async with aiohttp.ClientSession() as session:
                # Create user tasks
                user_tasks = []
                for i in range(self.config.concurrent_users):
                    task = asyncio.create_task(
                        self.simulate_user(i, session)
                    )
                    user_tasks.append(task)
                    
                # Wait for all users to complete or timeout
                done, pending = await asyncio.wait(
                    user_tasks,
                    timeout=self.config.test_duration
                )
                
                # Cancel any remaining tasks
                for task in pending:
                    task.cancel()
                    
            return self.analyze_results()
            
        finally:
            self.stop_server()
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze load test results
        
        Returns:
            Dictionary of test metrics and statistics
        """
        if not self.metrics:
            return {"error": "No metrics collected"}
            
        # Calculate response time statistics
        response_times = [m.response_time for m in self.metrics]
        error_count = sum(1 for m in self.metrics if m.is_error)
        
        analysis = {
            "summary": {
                "total_requests": len(self.metrics),
                "successful_requests": len(self.metrics) - error_count,
                "failed_requests": error_count,
                "error_rate": error_count / len(self.metrics)
            },
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": mean(response_times),
                "median": median(response_times),
                "stdev": stdev(response_times) if len(response_times) > 1 else 0
            },
            "status_codes": {}
        }
        
        # Count status codes
        for metrics in self.metrics:
            status = str(metrics.status_code)
            if status not in analysis["status_codes"]:
                analysis["status_codes"][status] = 0
            analysis["status_codes"][status] += 1
            
        return analysis

@pytest.mark.asyncio
async def test_normal_load():
    """Test normal load conditions"""
    config = LoadTestConfig(
        concurrent_users=5,
        requests_per_user=20,
        test_duration=30
    )
    runner = LoadTestRunner(config)
    results = await runner.run()
    
    # Validate results
    assert results["summary"]["error_rate"] < 0.1
    assert results["response_times"]["median"] < 1.0
    assert results["status_codes"].get("429", 0) == 0  # No backpressure
    assert results["status_codes"].get("503", 0) == 0  # No circuit breaking

@pytest.mark.asyncio
async def test_high_load():
    """Test high load conditions"""
    config = LoadTestConfig(
        concurrent_users=20,
        requests_per_user=50,
        test_duration=60
    )
    runner = LoadTestRunner(config)
    results = await runner.run()
    
    # Validate backpressure and circuit breaking
    assert results["status_codes"].get("429", 0) > 0  # Some backpressure
    assert results["summary"]["error_rate"] < 0.3  # Limited errors
    
@pytest.mark.asyncio
async def test_streaming_load():
    """Test streaming endpoint under load"""
    config = LoadTestConfig(
        concurrent_users=10,
        requests_per_user=10,
        test_duration=30
    )
    runner = LoadTestRunner(config)
    
    async def stream_user(user_id: int, session: aiohttp.ClientSession):
        """Simulate streaming user"""
        async with session.post(
            f"{config.base_url}/answer/stream",
            params={
                "query": f"Test stream {user_id}",
                "conversation_id": f"stream-{user_id}"
            }
        ) as response:
            assert response.status == 200
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = json.loads(line.split(b"data: ")[1])
                    assert "chunk" in data
                    
    try:
        runner.start_server()
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(stream_user(i, session))
                for i in range(config.concurrent_users)
            ]
            await asyncio.gather(*tasks)
            
    finally:
        runner.stop_server()