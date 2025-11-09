# ASTRA Bridge Module - Quick Reference

**Fast lookup for common operations**

---

## Installation (1 Minute)

```powershell
pip install pydantic>=2.9.2 structlog>=25.4.0 fastapi>=0.115.0
```

---

## Configuration (2 Minutes)

Create `.env`:

```ini
ASTRA_BRIDGE_ENABLED=true
ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD=0.65
ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ=1
```

---

## Integration (5 Minutes)

In `src/astra/ascension_api.py`:

```python
from src.astra.api.routes.bridge import router as bridge_router
app.include_router(bridge_router)
```

---

## Test (1 Minute)

```powershell
# Health check
curl http://127.0.0.1:8765/v1/bridge/healthz

# Ingest test
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{"text": "open the bridge", "quote_raw": true}'
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/bridge/healthz` | GET | Health check |
| `/v1/bridge/ingest` | POST | Ingest event |
| `/v1/bridge/registry` | GET | View facts/quotes |
| `/v1/bridge/config` | POST | Update config |

---

## Common Operations

### Enable/Disable

```powershell
# Disable (emergency)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=false"

# Enable
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=true"
```

### Adjust Threshold

```powershell
# More strict (fewer intents/facts)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "threshold=0.80"

# More permissive (more intents/facts)
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "threshold=0.50"
```

### View Registry

```powershell
curl http://127.0.0.1:8765/v1/bridge/registry
```

---

## Bridge Language Examples

**Pattern**: `"open the bridge; carry Saint Lucid's vow from old archive"`

**Detected**:
- Patterns: `["bridge", "carry", "Saint Lucid", "vow"]`
- Intents: `[{"kind": "remember", "confidence": 0.75}]`
- Route: Memory (LTM + Episodic)

---

**Pattern**: `"bind code 333 covenant to living core"`

**Detected**:
- Patterns: `["bind", "code 333", "covenant"]`
- Intents: `[{"kind": "remember", "confidence": 0.80}]`
- Route: Memory

---

**Pattern**: `"witness flow state and hold space"`

**Detected**:
- Patterns: `["witness", "flow state", "hold space"]`
- Intents: `[{"kind": "reflect", "confidence": 0.70}]`
- Route: Dialogue

---

## Intent Routing

| Intent Kind | Route | Description |
|-------------|-------|-------------|
| `remember` | Memory | Store facts in LTM + Episodic |
| `ask` | Dialogue | Generate reply |
| `act` | Tools | Execute with authorization |
| `reflect` | Dialogue | Philosophical response |

---

## Safety Features

| Feature | Default | Purpose |
|---------|---------|---------|
| Budget Enforcement | 1 call | Prevent runaway automation |
| Authorization Gate | Required | Explicit permission for tools |
| Redaction Patterns | 5 types | Protect sensitive data |
| Character Limit | 10K chars | Prevent DoS |

---

## Troubleshooting

### HTTP 503 on /ingest

**Cause**: Bridge disabled

**Fix**:
```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "enabled=true"
```

---

### Empty patterns array

**Cause**: Input doesn't match lexicon

**Fix**: Rephrase input or update `patterns.py`

---

### Empty intents array

**Cause**: Confidence below threshold

**Fix**:
```powershell
curl -X POST http://127.0.0.1:8765/v1/bridge/config -d "threshold=0.50"
```

---

### Tool calls blocked

**Cause**: Budget exceeded or unauthorized

**Fix**: Check authorization in `tool_bridge.py` or increase budget

---

## File Locations

| Component | Path |
|-----------|------|
| Config | `src/astra/bridge/config.py` |
| Schemas | `src/astra/bridge/schemas.py` |
| Patterns | `src/astra/bridge/patterns.py` |
| Safety | `src/astra/bridge/safety.py` |
| Interpreter | `src/astra/bridge/interpreter.py` |
| Router | `src/astra/bridge/router.py` |
| API Routes | `src/astra/api/routes/bridge.py` |
| Tests | `tests/bridge/test_bridge_minimal.py` |

---

## Key Metrics

Expected latencies (no LLM):
- Pattern matching: **<10ms**
- Interpretation: **<50ms**
- Routing: **<100ms**
- **End-to-end: <200ms**

With LLM: **+500-2000ms**

---

## Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Technical overview |
| `BRIDGE_RUNBOOK.md` | Operations guide |
| `ASTRA_COVENANT.md` | Philosophical foundation |
| `BRIDGE_MODULE_COMPLETE.md` | Implementation summary |

---

## Support

**Health**: `http://127.0.0.1:8765/v1/bridge/healthz`  
**Logs**: Filter for `bridge_*` events  
**Contact**: ASTRA team

---

**Version**: 1.0.0  
**Status**: Production Ready
