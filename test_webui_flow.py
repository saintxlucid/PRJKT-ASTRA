# Test exactly what the web UI does
import requests
import json

API_BASE = "http://localhost:8080"

# 1. Create conversation
print("Creating conversation...")
conv_resp = requests.post(
    f"{API_BASE}/v1/conversations",
    json={"title": "Web UI Test", "system_prompt": "You are ASTRA."}
)
print(f"Status: {conv_resp.status_code}")
print(f"Response: {conv_resp.json()}")
conv_id = conv_resp.json()["conversation_id"]

# 2. Send message (non-streaming first)
print(f"\nSending message to conversation {conv_id}...")
try:
    chat_resp = requests.post(
        f"{API_BASE}/v1/chat",
        json={
            "conversation_id": conv_id,
            "message": "Say hello in 3 words.",
            "stream": False
        }
    )
    print(f"Status: {chat_resp.status_code}")
    if chat_resp.status_code == 200:
        result = chat_resp.json()
        print(f"Success! Response: {result['message']}")
    else:
        print(f"Error: {chat_resp.text}")
except Exception as e:
    print(f"Exception: {e}")

# 3. Test streaming (what the UI actually uses)
print(f"\nTesting streaming with correct endpoint...")
try:
    chat_resp = requests.post(
        f"{API_BASE}/v1/chat/stream",
        json={
            "conversation_id": conv_id,
            "message": "Count to 3."
        },
        stream=True
    )
    print(f"Status: {chat_resp.status_code}")
    if chat_resp.status_code == 200:
        print("Stream chunks:")
        full_text = ""
        for line in chat_resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                print(f"  {decoded}")
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    chunk_data = decoded[6:]  # Remove "data: " prefix
                    full_text += chunk_data
        print(f"\nFull streamed response: {full_text}")
    else:
        print(f"Error: {chat_resp.text}")
except Exception as e:
    print(f"Exception: {e}")
