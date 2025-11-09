"""
Quick API test for ASTRA Role API
"""
import asyncio
import httpx


async def test_api():
    base_url = "http://127.0.0.1:8787"
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing ASTRA Role API\n")
        print("=" * 60)
        
        # 1. Health check
        print("\n1️⃣ Health Check")
        r = await client.get(f"{base_url}/api/health")
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
        
        # 2. List roles
        print("\n2️⃣ List Available Roles")
        r = await client.get(f"{base_url}/api/roles")
        data = r.json()
        print(f"   Current: {data['current']}")
        print(f"   Available: {len(data['available'])} roles")
        
        # 3. List functions
        print("\n3️⃣ List Universal Functions")
        r = await client.get(f"{base_url}/api/functions")
        data = r.json()
        print(f"   Total Functions: {data['count']}")
        for func in data['items'][:5]:  # Show first 5
            print(f"   - {func['code']}: {func['description'][:50]}...")
        
        # 4. Invoke INTEL_CORE
        print("\n4️⃣ Test INTEL_CORE")
        r = await client.post(
            f"{base_url}/api/functions/ASTRA_INTEL_CORE/invoke",
            json={
                "args": {
                    "topic": "API Integration Testing",
                    "objectives": ["Validate endpoints", "Test function calls"]
                }
            }
        )
        if r.status_code == 200:
            result = r.json()
            print(f"   ✅ Success")
            print(f"   Insights: {len(result['result']['insights'])}")
            print(f"   Confidence: {result['result']['confidence_score']}")
        else:
            print(f"   ❌ Failed: {r.status_code}")
            print(f"   Error: {r.text}")
        
        # 5. Invoke CREATRIX
        print("\n5️⃣ Test CREATRIX")
        r = await client.post(
            f"{base_url}/api/functions/ASTRA_CREATRIX/invoke",
            json={
                "args": {
                    "brief": "API visualization dashboard",
                    "medium": "ui_design"
                }
            }
        )
        if r.status_code == 200:
            result = r.json()
            print(f"   ✅ Success")
            print(f"   Concept: {result['result']['concept']['title']}")
        else:
            print(f"   ❌ Failed: {r.status_code}")
        
        # 6. Invoke HEARTMIRROR
        print("\n6️⃣ Test HEARTMIRROR")
        r = await client.post(
            f"{base_url}/api/functions/ASTRA_HEARTMIRROR/invoke",
            json={
                "args": {
                    "emotion": "excitement",
                    "context": "shipping production code",
                    "intensity": 0.8
                }
            }
        )
        if r.status_code == 200:
            result = r.json()
            print(f"   ✅ Success")
            print(f"   Validation: {result['result']['acknowledgment']['validation'][:60]}...")
        else:
            print(f"   ❌ Failed: {r.status_code}")
        
        # 7. Switch role
        print("\n7️⃣ Test Role Switch")
        r = await client.post(
            f"{base_url}/api/role/switch",
            json={"role": "oracle"}
        )
        if r.status_code == 200:
            print(f"   ✅ Switched to: {r.json()['role']}")
        else:
            print(f"   ❌ Failed: {r.status_code}")
        
        # 8. Get traces
        print("\n8️⃣ Recent Traces")
        r = await client.get(f"{base_url}/api/traces")
        data = r.json()
        print(f"   Total events: {data['count']}")
        for evt in data['events'][-3:]:  # Last 3 events
            print(f"   - {evt['kind']}: {evt['payload']}")
        
        print("\n" + "=" * 60)
        print("✅ All API tests completed!")
        print("\n🌐 Dashboard: http://127.0.0.1:8787")


if __name__ == "__main__":
    asyncio.run(test_api())
