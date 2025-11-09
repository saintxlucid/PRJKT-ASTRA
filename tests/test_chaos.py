"""
Chaos test scenarios for ASTRA server resilience
"""
import pytest
import asyncio
import aiohttp
import random
import json
import time
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_HOST = "http://localhost:8001"
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

class ChaosScenario:
    """Base class for chaos test scenarios"""
    def __init__(self, name: str, duration: int = 30):
        self.name = name
        self.duration = duration
        self.start_time = None
        
    async def setup(self):
        """Setup chaos conditions"""
        self.start_time = time.time()
        logger.info(f"Starting chaos scenario: {self.name}")
        
    async def cleanup(self):
        """Cleanup after chaos test"""
        logger.info(f"Cleaning up chaos scenario: {self.name}")
        
    async def run(self):
        """Execute chaos scenario"""
        raise NotImplementedError
        
    def is_complete(self) -> bool:
        """Check if scenario duration is complete"""
        return time.time() - self.start_time >= self.duration

class BurstyTrafficScenario(ChaosScenario):
    """Generate bursty traffic patterns"""
    async def run(self, client: aiohttp.ClientSession):
        while not self.is_complete():
            # Generate burst of requests
            burst_size = random.randint(50, 200)
            tasks = []
            for _ in range(burst_size):
                tasks.append(
                    client.post(
                        f"{TEST_HOST}/answer",
                        json={"query": "Burst test"},
                        headers=REQUEST_HEADERS
                    )
                )
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify backpressure kicks in
            status_codes = [
                r.status if isinstance(r, aiohttp.ClientResponse) else 500
                for r in responses
            ]
            assert any(c in (429, 503) for c in status_codes), "No backpressure detected"
            
            # Brief pause between bursts
            await asyncio.sleep(random.uniform(1, 5))

class CircuitBreakerScenario(ChaosScenario):
    """Force circuit breaker activation"""
    async def run(self, client: aiohttp.ClientSession):
        error_count = 0
        while not self.is_complete():
            # Send requests likely to trigger errors
            async with client.post(
                f"{TEST_HOST}/answer",
                json={"query": "error"},
                headers=REQUEST_HEADERS
            ) as response:
                if response.status != 200:
                    error_count += 1
                    
            if error_count >= 5:
                # Verify circuit breaker state
                async with client.get(f"{TEST_HOST}/metrics") as response:
                    data = await response.json()
                    assert any(
                        breaker["state"] == "open"
                        for breaker in data["circuit_breakers"].values()
                    ), "Circuit breaker did not open"
                break
                
            await asyncio.sleep(0.1)

class DrainScenario(ChaosScenario):
    """Test drain behavior under load"""
    async def run(self, client: aiohttp.ClientSession):
        # Start background traffic
        background_tasks = []
        for _ in range(50):
            background_tasks.append(
                client.post(
                    f"{TEST_HOST}/answer/stream",
                    json={"query": "Long running request"},
                    headers={"Accept": "text/event-stream"}
                )
            )
        
        # Initiate drain
        async with client.post(f"{TEST_HOST}/drain") as response:
            assert response.status == 200
            drain_start = time.time()
            
        # Monitor drain completion
        while not self.is_complete():
            async with client.get(f"{TEST_HOST}/ready") as response:
                data = await response.json()
                if response.status == 503 and data["draining"]:
                    drain_time = time.time() - drain_start
                    assert drain_time < 10, "Drain took too long"
                    break
            await asyncio.sleep(0.1)
        
        # Cancel background tasks
        for task in background_tasks:
            if not task.done():
                task.cancel()

class ResourceExhaustionScenario(ChaosScenario):
    """Test behavior under resource pressure"""
    async def run(self, client: aiohttp.ClientSession):
        # Create memory pressure
        long_requests = []
        for _ in range(100):
            long_requests.append(
                client.post(
                    f"{TEST_HOST}/answer",
                    json={"query": "X" * 10000},  # Large request
                    headers=REQUEST_HEADERS
                )
            )
        
        responses = await asyncio.gather(*long_requests, return_exceptions=True)
        
        # Verify graceful degradation
        error_responses = [r for r in responses if isinstance(r, Exception)]
        success_responses = [r for r in responses if isinstance(r, aiohttp.ClientResponse)]
        
        assert len(error_responses) > 0, "No backpressure under load"
        assert len(success_responses) > 0, "All requests failed"

@pytest.mark.asyncio
async def test_chaos_scenarios(http_client):
    """Run all chaos test scenarios"""
    scenarios = [
        BurstyTrafficScenario("bursty-traffic", duration=30),
        CircuitBreakerScenario("circuit-breaker", duration=30),
        DrainScenario("drain-sequence", duration=30),
        ResourceExhaustionScenario("resource-exhaustion", duration=30)
    ]
    
    for scenario in scenarios:
        await scenario.setup()
        try:
            await scenario.run(http_client)
        finally:
            await scenario.cleanup()
            
        # Brief pause between scenarios
        await asyncio.sleep(5)
        
        # Verify server health
        async with http_client.get(f"{TEST_HOST}/health") as response:
            assert response.status == 200, "Server unhealthy after chaos test"
            
@pytest.mark.asyncio
async def test_metrics_stability():
    """Verify metrics stability during chaos"""
    async with aiohttp.ClientSession() as client:
        # Collect metrics over time
        samples = []
        for _ in range(10):
            async with client.get(f"{TEST_HOST}/metrics") as response:
                assert response.status == 200
                data = await response.json()
                samples.append(data)
            await asyncio.sleep(1)
        
        # Verify metric consistency
        for sample in samples:
            assert "backpressure" in sample
            assert "circuit_breakers" in sample
            assert sample["backpressure"]["queue_depth"] >= 0
            assert all(
                breaker["state"] in ("closed", "open", "half_open")
                for breaker in sample["circuit_breakers"].values()
            )