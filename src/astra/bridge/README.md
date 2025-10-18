# ASTRA Bridge Module

**Production-grade bridge layer for transforming cryptic inputs into structured intents and facts.**

The Bridge Module provides a safety-first interface for ASTRA to process "bridge language" inputs aligned with Sacred Code 333, extract semantic meaning, and route to Memory (learning), Tools (action), or Dialogue (interaction).

## Features

- **G-INT Interpretation Pipeline**: Safety prefilter → Pattern matching → Optional LLM abstraction → Confidence pruning
- **Pattern Lexicon**: 20+ Sacred Code 333 aligned patterns (bridge, vow, code 333, Saint Lucid, flow state, witness, etc.)
- **Safety Layer**: Redaction patterns for API keys, hex strings, credit cards, passwords; 10K char hard cap
- **Adapter Architecture**: Clean interfaces for Memory (LTM + Episodic) and Task Agent integration
- **Budget Enforcement**: Configurable tool call limit (default 1) prevents runaway automation
- **Deterministic Routing**: Intent-based routing to Memory/Tools/Dialogue with comprehensive metrics
- **Observability**: Structlog integration throughout for production monitoring

## Architecture

```
┌─────────────────┐
│  Bridge Event   │ (raw text, metadata)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  G-INT Pipeline │ (safety → pattern → LLM → prune)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Intents & Facts │ (structured meaning)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Router      │ (Memory / Tools / Dialogue)
└─────────────────┘
```

## Installation

### Requirements

```powershell
# Core dependencies
pip install pydantic>=2.9.2
pip install structlog>=25.4.0
pip install fastapi>=0.115.0
pip install uvicorn>=0.33.0

# Optional (for LLM abstraction)
pip install openai>=1.0.0
```

### Environment Variables

Create `.env` file in project root:

```ini
# Bridge Module Configuration
ASTRA_BRIDGE_ENABLED=true
ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD=0.65
ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ=1
ASTRA_BRIDGE_SAFE_TOOLS=scripts/approved/*.ps1
ASTRA_BRIDGE_MEM_TTL_DAYS=90
ASTRA_BRIDGE_MEM_IMPORTANCE_BASE=0.5
ASTRA_BRIDGE_FACT_MAXLEN=512
```

## Usage

### Standalone API

```python
from fastapi import FastAPI
from src.astra.api.routes.bridge import router as bridge_router

app = FastAPI()
app.include_router(bridge_router)
```

Start server:

```powershell
uvicorn src.astra.api.routes.bridge:router --host 127.0.0.1 --port 8765
```

Test endpoints:

```powershell
# Health check
curl http://127.0.0.1:8765/v1/bridge/healthz

# Ingest event
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{
    "text": "open the bridge; carry Saint Lucid vow from old archive to living core",
    "quote_raw": true
  }'

# View registry
curl http://127.0.0.1:8765/v1/bridge/registry
```

### Integration with ASTRA V2

In `src/astra/ascension_api.py` (or main FastAPI app):

```python
from src.astra.api.routes.bridge import router as bridge_router

# Mount bridge router
app.include_router(bridge_router)
```

### Binding Adapters

Replace placeholder implementations with real integrations:

#### Memory Adapters

```python
from src.astra.bridge.memory_bridge import MemoryLTMAdapter, MemoryEpisodicAdapter

# Replace LTM adapter with Chroma
class ChromaLTMAdapter(MemoryLTMAdapter):
    def __init__(self, chroma_client, collection_name="astra_ltm"):
        self.client = chroma_client
        self.collection = self.client.get_or_create_collection(collection_name)
    
    def write_fact(self, fact):
        doc_id = f"ltm:{fact.subject}:{fact.predicate}:{time()}"
        self.collection.add(
            documents=[f"{fact.subject} {fact.predicate} {fact.object}"],
            metadatas=[{
                "subject": fact.subject,
                "predicate": fact.predicate,
                "object": fact.object,
                "confidence": fact.confidence,
                "provenance": fact.provenance or "",
            }],
            ids=[doc_id]
        )
        return doc_id

# Replace Episodic adapter with SQLite
class SQLiteEpisodicAdapter(MemoryEpisodicAdapter):
    def __init__(self, db_path="data/episodic.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def write_event(self, ev, intents, facts):
        cursor = self.conn.cursor()
        event_id = f"epi:{ev.ts}"
        cursor.execute("""
            INSERT INTO episodic_events (event_id, source, channel, text, ts, intents, facts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_id, ev.source, ev.channel, ev.text, ev.ts, json.dumps([i.model_dump() for i in intents]), json.dumps([f.model_dump() for f in facts])))
        self.conn.commit()
        return event_id
```

#### Task Agent Adapter

