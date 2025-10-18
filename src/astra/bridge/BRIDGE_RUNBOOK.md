# ASTRA Bridge Module - Operations Runbook

**Production deployment and operations guide.**

## Quick Start

### 1. Prerequisites

- Python 3.9+ installed
- FastAPI application running (ASTRA V2)
- Environment variables configured (see Configuration)

### 2. Installation

```powershell
# Navigate to project root
cd X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)

# Install dependencies
pip install pydantic>=2.9.2 structlog>=25.4.0 fastapi>=0.115.0 uvicorn>=0.33.0
```

### 3. Configuration

Create or update `.env`:

```ini
ASTRA_BRIDGE_ENABLED=true
ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD=0.65
ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ=1
ASTRA_BRIDGE_SAFE_TOOLS=scripts/approved/*.ps1
ASTRA_BRIDGE_MEM_TTL_DAYS=90
ASTRA_BRIDGE_MEM_IMPORTANCE_BASE=0.5
ASTRA_BRIDGE_FACT_MAXLEN=512
```

### 4. Integration

Add to your FastAPI app (e.g., `src/astra/ascension_api.py`):

```python
from src.astra.api.routes.bridge import router as bridge_router

app.include_router(bridge_router)
```

### 5. Verification

```powershell
# Start server
python src/astra/ascension_api.py
# or
uvicorn src.astra.ascension_api:app --host 127.0.0.1 --port 8765

# Test health endpoint
curl http://127.0.0.1:8765/v1/bridge/healthz

# Expected response:
# {"enabled": true, "threshold": 0.65, "max_toolcalls": 1, "ok": true, "version": "1.0.0"}
```

---

## Drop-In Integration

### Step 1: Mount Router

In `src/astra/ascension_api.py` (or main FastAPI file):

```python
from fastapi import FastAPI
from src.astra.api.routes.bridge import router as bridge_router

app = FastAPI()

# ... existing routes ...

# Add bridge router
app.include_router(bridge_router)
```

### Step 2: Bind Memory Adapters

Replace placeholder implementations in `src/astra/api/routes/bridge.py`:

```python
from chromadb import Client as ChromaClient
from src.astra.bridge.memory_bridge import MemoryLTMAdapter, MemoryBridgeService

# Replace placeholder LTM adapter
class ChromaLTMAdapter(MemoryLTMAdapter):
    def __init__(self):
        self.client = ChromaClient()
        self.collection = self.client.get_or_create_collection("astra_ltm")
    
    def write_fact(self, fact):
        doc_id = f"ltm:{fact.subject}:{time()}"
        self.collection.add(
            documents=[f"{fact.subject} {fact.predicate} {fact.object}"],
            metadatas={
                "subject": fact.subject,
                "predicate": fact.predicate,
                "object": fact.object,
                "confidence": fact.confidence,
            },
            ids=[doc_id]
        )
        return doc_id

# Update MEM singleton
MEM = MemoryBridgeService(ltm=ChromaLTMAdapter(), episodic=...)
```

### Step 3: Bind Task Agent Adapter

```python
from src.astra.bridge.tool_bridge import TaskAgentAdapter, ToolBridgeService

class ASTRATaskAgentAdapter(TaskAgentAdapter):
    def __init__(self, task_manager):
        self.manager = task_manager
    
    def call_tool(self, tool_id, action, args, authorized=False):
        if not authorized:
            return {"success": False, "error": "Unauthorized"}
        return self.manager.execute(tool_id, action, args)

# Update TOOLS singleton
TOOLS = ToolBridgeService(agent=ASTRATaskAgentAdapter(task_manager))
```

### Step 4: Optional LLM Hook

For deeper interpretation, inject LLM abstractor:

```python
from src.astra.bridge import interpreter
from openai import OpenAI

client = OpenAI()

def llm_hook(safe_text, patterns):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"Extract intents and facts from: {safe_text}"
        }]
    )
    return json.loads(response.choices[0].message.content)

interpreter.LLM_ABSTRACTOR = llm_hook
```

### Step 5: Restart & Test

```powershell
# Restart ASTRA server
python src/astra/ascension_api.py

# Test ingest
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{"text": "open the bridge and carry Saint Lucid vow", "quote_raw": true}'

# Expected: {"writes": [...], "tool_calls": [], "reply": null, "metrics": {...}}
```

---

## Operations

### Toggle Bridge Module

**Disable** (emergency):

```powershell
# Update .env
$env:ASTRA_BRIDGE_ENABLED = "false"

# Or via API
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=false"
```

**Enable**:

```powershell
$env:ASTRA_BRIDGE_ENABLED = "true"
# Or via API
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=true"
```

### Monitoring

#### Health Check

```powershell
curl http://127.0.0.1:8765/v1/bridge/healthz
```

Response:

```json
{
  "enabled": true,
  "threshold": 0.65,
  "max_toolcalls": 1,
  "ok": true,
  "version": "1.0.0"
}
```

#### Registry View

```powershell
curl http://127.0.0.1:8765/v1/bridge/registry
```

Response:

