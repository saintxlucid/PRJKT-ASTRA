"""
Load Testing Script

Async stress test with configurable concurrency and duration.
Tracks p50/p95/p99 latency and throughput.

Usage:
    # Test with 24 concurrent users for 45 seconds
    ASTRA_LOAD_CONC=24 ASTRA_LOAD_SECS=45 python scripts/load_test.py
    
    # Custom endpoint
    ASTRA_LOAD_URL=http://localhost:8080/v1/chat/completions python scripts/load_test.py

Environment Variables:
    ASTRA_LOAD_URL - Full target URL (overrides BASE + path)
    ASTRA_BACKEND_URL - Base backend URL (default: http://127.0.0.1:8080)
    ASTRA_LOAD_METHOD - HTTP method (GET or POST, default: POST)
    ASTRA_LOAD_CONC - Concurrent requests (default: 12)
    ASTRA_LOAD_SECS - Duration in seconds (default: 30)
    ASTRA_LOAD_PAYLOAD - JSON file with request payload (default: inline payload)
    ASTRA_LOAD_TIMEOUT - Request timeout in seconds (default: 15 for GET, 120 for others)
    ASTRA_LOAD_RPS - Target total requests per second (optional; default unlimited)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

import httpx
import structlog

logger = structlog.get_logger()

# Configuration
BACKEND_URL = os.getenv("ASTRA_BACKEND_URL", "http://127.0.0.1:8080")
METHOD = os.getenv("ASTRA_LOAD_METHOD", "POST").upper()
explicit_url = os.getenv("ASTRA_LOAD_URL")
if explicit_url:
    TARGET_URL = explicit_url
else:
    TARGET_URL = BACKEND_URL.rstrip("/") + "/v1/chat/"

CONCURRENCY = int(os.getenv("ASTRA_LOAD_CONC", "12"))
DURATION_SECS = int(os.getenv("ASTRA_LOAD_SECS", "30"))
PAYLOAD_FILE = os.getenv("ASTRA_LOAD_PAYLOAD")
TARGET_RPS_ENV = os.getenv("ASTRA_LOAD_RPS")

if TARGET_RPS_ENV is not None:
    try:
        TARGET_RPS = float(TARGET_RPS_ENV)
        if TARGET_RPS <= 0:
            raise ValueError
    except ValueError:
        raise SystemExit("ASTRA_LOAD_RPS must be a positive number when provided")
else:
    TARGET_RPS = None

DEFAULT_TIMEOUT = float(
    os.getenv(
        "ASTRA_LOAD_TIMEOUT",
        "15" if METHOD == "GET" else "120",
    )
)

# Default test payload
DEFAULT_PAYLOAD = {
    "conversation_id": None,
    "message": "Summarize why ASTRA uses semantic memory.",
    "use_memory": True,
    "temperature": 0.7,
    "max_tokens": 128,
}


@dataclass
class RequestResult:
    """Single request result"""
    latency: float  # seconds
    status: int
    success: bool
    error: str | None = None
    tokens: int = 0


@dataclass
class LoadTestStats:
    """Aggregated load test statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.total_requests == 0:
            return 0
        return 100 * self.successful_requests / self.total_requests
    
    @property
    def requests_per_second(self) -> float:
        """Average throughput"""
        if self.duration_seconds == 0:
            return 0
        return self.total_requests / self.duration_seconds
    
    @property
    def tokens_per_second(self) -> float:
        """Token throughput"""
        if self.duration_seconds == 0:
            return 0
        return self.total_tokens / self.duration_seconds
    
    def percentile(self, p: float) -> float:
        """Calculate latency percentile"""
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * p / 100)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def p50(self) -> float:
        """Median latency"""
        return self.percentile(50)
    
    @property
    def p95(self) -> float:
        """95th percentile latency"""
        return self.percentile(95)
    
    @property
    def p99(self) -> float:
        """99th percentile latency"""
        return self.percentile(99)
    
    @property
    def min_latency(self) -> float:
        """Minimum latency"""
        return min(self.latencies) if self.latencies else 0
    
    @property
    def max_latency(self) -> float:
        """Maximum latency"""
        return max(self.latencies) if self.latencies else 0


