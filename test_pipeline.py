# Quick LLM pipeline test
import requests
import json

API_BASE = "http://localhost:8080"

# 1. Create conversation
conv_resp = requests.post(
    f"{API_BASE}/v1/conversations",
    json={"title": "Test", "system_prompt": "You are ASTRA."}
)
conv_id = conv_resp.json()["conversation_id"]
print(f"✓ Created conversation: {conv_id}")

# 2. Send message
chat_resp = requests.post(
    f"{API_BASE}/v1/chat",
    json={
        "conversation_id": conv_id,
        "message": "Hello! Please respond with just: I am working correctly.",
        "stream": False
    }
)

result = chat_resp.json()
print(f"\n✓ LLM Response:")
print(f"  Message: {result['message']}")
print(f"  Model: {result['model']}")
print(f"  Tokens: {result['usage']}")
print(f"\n✅ Full pipeline working!")
