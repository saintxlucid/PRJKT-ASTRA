"""
Tests for ASTRA Model Server Reference
"""
import os
import pytest
from fastapi.testclient import TestClient
from tools.model_server import app, MODE

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert "mode" in j
    assert j["ok"] is True

def test_generate_empty_prompt():
    r = client.post("/generate", json={"prompt": ""})
    assert r.status_code == 400

def test_adapter_lifecycle():
    aid = "test-adapter-123"
    r = client.post("/adapter/load", json={"adapter_id": aid})
    assert r.status_code == 200
    j = r.json()
    assert j.get("adapter_id") == aid
    assert j.get("status") == "loaded"
    
    r2 = client.get("/adapter/status", params={"adapter_id": aid})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2.get("adapter_id") == aid
    assert "loaded_at" in j2
    
def test_generate_with_adapter():
    aid = "test-adapter-gen"
    # Load adapter first
    r = client.post("/adapter/load", json={"adapter_id": aid})
    assert r.status_code == 200
    
    # Generate with adapter
    r2 = client.post("/generate", json={
        "prompt": "Test prompt",
        "adapter_ids": [aid],
        "max_tokens": 10
    })
    
    # CLI mode without LLAMA_CLI_CMD will fail, transformers should work
    if MODE == "transformers":
        assert r2.status_code == 200
        j = r2.json()
        assert "request_id" in j
        assert "result" in j
        assert "provenance" in j
        assert aid in j["provenance"]["adapter_ids"]
    else:
        # CLI mode without command should fail gracefully
        assert r2.status_code in (500, 200)  # 500 if no CLI cmd, 200 if cmd exists

def test_adapter_status_list():
    # Load a couple adapters
    aids = ["test-list-1", "test-list-2"]
    for aid in aids:
        r = client.post("/adapter/load", json={"adapter_id": aid})
        assert r.status_code == 200
    
    # Get list
    r = client.get("/adapter/status")
    assert r.status_code == 200
    j = r.json()
    assert "adapters" in j
    assert isinstance(j["adapters"], list)
    for aid in aids:
        assert aid in j["adapters"]