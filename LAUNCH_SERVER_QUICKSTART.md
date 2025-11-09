# 🚀 ASTRA Server Quick Start Guide

**File:** `launch_server.py`  
**Purpose:** Week-2 integrated FastAPI server with boot orchestration  
**Status:** ✅ Operational

---

## ⚡ Quick Start (30 seconds)

```bash
# 1. Start server
python launch_server.py

# 2. Test health endpoint
curl http://localhost:8000/health

# 3. View API docs
http://localhost:8000/docs
```

---

## 📡 API Endpoints

### Core Operations

| Method | Endpoint | Purpose | Event Logged |
|--------|----------|---------|--------------|
| GET | `/health` | System health + boot status | `health_check` |
| GET | `/docs` | Interactive API documentation | - |
| GET | `/metrics` | Prometheus metrics | - |

### AI Operations

| Method | Endpoint | Purpose | Event Logged |
|--------|----------|---------|--------------|
| POST | `/chat` | Chat with ASTRA (policy enforced) | `chat_requested`, `chat_completed` |
| POST | `/tool/execute` | Execute tool (sandboxed) | `tool_executed` |
| POST | `/memory/search` | Search memory store | `memory_searched` |

### Audit Trail

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/events?limit=N` | View last N events |
| GET | `/events/replay?event_type=X` | Filter events by type |

---

## 💬 Example: Chat Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What can you do?",
    "temperature": 0.7,
    "max_tokens": 512
  }'
```

**Response:**
```json
{
  "response": "[PLACEHOLDER] Response to: What can you do?",
  "event_id": "abc123-def456-789"
}
```

**Events Logged:**
1. `chat_requested` - Input message logged
2. `chat_completed` - Response logged (or `chat_rejected` if policy denied)

---

## 🔧 Example: Tool Execution

```bash
curl -X POST http://localhost:8000/tool/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "read_file",
    "arguments": {"path": "README.md"}
  }'
```

**Response:**
```json
{
  "status": 0,
  "output": "File contents here...",
  "error": null,
  "event_id": "xyz789-abc123-456"
}
```

**Policy Check:** If tool denied by policy → HTTP 403 + `tool_rejected` event

---

## 📊 View Event Log

```bash
# Last 10 events
curl http://localhost:8000/events?limit=10

# All chat events
curl http://localhost:8000/events/replay?event_type=chat_completed

# All tool executions
curl http://localhost:8000/events/replay?event_type=tool_executed
```

**Event Structure:**
```json
{
  "id": "2cea49de-...",
  "ts": "2025-11-01T23:10:10.123456+00:00",
  "typ": "session_started",
  "payload": {"cwd": "...", "python_version": "3.13.3"},
  "identity": {"warmth": 0.7, "autonomy": "low"},
  "prev_hash": "cf4c3ae1...",
  "hash": "9745de08..."
}
```

**Hash Chain:** Each event links to previous via SHA256 (tamper-evident)

---

## 🏥 Health Check Response

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "operational",
  "event_store_count": 37,
  "policy_count": 0,
  "executor_type": "LocalExecutor"
}
```

**Fields:**
- `status`: "operational" or "error"
- `event_store_count`: Total events logged (audit trail size)
- `policy_count`: Number of loaded identity policies
- `executor_type`: "LocalExecutor" (dev) or "DockerSandboxExecutor" (prod)

---

## 📈 Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

```json
{
  "event_store_count": 37,
  "policy_count": 0,
  "executor_type": "LocalExecutor",
  "boot_event_id": "2cea49de-..."
}
```

---

## 🔒 Security Features

### 1. Policy Enforcement

Every tool/action checked before execution:

```python
# Automatic policy check
approved, errors = plan_verifier.check(
    {"action": "read_file", "path": "secrets.txt"},
    {}
)

# If denied → HTTP 403 + event logged
```

### 2. Event Logging (Tamper-Evident)

All operations logged with SHA256 hash chain:

```
Event 1: hash = SHA256(id + timestamp + payload)
Event 2: hash = SHA256(id + timestamp + payload + Event1.hash)
Event 3: hash = SHA256(id + timestamp + payload + Event2.hash)
...
```

**Tampering Detection:** If any event modified, hash chain breaks

### 3. Sandboxed Execution

Tools run in isolated environment:

- **LocalExecutor** (dev): Allowlist-only tools
- **DockerSandboxExecutor** (prod): Full containerization

---

## 🐛 Troubleshooting

### Server won't start

```bash
# Check Python version (requires 3.13+)
python --version

