# Debug raw response
import requests

API_BASE = "http://localhost:8080"

# Create conversation
conv_resp = requests.post(
    f"{API_BASE}/v1/conversations",
    json={"title": "Debug", "system_prompt": "You are ASTRA."}
)
conv_id = conv_resp.json()["conversation_id"]

# Send message
chat_resp = requests.post(
    f"{API_BASE}/v1/chat",
    json={
        "conversation_id": conv_id,
        "message": "Explain what you are in one sentence.",
        "stream": False
    }
)

result = chat_resp.json()
print("="*80)
print("RAW RESPONSE:")
print("="*80)
print(repr(result['message']))
print("\n" + "="*80)
print("VISIBLE RESPONSE:")
print("="*80)
print(result['message'])
