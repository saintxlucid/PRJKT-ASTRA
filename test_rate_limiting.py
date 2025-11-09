#!/usr/bin/env python3
"""Rate limiting test for ASTRA Core"""
import asyncio
import aiohttp
import time
from collections import defaultdict

async def test_rate_limiting(url: str = "http://localhost:8001", duration: int = 10):
    """Test rate limiting on different endpoints"""
    endpoints = {
        "/answer": {"limit": 50, "concurrent": 20},
        "/live": {"limit": 1000, "concurrent": 100},
    }
    
    results = defaultdict(lambda: {"total": 0, "success": 0, "rate_limited": 0})
    
    async with aiohttp.ClientSession() as session:
        for endpoint, config in endpoints.items():
            print(f"\n🧪 Testing {endpoint} (limit: {config['limit']} req/s)")
            print(f"   Concurrent requests: {config['concurrent']}")
            print(f"   Duration: {duration}s")
            
            start_time = time.time()
            tasks = []
            
            # Create burst of requests
            while time.time() - start_time < duration:
                # Submit batch
                for _ in range(config["concurrent"]):
                    if endpoint == "/answer":
                        task = session.post(
                            f"{url}{endpoint}",
                            json={"question": "test"},
                            timeout=aiohttp.ClientTimeout(total=5)
                        )
                    else:
                        task = session.get(
                            f"{url}{endpoint}",
                            timeout=aiohttp.ClientTimeout(total=5)
                        )
                    tasks.append(task)
                
                # Collect results
                if tasks:
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    for response in responses:
                        results[endpoint]["total"] += 1
                        if isinstance(response, Exception):
                            pass
                        elif response.status == 429:
                            results[endpoint]["rate_limited"] += 1
                        elif response.status < 400:
                            results[endpoint]["success"] += 1
                        await response.text()  # Clear response
                    tasks = []
                
                await asyncio.sleep(0.1)
            
            elapsed = time.time() - start_time
            actual_rps = results[endpoint]["total"] / elapsed
            print(f"\n   Results:")
            print(f"    Total requests: {results[endpoint]['total']}")
            print(f"    Successful: {results[endpoint]['success']}")
            print(f"    Rate limited (429): {results[endpoint]['rate_limited']}")
            print(f"    Actual throughput: {actual_rps:.1f} req/s")
            print(f"    Limit exceeded by: {results[endpoint]['rate_limited'] / results[endpoint]['total'] * 100:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
