#!/usr/bin/env python3
"""Quick test script for unified health endpoints."""

import requests
import json
import time

# Wait for server to be ready
print("⏳ Waiting 2 seconds for server...")
time.sleep(2)

endpoints = [
    "http://127.0.0.1:8770/v1/system/health/unified",
    "http://127.0.0.1:8770/api/system/health/unified"
]

for url in endpoints:
    print(f"\n🔍 Testing: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
