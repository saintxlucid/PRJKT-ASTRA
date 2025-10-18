# LLM Integration Repair Log — 2025-10-08

## Summary

- **Symptoms:** ASTRA API failed to respond to chat requests because the backend provider targeted `http://localhost:8001/v1/completion`, which llama.cpp does not expose. Uvicorn also collided with existing port bindings when zombie processes were left running.
- **Fixes Applied:**
  - Updated the default LLM base URL to `http://localhost:8001`, matching llama.cpp's `/completion` endpoint.
  - Regenerated the environment so new settings propagate without stale overrides.
  - Relaunched the llama.cpp server and ASTRA API in dedicated processes to eliminate port contention.
- **Validation:**
  - `GET /v1/system/health` now returns `{"status":"healthy","llm_healthy":true}`.
  - `POST /v1/chat/` succeeds after creating a conversation and returns model output with token usage metrics.

## Commands Executed

```powershell
# Launch llama.cpp server
Start-Process -FilePath "x:\PROJECT_ASTRA\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe" `
    -ArgumentList @('-m','x:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf','--host','127.0.0.1','--port','8001','--ctx-size','4096','--n-gpu-layers','0')

# Launch ASTRA API
Start-Process -FilePath "x:\PROJECT_ASTRA\.venv\Scripts\python.exe" `
    -ArgumentList 'run_server.py' -WorkingDirectory 'x:\PROJECT_ASTRA'

# Health check
powershell -NoProfile -Command "Invoke-WebRequest -Uri http://localhost:8080/v1/system/health -UseBasicParsing"

# Conversation + chat smoke test
.\.venv\Scripts\python.exe -c "import httpx, json; client = httpx.Client(timeout=120); conv = client.post('http://localhost:8080/v1/conversations/', json={'title': 'Validation Run'}); conv.raise_for_status(); conv_id = conv.json()['conversation_id']; chat_body={'conversation_id': conv_id, 'message': 'Hello ASTRA, give me a short greeting.', 'max_tokens': 128}; resp = client.post('http://localhost:8080/v1/chat/', json=chat_body); print(resp.status_code); print(json.dumps(resp.json(), indent=2))"
```

## Follow-up Suggestions

- If you switch llama.cpp into OpenAI-compatible `--api` mode, update `settings.llm.base_url` to include `/v1` and adjust the provider to send OpenAI-format payloads.
- Consider trimming Harmony template artifacts from final responses before storing them in conversation history.
