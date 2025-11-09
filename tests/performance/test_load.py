"""
ASTRA OS - Phase Ω Performance Verification Script
===================================================
Load testing to validate < 1s p95 latency across all routes.

Test Scenarios:
- 100 req/s sustained for 5 minutes
- Mixed endpoint testing (chat, cognitive, agent, memory)
- Concurrent task execution
- Memory search under load

Target Metrics:
- p50 latency: < 200ms
- p95 latency: < 1000ms  ← CRITICAL
- p99 latency: < 2000ms
- Error rate: < 0.1%
- Throughput: 100 req/s

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""

import argparse
import asyncio
import json
import signal
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

import aiohttp

# Graceful shutdown flag
_shutdown = False


def _sigint_handler(*_args):
    """Handle SIGINT (Ctrl-C) gracefully."""
    global _shutdown
    _shutdown = True
    print("\n⚠️  Received SIGINT, stopping workers gracefully...")


signal.signal(signal.SIGINT, _sigint_handler)


@dataclass
class LatencyStats:
    """Track latency statistics for an endpoint."""

    endpoint: str
    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    successes: int = 0

    def add(self, latency: float, success: bool):
        """Add a measurement."""
        self.latencies.append(latency)
        if success:
            self.successes += 1
        else:
            self.errors += 1

    def get_stats(self) -> Dict:
        """Calculate percentiles and statistics with safe indexing."""
        if not self.latencies:
            return {"endpoint": self.endpoint, "error": "No data"}

        xs = sorted(self.latencies)
        n = len(xs)

        def p(q: float) -> float:
            """Nearest-rank percentile with safe clamping."""
            idx = max(0, min(n - 1, int(q * n)))
            if idx > 0:
                idx -= 1  # Adjust for 0-based indexing
            return xs[idx]

        return {
            "endpoint": self.endpoint,
            "total_requests": n,
            "successes": self.successes,
            "errors": self.errors,
            "error_rate": self.errors / n if n else 0.0,
            "min": xs[0],
            "max": xs[-1],
            "mean": statistics.mean(xs),
            "median": statistics.median(xs),
            "p50": p(0.50),
            "p75": p(0.75),
            "p90": p(0.90),
            "p95": p(0.95),
            "p99": p(0.99),
        }


class LoadTester:
    """Async load tester for ASTRA OS."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.stats: dict[str, LatencyStats] = defaultdict(lambda: LatencyStats(""))
        self.start_time = None
        self.end_time = None

    async def make_request(
        self, session: aiohttp.ClientSession, method: str, endpoint: str, payload: dict = None
    ) -> tuple[float, bool]:
        """Make a single HTTP request and measure latency."""
        url = f"{self.base_url}{endpoint}"
        start = time.perf_counter()

        try:
            if method.upper() == "GET":
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    await resp.read()
                    success = resp.status == 200
            else:  # POST
                async with session.post(
                    url, json=payload, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    await resp.read()
                    success = resp.status == 200

            latency = (time.perf_counter() - start) * 1000  # Convert to ms
            return latency, success

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            print(f"Error on {endpoint}: {e}")
            return latency, False

    async def test_endpoint(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        payload: dict = None,
        weight: float = 1.0,
    ):
        """Test a single endpoint (called repeatedly)."""
        latency, success = await self.make_request(session, method, endpoint, payload)
        self.stats[endpoint].endpoint = endpoint
        self.stats[endpoint].add(latency, success)

    async def test_chat_endpoint(self, session: aiohttp.ClientSession):
        """Test /v1/chat endpoint."""
        payload = {"messages": [{"role": "user", "content": "Hello, how are you?"}], "max_tokens": 100}
        await self.test_endpoint(session, "POST", "/v1/chat", payload)

    async def test_memory_search(self, session: aiohttp.ClientSession):
        """Test /v1/memory/search endpoint."""
        payload = {"query": "vector embeddings", "top_k": 5}
        await self.test_endpoint(session, "POST", "/v1/memory/search", payload)

    async def test_cognitive_status(self, session: aiohttp.ClientSession):
        """Test /v1/cognitive/status endpoint."""
        await self.test_endpoint(session, "GET", "/v1/cognitive/status")

    async def test_agent_status(self, session: aiohttp.ClientSession):
        """Test /v1/agent/status endpoint."""
        await self.test_endpoint(session, "GET", "/v1/agent/status")

    async def test_system_health(self, session: aiohttp.ClientSession):
        """Test /v1/system/health endpoint."""
        await self.test_endpoint(session, "GET", "/v1/system/health")

    async def test_cognitive_reasoning(self, session: aiohttp.ClientSession):
        """Test /v1/cognitive/reasoning endpoint."""
        payload = {
            "mode": "analytical",
            "input": "What is the efficiency of quicksort?",
            "context": {},
        }
        await self.test_endpoint(session, "POST", "/v1/cognitive/reasoning", payload)

    async def test_agent_create_and_poll(self, session: aiohttp.ClientSession):
        """Test agent task lifecycle: create + poll."""
        # Create task
        create_payload = {
            "goal": "ping example.org",
            "timeout_s": 12,
            "max_iterations": 6,
        }
        create_latency, create_ok = await self.make_request(
            session, "POST", "/v1/agent/task", create_payload
        )
        self.stats["/v1/agent/task"].endpoint = "/v1/agent/task"
        self.stats["/v1/agent/task"].add(create_latency, create_ok)

        # Poll status if create succeeded
        if create_ok:
            poll_latency, poll_ok = await self.make_request(
                session, "GET", "/v1/agent/status", None
            )
            self.stats["/v1/agent/status"].endpoint = "/v1/agent/status"
            self.stats["/v1/agent/status"].add(poll_latency, poll_ok)

    async def worker(
        self, session: aiohttp.ClientSession, duration_seconds: int, requests_per_second: int
    ):
        """Worker coroutine that generates load."""
        interval = 1.0 / requests_per_second
        end_time = time.time() + duration_seconds

        # Test distribution (weights sum to 1.0)
        test_weights = {
            self.test_chat_endpoint: 0.28,
            self.test_memory_search: 0.25,
            self.test_cognitive_status: 0.14,
            self.test_agent_status: 0.08,
            self.test_system_health: 0.10,
            self.test_cognitive_reasoning: 0.10,
            self.test_agent_create_and_poll: 0.05,  # Realistic agent lifecycle
        }

        # Build weighted list of tests
        tests = []
        for test_func, weight in test_weights.items():
            count = int(weight * 100)  # 100 total
            tests.extend([test_func] * count)

        request_count = 0
        while time.time() < end_time and not _shutdown:
            start = time.time()

            # Pick a test function based on weights
            test_func = tests[request_count % len(tests)]
            await test_func(session)

            request_count += 1

            # Sleep to maintain target rate
            elapsed = time.time() - start
            sleep_time = max(0, interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def run_load_test(
        self,
        duration_seconds: int = 300,  # 5 minutes
        requests_per_second: int = 100,
        num_workers: int = 10,
        warmup_s: int = 15,
        auth_token: str = None,
    ):
        """Run the load test with multiple workers."""
        print("🚀 Starting load test...")
        print(f"   Duration: {duration_seconds}s (+ {warmup_s}s warmup)")
        print(f"   Target: {requests_per_second} req/s")
        print(f"   Workers: {num_workers}")
        print(f"   Total requests: ~{duration_seconds * requests_per_second}")
        print()

        self.start_time = time.time()

        # Create session with connection pooling and persistent headers
        connector = aiohttp.TCPConnector(
            limit=4 * requests_per_second, limit_per_host=2 * requests_per_second
        )
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            # Warmup phase (don't record stats)
            print(f"🔥 Warming up for {warmup_s}s...")
            warmup_end = time.time() + warmup_s
            while time.time() < warmup_end and not _shutdown:
                await self.test_cognitive_status(session)
                await self.test_system_health(session)
                await asyncio.sleep(0.01)

            # Reset stats after warmup
            self.stats.clear()
            print("✅ Warmup complete, starting measured load test...\n")

            # Accurate RPS distribution with remainder handling
            base_rps = requests_per_second
            quotient, remainder = divmod(base_rps, num_workers)
            per_worker_rps = [
                quotient + (1 if i < remainder else 0) for i in range(num_workers)
            ]

            # Create workers with accurate RPS allocation
            tasks = [
                self.worker(session, duration_seconds, rps)
                for rps in per_worker_rps
                if rps > 0
            ]

            # Run workers concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        self.end_time = time.time()

    def print_results(self, write_json: str = None):
        """Print comprehensive test results and optionally export JSON."""
        if not self.stats:
            print("❌ No test results available")
            return False

        total_duration = self.end_time - self.start_time
        total_requests = sum(s.successes + s.errors for s in self.stats.values())
        total_errors = sum(s.errors for s in self.stats.values())

        print("\n" + "=" * 80)
        print("📊 LOAD TEST RESULTS")
        print("=" * 80)
        print(f"Duration: {total_duration:.1f}s")
        print(f"Total Requests: {total_requests}")
        print(f"Total Errors: {total_errors}")
        print(f"Error Rate: {(total_errors / total_requests * 100):.2f}%")
        print(f"Throughput: {(total_requests / total_duration):.1f} req/s")
        print()

        # Per-endpoint statistics
        print("📈 PER-ENDPOINT STATISTICS")
        print("-" * 80)

        all_pass = True
        for endpoint, stats in sorted(self.stats.items()):
            stats_dict = stats.get_stats()

            # Check if meets SLA (p95 < 1000ms)
            p95_pass = stats_dict["p95"] < 1000
            p95_status = "✅" if p95_pass else "❌"
            if not p95_pass:
                all_pass = False

            print(f"\n{endpoint}")
            print(f"  Requests:   {stats_dict['total_requests']}")
            print(f"  Successes:  {stats_dict['successes']}")
            print(f"  Errors:     {stats_dict['errors']} ({stats_dict['error_rate']:.2%})")
            print("  Latency:")
            print(f"    Min:      {stats_dict['min']:.1f}ms")
            print(f"    Mean:     {stats_dict['mean']:.1f}ms")
            print(f"    Median:   {stats_dict['median']:.1f}ms")
            print(f"    p95:      {stats_dict['p95']:.1f}ms {p95_status}")
            print(f"    p99:      {stats_dict['p99']:.1f}ms")
            print(f"    Max:      {stats_dict['max']:.1f}ms")

        print("\n" + "=" * 80)

        # Overall verdict
        error_rate = (total_errors / total_requests) if total_requests else 0.0
        sla_pass = all_pass and error_rate < 0.001

        if sla_pass:
            print("✅ PASS: System meets performance requirements!")
            print("   - All endpoints p95 < 1000ms")
            print("   - Error rate < 0.1%")
        else:
            print("❌ FAIL: System does not meet performance requirements")
            if not all_pass:
                print("   - Some endpoints exceed 1000ms p95 latency")
            if error_rate >= 0.001:
                print(f"   - Error rate {error_rate:.2%} exceeds 0.1%")

        print("=" * 80)

        # Export JSON report for CI/Grafana
        if write_json:
            report = {
                "duration_s": total_duration,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": error_rate,
                "throughput_rps": (total_requests / total_duration) if total_duration else 0.0,
                "endpoints": {ep: s.get_stats() for ep, s in self.stats.items()},
                "sla": {"p95_ms_lt": 1000, "error_rate_lt": 0.001},
                "pass": sla_pass,
            }
            try:
                with open(write_json, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)
                print(f"\n📄 Results exported to: {write_json}")
            except Exception as e:
                print(f"\n⚠️  Failed to write JSON report: {e}")

        return sla_pass


async def quick_smoke_test(base_url: str = "http://localhost:8000"):
    """Quick smoke test before full load test."""
    print("🔍 Running smoke test...")

    async with aiohttp.ClientSession() as session:
        tests = [
            ("GET", "/v1/system/health", None),
            ("GET", "/v1/boot/status", None),
            ("GET", "/v1/cognitive/status", None),
            ("GET", "/v1/agent/status", None),
        ]

        for method, endpoint, payload in tests:
            url = f"{base_url}{endpoint}"
            try:
                if method == "GET":
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            print(f"   ✅ {endpoint}")
                        else:
                            print(f"   ❌ {endpoint} (status {resp.status})")
                            return False
            except Exception as e:
                print(f"   ❌ {endpoint} ({e})")
                return False

    print("   ✅ Smoke test passed!\n")
    return True


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ASTRA OS Load Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--duration", type=int, default=300, help="Test duration (seconds)")
    parser.add_argument("--rps", type=int, default=100, help="Requests per second")
    parser.add_argument("--workers", type=int, default=10, help="Number of workers")
    parser.add_argument("--warmup", type=int, default=15, help="Warmup seconds (excluded from stats)")
    parser.add_argument("--auth", default=None, help="Bearer token for protected routes")
    parser.add_argument("--json-out", default=None, help="Write results JSON to file")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke test")

    args = parser.parse_args()

    # Run smoke test first
    if not args.skip_smoke:
        smoke_passed = await quick_smoke_test(args.url)
        if not smoke_passed:
            print("\n❌ Smoke test failed. Fix issues before running load test.")
            sys.exit(1)

    # Run load test
    tester = LoadTester(base_url=args.url)
    await tester.run_load_test(
        duration_seconds=args.duration,
        requests_per_second=args.rps,
        num_workers=args.workers,
        warmup_s=args.warmup,
        auth_token=args.auth,
    )

    # Print results and export JSON
    passed = tester.print_results(write_json=args.json_out)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
