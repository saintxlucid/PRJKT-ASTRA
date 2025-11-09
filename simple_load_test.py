#!/usr/bin/env python3
"""Simple load test for ASTRA Core"""
import asyncio
import aiohttp
import time
import json
from statistics import mean, median
from collections import defaultdict

async def test_endpoint(session, url, method="GET", json_data=None):
    """Test a single endpoint"""
    start = time.time()
    try:
        if method == "GET":
            async with session.get(url) as resp:
                status = resp.status
                await resp.text()
        else:
            async with session.post(url, json=json_data) as resp:
                status = resp.status
                await resp.text()
        
        latency = (time.time() - start) * 1000  # ms
        return {"success": True, "status": status, "latency": latency}
    except Exception as e:
        latency = (time.time() - start) * 1000
        return {"success": False, "error": str(e), "latency": latency}

async def run_load_test(base_url, duration_seconds=30, concurrent_users=10):
    """Run load test"""
    print(f"\n🚀 Starting Load Test")
    print(f"Target: {base_url}")
    print(f"Duration: {duration_seconds}s")
    print(f"Concurrent Users: {concurrent_users}")
    print("=" * 60)
    
    metrics = defaultdict(lambda: {"requests": 0, "failures": 0, "latencies": []})
    
    async def user_session():
        """Simulate one user"""
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                # Test health endpoint
                result = await test_endpoint(session, f"{base_url}/live")
                metrics["GET /live"]["requests"] += 1
                if result["success"]:
                    metrics["GET /live"]["latencies"].append(result["latency"])
                else:
                    metrics["GET /live"]["failures"] += 1
                
                await asyncio.sleep(0.5)
                
                # Test answer endpoint
                payload = {
                    "query": "What is ASTRA?",
                    "max_tokens": 100,
                    "temperature": 0.7
                }
                result = await test_endpoint(session, f"{base_url}/answer", method="POST", json_data=payload)
                metrics["POST /answer"]["requests"] += 1
                if result["success"]:
                    metrics["POST /answer"]["latencies"].append(result["latency"])
                else:
                    metrics["POST /answer"]["failures"] += 1
                
                await asyncio.sleep(0.5)
                
                # Test stream endpoint
                payload["stream"] = True
                result = await test_endpoint(session, f"{base_url}/answer/stream", method="POST", json_data=payload)
                metrics["POST /answer/stream"]["requests"] += 1
                if result["success"]:
                    metrics["POST /answer/stream"]["latencies"].append(result["latency"])
                else:
                    metrics["POST /answer/stream"]["failures"] += 1
                
                await asyncio.sleep(1)
    
    # Run concurrent users
    start_time = time.time()
    await asyncio.gather(*[user_session() for _ in range(concurrent_users)])
    total_duration = time.time() - start_time
    
    # Print results
    print(f"\n📊 Load Test Results ({total_duration:.1f}s)")
    print("=" * 60)
    
    total_requests = 0
    total_failures = 0
    
    for endpoint, data in metrics.items():
        requests = data["requests"]
        failures = data["failures"]
        latencies = data["latencies"]
        
        total_requests += requests
        total_failures += failures
        
        if latencies:
            avg_latency = mean(latencies)
            med_latency = median(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
            max_latency = max(latencies)
            min_latency = min(latencies)
            success_rate = ((requests - failures) / requests * 100) if requests > 0 else 0
            
            print(f"\n{endpoint}")
            print(f"  Requests: {requests}")
            print(f"  Failures: {failures}")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Latency:")
            print(f"    Min: {min_latency:.0f}ms")
            print(f"    Avg: {avg_latency:.0f}ms")
            print(f"    Med: {med_latency:.0f}ms")
            print(f"    P95: {p95_latency:.0f}ms")
            print(f"    Max: {max_latency:.0f}ms")
            print(f"  Throughput: {requests/total_duration:.1f} req/s")
    
    # Overall stats
    print(f"\n📈 Overall Statistics")
    print("=" * 60)
    print(f"Total Requests: {total_requests}")
    print(f"Total Failures: {total_failures}")
    success_rate = ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0
    print(f"Overall Success Rate: {success_rate:.1f}%")
    print(f"Overall Throughput: {total_requests/total_duration:.1f} req/s")
    
    # SLO checks
    print(f"\n✅ SLO Checks")
    print("=" * 60)
    
    if success_rate >= 99.5:
        print("✅ Success Rate: PASS (>= 99.5%)")
    else:
        print(f"❌ Success Rate: FAIL ({success_rate:.1f}% < 99.5%)")
    
    # Check P95 latency for answer endpoint
    answer_latencies = metrics["POST /answer"]["latencies"]
    if answer_latencies:
        p95 = sorted(answer_latencies)[int(len(answer_latencies) * 0.95)]
        if p95 <= 2500:
            print(f"✅ Answer P95 Latency: PASS ({p95:.0f}ms <= 2500ms)")
        else:
            print(f"❌ Answer P95 Latency: FAIL ({p95:.0f}ms > 2500ms)")

if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    users = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    asyncio.run(run_load_test(base_url, duration, users))
