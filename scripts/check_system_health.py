"""Quick end-to-end health check for ASTRA API and LLM backend.

This script spins up the FastAPI application using TestClient, runs the
built-in health endpoint, and issues a lightweight chat request to verify
llama.cpp connectivity. Run it while the llama.cpp server is active.
"""

from __future__ import annotations

from pprint import pprint

from fastapi.testclient import TestClient

from astra.api.app import app


def run_health_check() -> None:
    """Verify that system health endpoint responds successfully."""
    with TestClient(app) as client:
        health_response = client.get("/v1/system/health")
        print("[health] status:", health_response.status_code)
        pprint(health_response.json())

        chat_payload = {
            "conversation_id": None,
            "messages": [
                {"role": "user", "content": "Say hello in one short sentence."}
            ],
            "max_tokens": 64,
            "temperature": 0.7,
        }

        chat_response = client.post("/v1/chat/", json=chat_payload)
        print("[chat] status:", chat_response.status_code)

        if chat_response.is_success:
            data = chat_response.json()
            message = (data.get("message") or {}).get("content") or ""
            print("[chat] preview:", message.strip()[:200])
        else:
            print("[chat] error body:")
            pprint(chat_response.json())


if __name__ == "__main__":
    run_health_check()