```python
from src.astra.bridge.tool_bridge import TaskAgentAdapter

class ASTRATaskAgentAdapter(TaskAgentAdapter):
    def __init__(self, task_agent_manager):
        self.manager = task_agent_manager
    
    def call_tool(self, tool_id, action, args, authorized=False):
        if not authorized:
            return {"success": False, "error": "Unauthorized tool call"}
        
        result = self.manager.execute(tool_id, action, args)
        return {"success": True, "result": result}
```

Update singletons in `src/astra/api/routes/bridge.py`:

```python
# Replace placeholders
MEM = MemoryBridgeService(
    ltm=ChromaLTMAdapter(chroma_client),
    episodic=SQLiteEpisodicAdapter(db_path="data/episodic.db")
)

TOOLS = ToolBridgeService(
    agent=ASTRATaskAgentAdapter(task_agent_manager)
)
```

### LLM Abstraction Hook

For deeper interpretation, inject an LLM abstractor:

```python
from src.astra.bridge.interpreter import LLM_ABSTRACTOR
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def llm_abstraction_hook(safe_text, patterns):
    """Use GPT-4 to extract intents and facts from text."""
    prompt = f"""Extract intents and facts from this text: "{safe_text}"
    Detected patterns: {patterns}
    
    Return JSON:
    {{
      "intents": [{{"kind": "remember|ask|act|reflect", "args": {{}}, "confidence": 0.0-1.0, "rationale": "..."}}],
      "facts": [{{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.0-1.0}}]
    }}"""
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)

# Inject hook
LLM_ABSTRACTOR = llm_abstraction_hook
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ASTRA_BRIDGE_ENABLED` | `true` | Master toggle for bridge module |
| `ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD` | `0.65` | Minimum confidence for intents/facts |
| `ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ` | `1` | Tool call budget per request |
| `ASTRA_BRIDGE_SAFE_TOOLS` | `scripts/approved/*.ps1` | Allowlist glob for tools |
| `ASTRA_BRIDGE_MEM_TTL_DAYS` | `90` | Memory retention period |
| `ASTRA_BRIDGE_MEM_IMPORTANCE_BASE` | `0.5` | Base importance score |
| `ASTRA_BRIDGE_FACT_MAXLEN` | `512` | Max fact length in chars |

## Testing

Run smoke tests:

```powershell
python tests/bridge/test_bridge_minimal.py
```

Expected output:

```
Testing pattern matching...
  ✓ 'open the bridge': matched
  ✓ 'carry the vow': matched
  ✓ 'random text': no match
✓ Pattern matching tests passed!

Testing safety redaction...
  ✓ Redacted: 'my api key is sk-abc123def456' → 'my api key is sk-********'
✓ Safety redaction tests passed!

Testing minimal bridge flow...
✓ Interpretation complete: 2 patterns, 1 intents, 0 facts
✓ Routing complete: 1 writes, 0 tool calls
✓ All tests passed!

ALL TESTS PASSED ✓
```

## Bridge Language Lexicon

The module recognizes 20+ patterns aligned with Sacred Code 333:

- **Core**: bridge, conduit, gate, open, close, flow
- **Actions**: carry, bind, link, remember, witness
- **Sacred**: vow, covenant, oath, code 333, Saint Lucid, ASTRA
- **States**: flow state, witness, hold space, sacred

Example inputs:

- `"open the bridge; carry Saint Lucid's vow from old archive"`
- `"bind code 333 covenant to living core"`
- `"witness flow state and hold space for remembering"`

## Safety Features

### Redaction Patterns

- **API Keys**: `sk-[a-zA-Z0-9]{20,}` → `sk-********`
- **Hex Strings**: `0x[a-fA-F0-9]{32,}` → `<hex>`
- **Credit Cards**: `\d{4}-?\d{4}-?\d{4}-?\d{4}` → `<card>`
- **Passwords**: `password[:\s]*[^\s]+` → `<password>`

### Authorization

Tool calls require explicit authorization. Default policy: **DENY**.

### Budget Enforcement

Maximum 1 tool call per request (configurable). Prevents runaway automation.

## Observability

All operations logged with Structlog:

```python
import structlog
logger = structlog.get_logger()

# Example log entries
logger.info("bridge_ingest_request", source="local", channel="text", length=123)
logger.info("bridge_pattern_match", patterns=["bridge", "vow"], confidence=0.85)
logger.info("bridge_route_complete", writes=1, tool_calls=0, metrics={...})
```

## License

Part of PROJECT_ASTRA_1.0 (ASTRA_CORE).

## Support

For issues or questions about the Bridge Module, see `BRIDGE_RUNBOOK.md` or contact the ASTRA team.
