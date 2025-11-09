"""
ASTRA Error Chaos Testing
Created: October 25, 2025

Generates controlled exceptions and verifies logging
for ASTRA's error handling system.
"""
import requests
import random
import time
from typing import Optional

BASE = "http://127.0.0.1:8080"

def bang(path: str) -> None:
    """Send a request and handle/display the response
    
    Args:
        path: API endpoint path to test
    """
    try:
        r = requests.get(
            f"{BASE}{path}",
            headers={
                "x-request-id": f"chaos-{random.randint(1,1000000)}"
            }
        )
        print(f"{path} {r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"Request failed: {e}")

def main() -> None:
    """Run chaos test sequence"""
    # 1) Verify healthy endpoint
    print("\n=== Testing healthy endpoint ===")
    bang("/health")
    
    # 2) Trigger an error via debug route
    print("\n=== Triggering error via /boom ===")
    bang("/boom")
    
    # 3) Verify system still healthy
    print("\n=== Verifying system still responsive ===")
    bang("/astra/status")
    
    print("\nCheck logs/astra.jsonl for:")
    print("- unhandled_error events")
    print("- err_id correlation")
    print("- req_id correlation")
    print("- Redacted sensitive headers")
    
if __name__ == "__main__":
    main()