class LoadTester:
    """Async load testing engine"""
    
    def __init__(
        self,
        url: str,
        method: str,
        concurrency: int,
        duration: int,
        timeout: float,
        payload: Dict[str, Any] | None,
        target_rps: float | None,
    ):
        self.url = url
        self.method = method
        self.concurrency = concurrency
        self.duration = duration
        self.timeout = timeout
        self.payload = payload
        self.target_rps = target_rps
        self.stats = LoadTestStats()
        self.running = False

        if self.target_rps is not None:
            if self.concurrency <= 0:
                raise ValueError("Concurrency must be positive when using ASTRA_LOAD_RPS")
            self.worker_interval = self.concurrency / self.target_rps
        else:
            self.worker_interval = None
    
    async def send_request(self, client: httpx.AsyncClient) -> RequestResult:
        """Send single request and measure latency"""
        start = time.perf_counter()
        
        try:
            request_kwargs: Dict[str, Any] = {"timeout": self.timeout}
            if self.method != "GET" and self.payload is not None:
                request_kwargs["json"] = self.payload
            response = await client.request(self.method, self.url, **request_kwargs)
            latency = time.perf_counter() - start
            
            success = 200 <= response.status_code < 300
            tokens = 0
            
            if success and response.headers.get("content-type", "").startswith("application/json"):
                try:
                    data = response.json()
                    usage = data.get("usage", {})
                    tokens = usage.get("total_tokens", 0)
                except Exception:
                    pass
            
            return RequestResult(
                latency=latency,
                status=response.status_code,
                success=success,
                tokens=tokens
            )
        
        except Exception as e:
            latency = time.perf_counter() - start
            return RequestResult(
                latency=latency,
                status=0,
                success=False,
                error=str(e)
            )
    
    async def worker(self, worker_id: int, client: httpx.AsyncClient):
        """Worker coroutine that continuously sends requests"""
        logger.info("worker_started", worker_id=worker_id)
        
        while self.running:
            result = await self.send_request(client)
            
            # Update stats
            self.stats.total_requests += 1
            self.stats.latencies.append(result.latency)
            
            if result.success:
                self.stats.successful_requests += 1
                self.stats.total_tokens += result.tokens
            else:
                self.stats.failed_requests += 1
                error_key = result.error or f"HTTP {result.status}"
                self.stats.errors[error_key] = self.stats.errors.get(error_key, 0) + 1
            
            # Log progress every 10 requests
            if self.stats.total_requests % 10 == 0:
                logger.info("progress",
                           requests=self.stats.total_requests,
                           success_rate=f"{self.stats.success_rate:.1f}%",
                           rps=f"{self.stats.requests_per_second:.1f}")

            if self.worker_interval is not None and self.running:
                sleep_time = self.worker_interval - result.latency
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        logger.info("worker_stopped", worker_id=worker_id)
    
    async def run(self):
        """Run load test"""
        print("="*80)
        print("ASTRA LOAD TEST")
        print("="*80)
        print(f"Target URL: {self.url}")
        print(f"Method: {self.method}")
        print(f"Concurrency: {self.concurrency}")
        print(f"Duration: {self.duration}s")
        if self.target_rps is not None:
            print(f"Target RPS: {self.target_rps:.2f}")
        if self.payload is not None:
            print(f"Payload: {json.dumps(self.payload, indent=2)}")
        else:
            print("Payload: <none>")
        print("="*80)
        print("\nStarting load test...\n")
        
        self.running = True
        start_time = time.time()
        
        # Create HTTP client with connection pooling
        async with httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=self.concurrency * 2,
                max_keepalive_connections=self.concurrency
            )
        ) as client:
            # Start workers
            workers = [
                asyncio.create_task(self.worker(i, client))
                for i in range(self.concurrency)
            ]
            
            # Wait for duration
            await asyncio.sleep(self.duration)
            
            # Stop workers
            self.running = False
            
            # Wait for all workers to finish current requests
            await asyncio.gather(*workers, return_exceptions=True)
        
        self.stats.duration_seconds = time.time() - start_time
        
        # Print results
        self.print_results()
    
    def print_results(self):
        """Print formatted test results"""
        print("\n" + "="*80)
        print("LOAD TEST RESULTS")
        print("="*80)
        
        print(f"\nRequests:")
        print(f"  Total:      {self.stats.total_requests:,}")
        print(f"  Successful: {self.stats.successful_requests:,}")
        print(f"  Failed:     {self.stats.failed_requests:,}")
        print(f"  Success:    {self.stats.success_rate:.2f}%")
        
        print(f"\nThroughput:")
        print(f"  Requests/sec: {self.stats.requests_per_second:.2f}")
        print(f"  Tokens/sec:   {self.stats.tokens_per_second:.2f}")
        print(f"  Total tokens: {self.stats.total_tokens:,}")
        
        print(f"\nLatency (seconds):")
        print(f"  Min:  {self.stats.min_latency:.3f}")
        print(f"  p50:  {self.stats.p50:.3f}")
        print(f"  p95:  {self.stats.p95:.3f}")
        print(f"  p99:  {self.stats.p99:.3f}")
        print(f"  Max:  {self.stats.max_latency:.3f}")
        
        if self.stats.errors:
            print(f"\nErrors:")
            for error, count in sorted(self.stats.errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count}")
        
        print("\n" + "="*80)
        
        # Save results
        report = {
            "url": self.url,
            "concurrency": self.concurrency,
            "duration_seconds": self.stats.duration_seconds,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": round(self.stats.success_rate, 2),
            "requests_per_second": round(self.stats.requests_per_second, 2),
            "tokens_per_second": round(self.stats.tokens_per_second, 2),
            "total_tokens": self.stats.total_tokens,
            "latency": {
                "min": round(self.stats.min_latency, 3),
                "p50": round(self.stats.p50, 3),
                "p95": round(self.stats.p95, 3),
                "p99": round(self.stats.p99, 3),
                "max": round(self.stats.max_latency, 3)
            },
            "errors": self.stats.errors
        }
        
        report_path = f"data/logs/load_test_{int(time.time())}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport saved to: {report_path}\n")


async def main():
    """Main async entry point"""
    # Load payload
    if PAYLOAD_FILE and os.path.exists(PAYLOAD_FILE):
        with open(PAYLOAD_FILE) as f:
            payload = json.load(f)
    else:
        payload = DEFAULT_PAYLOAD
    
    if METHOD == "GET":
        payload = None
    
    # Run test
    tester = LoadTester(
        TARGET_URL,
        METHOD,
        CONCURRENCY,
        DURATION_SECS,
        DEFAULT_TIMEOUT,
        payload,
        TARGET_RPS,
    )
    await tester.run()


if __name__ == "__main__":
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )
    
    asyncio.run(main())
