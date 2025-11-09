#!/usr/bin/env python3
"""Test rate limiting functionality"""
import asyncio
import aiohttp
import time
from datetime import datetime

async def test_rate_limiting(url: str = "http://localhost:8001"):
    """Test rate limiting by sending rapid requests"""
    
    print(f"\n🔍 Rate Limiting Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Test /answer endpoint (limit: 50 req/s)
    print(f"\n📊 Testing /answer endpoint (limit: 50 req/s)")
    success_count = 0
    rate_limited_count = 0
    
    async with aiohttp.ClientSession() as session:
        # Send 60 requests as fast as possible
        tasks = []
        for i in range(60):
            tasks.append(send_request(session, f"{url}/answer", i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"  ❌ Error: {result}")
            elif result == 200:
                success_count += 1
            elif result == 429:
                rate_limited_count += 1
        
        print(f"  ✅ Success: {success_count}")
        print(f"  🚫 Rate Limited: {rate_limited_count}")
        print(f"  📈 Actual Rate: {success_count}/{success_count + rate_limited_count} = {success_count/(success_count + rate_limited_count)*100:.1f}%")
        
        # Test /live endpoint (limit: 1000 req/s) - should not be rate limited
        print(f"\n📊 Testing /live endpoint (limit: 1000 req/s)")
        success_count = 0
        rate_limited_count = 0
        
        tasks = []
        for i in range(60):
            tasks.append(send_request(session, f"{url}/live", i, method="GET"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"  ❌ Error: {result}")
            elif result == 200:
                success_count += 1
            elif result == 429:
                rate_limited_count += 1
        
        print(f"  ✅ Success: {success_count}")
        print(f"  🚫 Rate Limited: {rate_limited_count}")
        
        # Wait a bit and test recovery
        print(f"\n⏳ Waiting 2 seconds for token bucket refill...")
        await asyncio.sleep(2)
        
        print(f"\n📊 Testing /answer recovery after wait")
        success_count = 0
        rate_limited_count = 0
        
        tasks = []
        for i in range(60):
            tasks.append(send_request(session, f"{url}/answer", i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                pass
            elif result == 200:
                success_count += 1
            elif result == 429:
                rate_limited_count += 1
        
        print(f"  ✅ Success: {success_count}")
        print(f"  🚫 Rate Limited: {rate_limited_count}")
        print(f"  📈 Recovery Rate: {success_count/(success_count + rate_limited_count)*100:.1f}%")
    
    print("\n" + "=" * 70)
    print("✅ Rate Limiting Test Complete\n")

async def send_request(session, url, req_id, method="POST"):
    """Send a single request"""
    try:
        if method == "POST":
            async with session.post(
                url,
                json={"query": f"test {req_id}", "max_tokens": 100},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status
        else:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        return None

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
