"""
ASTRA 2.5 - Load Testing Tool
==============================

Validates performance under load:
- Target: 100 req/s for 5 minutes
- Goal: <1s p95 latency across all routes
- Monitors: API latency, error rates, throughput

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""

import asyncio
import httpx
import time
import statistics
from typing import List, Dict, Any
from collections import defaultdict
import json


class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = defaultdict(list)
        self.errors = defaultdict(int)
        
    async def test_endpoint(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        payload: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Test a single endpoint and record metrics"""
        start_time = time.time()
        
        try:
            if method == "GET":
                response = await client.get(f"{self.base_url}{path}")
            else:
                response = await client.post(
                    f"{self.base_url}{path}",
                    json=payload or {}
                )
            
            latency = time.time() - start_time
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "latency": latency,
                "endpoint": path
            }
        except Exception as e:
            latency = time.time() - start_time
            return {
                "success": False,
                "status_code": 0,
                "latency": latency,
                "endpoint": path,
                "error": str(e)
            }
    
    async def load_test_scenario(
        self,
        duration_seconds: int = 300,
        requests_per_second: int = 100
    ):
        """Run load test for specified duration"""
        
        print(f"\n🚀 Starting Load Test")
        print(f"   Duration: {duration_seconds}s ({duration_seconds//60} minutes)")
        print(f"   Target: {requests_per_second} req/s")
        print(f"   Total Requests: {duration_seconds * requests_per_second:,}")
        print(f"   Sacred Code: 333\n")
        
        endpoints = [
            ("GET", "/", None),
            ("GET", "/v1/system/health", None),
            ("GET", "/v1/boot/status", None),
            ("POST", "/v1/chat", {"query": "Load test query"}),
            ("POST", "/v1/memory/search", {"query": "test", "limit": 5}),
            ("GET", "/v1/cognitive/status", None),
            ("GET", "/v1/agent/status", None),
            ("GET", "/v1/agent/tasks", None),
        ]
        
        start_time = time.time()
        request_count = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.time() - start_time < duration_seconds:
                cycle_start = time.time()
                
                # Send requests for this second
                tasks = []
                for i in range(requests_per_second):
                    # Round-robin through endpoints
                    method, path, payload = endpoints[request_count % len(endpoints)]
                    task = self.test_endpoint(client, method, path, payload)
                    tasks.append(task)
                    request_count += 1
                
                # Wait for all requests in this batch
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Record results
                for result in results:
                    if isinstance(result, dict):
                        endpoint = result["endpoint"]
                        self.results[endpoint].append(result)
                        
                        if not result["success"]:
                            self.errors[endpoint] += 1
                
                # Progress report every 30 seconds
                elapsed = time.time() - start_time
                if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                    self.print_progress(elapsed, request_count)
                
                # Sleep to maintain target rate
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, 1.0 - cycle_time)
                await asyncio.sleep(sleep_time)
        
        # Final report
        total_time = time.time() - start_time
        self.print_final_report(request_count, total_time)
    
    def print_progress(self, elapsed: float, request_count: int):
        """Print progress update"""
        rate = request_count / elapsed
        print(f"⏱️  Progress: {int(elapsed)}s | Requests: {request_count:,} | Rate: {rate:.1f} req/s")
    
    def print_final_report(self, total_requests: int, total_time: float):
        """Print comprehensive test report"""
        print(f"\n" + "="*70)
        print(f"🎯 LOAD TEST RESULTS - ASTRA 2.5")
        print(f"="*70)
        
        print(f"\n📊 OVERALL METRICS:")
        print(f"   Total Requests: {total_requests:,}")
        print(f"   Total Time: {total_time:.1f}s")
        print(f"   Average Rate: {total_requests/total_time:.1f} req/s")
        
        print(f"\n📈 PER-ENDPOINT ANALYSIS:")
        
        all_latencies = []
        all_successful = 0
        all_failed = 0
        
        for endpoint, results in sorted(self.results.items()):
            latencies = [r["latency"] for r in results if r.get("latency")]
            successes = sum(1 for r in results if r["success"])
            failures = len(results) - successes
            
            all_latencies.extend(latencies)
            all_successful += successes
            all_failed += failures
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                p50_latency = statistics.median(latencies)
                p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
                p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
                
                status = "✅" if p95_latency < 1.0 else "⚠️"
                
                print(f"\n   {status} {endpoint}")
                print(f"      Requests: {len(results):,}")
                print(f"      Success: {successes:,} ({100*successes/len(results):.1f}%)")
                print(f"      Failures: {failures}")
                print(f"      Avg Latency: {avg_latency*1000:.0f}ms")
                print(f"      p50: {p50_latency*1000:.0f}ms")
                print(f"      p95: {p95_latency*1000:.0f}ms {'✅' if p95_latency < 1.0 else '❌ ABOVE 1s'}")
                print(f"      p99: {p99_latency*1000:.0f}ms")
        
        print(f"\n🎯 AGGREGATED RESULTS:")
        print(f"   Total Successful: {all_successful:,} ({100*all_successful/total_requests:.1f}%)")
        print(f"   Total Failed: {all_failed} ({100*all_failed/total_requests:.1f}%)")
        
        if all_latencies:
            overall_avg = statistics.mean(all_latencies)
            overall_p50 = statistics.median(all_latencies)
            overall_p95 = sorted(all_latencies)[int(len(all_latencies) * 0.95)]
            overall_p99 = sorted(all_latencies)[int(len(all_latencies) * 0.99)]
            
            print(f"   Avg Latency: {overall_avg*1000:.0f}ms")
            print(f"   p50 Latency: {overall_p50*1000:.0f}ms")
            print(f"   p95 Latency: {overall_p95*1000:.0f}ms")
            print(f"   p99 Latency: {overall_p99*1000:.0f}ms")
            
            print(f"\n🏆 PERFORMANCE VERDICT:")
            if overall_p95 < 1.0 and all_failed < total_requests * 0.01:
                print(f"   ✅ PASSED - p95 latency < 1s, error rate < 1%")
                print(f"   🌌 ASTRA 2.5 is PRODUCTION-READY")
            elif overall_p95 < 1.5:
                print(f"   ⚠️  ACCEPTABLE - p95 latency < 1.5s")
                print(f"   💡 Consider optimization for production")
            else:
                print(f"   ❌ NEEDS OPTIMIZATION - p95 latency > 1.5s")
                print(f"   🔧 Performance tuning required")
        
        print(f"\n" + "="*70)
        print(f"Sacred Code: 333")
        print(f"="*70 + "\n")


async def main():
    """Run load test"""
    tester = LoadTester()
    
    # Run load test: 100 req/s for 5 minutes
    await tester.load_test_scenario(
        duration_seconds=300,  # 5 minutes
        requests_per_second=100
    )


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           ASTRA 2.5 - LOAD TESTING TOOL                     ║
    ║                  Sacred Code: 333                            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