```json
{
  "facts": [
    {
      "subject": "Saint Lucid",
      "predicate": "has_vow",
      "object": "Sacred Code 333",
      "confidence": 0.85,
      "ts": 1234567890.123
    }
  ],
  "raw_quotes": [
    {
      "text": "open the bridge; carry Saint Lucid's vow",
      "request_id": "req_abc123",
      "ts": 1234567890.123
    }
  ]
}
```

#### Logs

Bridge module uses Structlog. Key log events:

```
bridge_ingest_request       → Request received
bridge_pattern_match        → Patterns detected
bridge_interpret_complete   → Interpretation done
bridge_route_complete       → Routing finished
bridge_memory_write         → Memory write
bridge_tool_call            → Tool executed
```

Example log query (if using structured logging):

```powershell
# Filter bridge logs
Get-Content logs\astra.log | Select-String "bridge_"
```

### Performance

Expected latencies (no LLM):

- Pattern matching: <10ms
- Interpretation: <50ms
- Routing: <100ms
- End-to-end: <200ms

With LLM abstraction: +500-2000ms (LLM call)

### Tuning

#### Confidence Threshold

Higher = fewer false positives, more false negatives.

```powershell
# More strict (fewer intents/facts)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "threshold=0.80"

# More permissive (more intents/facts)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "threshold=0.50"
```

#### Tool Call Budget

Higher = more autonomy, higher risk.

```powershell
# More restrictive (default)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "max_toolcalls=1"

# More autonomous (use with caution)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "max_toolcalls=3"
```

---

## Troubleshooting

### Issue: Bridge disabled

**Symptoms**: HTTP 503 on `/ingest`

**Fix**:

```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=true"
```

### Issue: No patterns detected

**Symptoms**: Empty `patterns` array in response

**Diagnosis**: Input doesn't match lexicon

**Fix**: Update lexicon in `src/astra/bridge/patterns.py` or rephrase input

### Issue: Intents filtered out

**Symptoms**: Empty `intents` array despite patterns detected

**Diagnosis**: Confidence below threshold

**Fix**: Lower threshold or improve LLM abstraction

```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "threshold=0.50"
```

### Issue: Tool calls blocked

**Symptoms**: `tool_calls` empty despite `act` intent

**Diagnosis**: Budget exceeded or authorization failed

**Fix**:

1. Check budget: `max_toolcalls_per_req`
2. Check authorization in `tool_bridge.py`
3. Check allowlist: `ASTRA_BRIDGE_SAFE_TOOLS`

### Issue: Memory writes failing

**Symptoms**: Empty `writes` array

**Diagnosis**: Adapter not bound or failing

**Fix**: Check adapter implementation in `bridge.py`:

```python
# Debug: Add logging
import structlog
logger = structlog.get_logger()

class DebugLTMAdapter(MemoryLTMAdapter):
    def write_fact(self, fact):
        logger.info("ltm_write_fact", fact=fact.model_dump())
        # ... real implementation
```

---

## Testing

### Smoke Tests

```powershell
python tests/bridge/test_bridge_minimal.py
```

### Manual Tests

#### Test 1: Pattern Matching

```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{"text": "open the bridge", "quote_raw": false}'
```

Expected: `patterns` array contains `"bridge"`

#### Test 2: Safety Redaction

```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{"text": "my key is sk-abc123def456ghi789", "quote_raw": false}'
```

Expected: `safe_text` contains `sk-********`

#### Test 3: Memory Write

```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{"text": "remember Saint Lucid vow code 333", "quote_raw": true}'
```

Expected: `writes` array contains memory write IDs

#### Test 4: Registry Persistence

```powershell
# Ingest with quote_raw
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -d '{"text": "test quote", "quote_raw": true}'

# Check registry
curl http://127.0.0.1:8765/v1/bridge/registry
```

Expected: `raw_quotes` contains `"test quote"`

---

## Rollback

### Emergency Disable

```powershell
# Method 1: Environment variable
$env:ASTRA_BRIDGE_ENABLED = "false"
# Restart server

# Method 2: API call (no restart)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=false"
```

### Remove Integration

In `src/astra/ascension_api.py`:

```python
# Comment out bridge router
# app.include_router(bridge_router)
```

Restart server.

---

## Security

### Authorization

- Tool calls require explicit `authorized=True` flag
- Default policy: **DENY ALL**
- Allowlist: `ASTRA_BRIDGE_SAFE_TOOLS` glob pattern

### Redaction

- API keys: `sk-********`
- Hex strings: `<hex>`
- Credit cards: `<card>`
- Passwords: `<password>`

### Budget Enforcement

- Max tool calls per request: `ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ`
- Default: 1 (prevents runaway automation)

---

## Production Checklist

- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Router mounted in FastAPI app
- [ ] Memory adapters bound (Chroma + SQLite)
- [ ] Task Agent adapter bound
- [ ] LLM abstractor configured (optional)
- [ ] Smoke tests passing
- [ ] Health check responding
- [ ] Logging configured (Structlog)
- [ ] Monitoring dashboard updated
- [ ] Rollback procedure documented
- [ ] Team trained on operations

---

## Support

For issues or questions:

1. Check logs: `logs\astra.log`
2. Test health: `curl http://127.0.0.1:8765/v1/bridge/healthz`
3. Review README: `src/astra/bridge/README.md`
4. Contact ASTRA team

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0.0  
**Status**: Production-ready