# Check dependencies
pip install -r requirements.txt

# Check event store
ls -la data/eventlog.sqlite
```

### HTTP 503 "Server not ready"

Boot sequence failed. Check logs for:

- ⚠️ GPG decryption errors
- ⚠️ Model verification failures
- ⚠️ Event store connection issues

### HTTP 403 "Policy denied"

Operation blocked by identity policy:

1. Check policy rules: `config/identity_policies.yaml`
2. View denial reason in event log: `/events/replay?event_type=tool_rejected`
3. Update policy or request consent

---

## 🧪 Testing

### Manual Test Suite

```bash
# 1. Start server
python launch_server.py

# 2. Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat -d '{"message":"test"}'
curl http://localhost:8000/events?limit=5

# 3. Check event log
python -c "
import sys; sys.path.insert(0, 'src')
from gateways.event_store_sqlite import SQLiteEventStore
store = SQLiteEventStore('data/eventlog.sqlite')
print(f'Total events: {store.count()}')
for e in list(store.replay())[-5:]:
    print(f'{e.ts[:19]} | {e.typ}')
"
```

### Automated Test Script

```bash
# Run test_server.py (if exists)
python test_server.py
```

---

## 📝 Development Tips

### Adding New Endpoints

```python
@app.post("/my_endpoint")
async def my_endpoint(req: MyRequest):
    # 1. Check boot complete
    if not _deps:
        raise HTTPException(status_code=503, detail="Server not ready")
    
    # 2. Log request
    event_id = _deps.event_store.append(
        "my_event_type",
        {"input": req.data},
        _deps.identity_snapshot
    )
    
    # 3. Check policy (optional)
    approved, errors = _deps.plan_verifier.check(
        {"action": "my_action"},
        {}
    )
    if not approved:
        raise HTTPException(status_code=403, detail=errors)
    
    # 4. Execute + return
    result = do_work(req)
    return MyResponse(result=result, event_id=event_id)
```

### Accessing Boot Dependencies

```python
# Global dependencies injected during boot
_deps: BootDependencies

# Available components:
_deps.event_store       # SQLiteEventStore
_deps.plan_verifier     # PlanVerifier
_deps.action_executor   # LocalExecutor or DockerSandboxExecutor
_deps.identity_snapshot # dict[str, Any]
_deps.boot_event_id     # str
```

---

## 🎯 Next Steps

### Week-2 Days 9-10

1. **Memory Integration**
   - Create `src/gateways/chroma_memory_gateway.py`
   - Implement `MemoryGateway` protocol
   - Wire into `/memory/search` endpoint

2. **Policy Rules**
   - Create `config/identity_policies.yaml`
   - Add rules: no_system_commands, require_consent_for_files
   - Test policy enforcement

3. **Prompt Guard**
   - Wire `prompt_guard` into `/chat` endpoint
   - Add 3-layer defense: heuristic + LLM judge + consent

### Week-2 Days 11-12

4. **CI/CD Workflow**
   - Create `.github/workflows/ci.yml`
   - Add: pytest, coverage, bandit scans
   - Automate validation

5. **Production Hardening**
   - Enable GPG secrets decryption
   - Switch to DockerSandboxExecutor
   - Add rate limiting + authentication

---

## 📚 References

- **Full Documentation:** [✅_WEEK_2_DAYS_7-8_SERVICE_INTEGRATION_COMPLETE.md](./✅_WEEK_2_DAYS_7-8_SERVICE_INTEGRATION_COMPLETE.md)
- **Boot Module:** [src/boot.py](./src/boot.py)
- **Week-2 Plan:** [WEEK_2_ARCHITECTURE_REFACTOR.md](./WEEK_2_ARCHITECTURE_REFACTOR.md)
- **API Docs (Interactive):** http://localhost:8000/docs (when server running)

---

**Status:** ✅ Operational  
**Version:** 0.2.0  
**Last Updated:** 2025-11-02

*ASTRA Core Team - Week-2 Architecture Refactor*
