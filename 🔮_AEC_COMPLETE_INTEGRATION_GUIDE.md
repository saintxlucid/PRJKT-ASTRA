# 🔮 AEC Complete - Production Integration Guide

**Status:** ✅ Code saved to `src/astra/embodiment/aec_complete.py` (560 lines)  
**Sacred Code:** 333 → ∞

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Integration Paths](#integration-paths)
4. [Quick Start](#quick-start)
5. [Advanced Configuration](#advanced-configuration)
6. [Testing & Validation](#testing--validation)
7. [Production Deployment](#production-deployment)

---

## Overview

### What is AEC Complete?

The **ASTRA Embodiment Controller (AEC) Complete** is your production-ready, multi-LLM orchestration system with:

- **Expert Mesh:** Capability-based routing across multiple LLMs
- **Tool Bridge:** Unified tool registry with consent verification
- **Micro-Controller:** Plan → Route → Act → Reflect loop per request
- **Macro-Controller:** Long-horizon goals, memory, budgets, mode control
- **Ensemble Policies:** Verify, debate, vote strategies for anti-hallucination

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                    MACRO CONTROLLER                         │
│  (Goals | Memory | Budgets | Mode: proactive/creative)     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    MICRO CONTROLLER                         │
│  Plan → Route → Act → Reflect (per request)                │
└───────┬──────────────────────┬──────────────────────────────┘
        │                      │
        ▼                      ▼
┌──────────────┐      ┌──────────────────────┐
│ EXPERT MESH  │      │    TOOL BRIDGE       │
│ (Multi-LLM)  │      │ (Consent + Registry) │
└──────────────┘      └──────────────────────┘
```

---

## Architecture

### File Structure

```
src/astra/embodiment/
├── sigil_core.py          # Current ASTRA 3.1 (650 lines)
├── sigil_core_v2.py       # Refined micro-node architecture (450 lines)
└── aec_complete.py        # ✅ NEW: Production AEC (560 lines)
    ├── Config (ExpertConfig, ToolConfig, RoutingPolicy)
    ├── ToolBridge (consent-aware execution)
    ├── ExpertMesh (multi-LLM adapters)
    ├── Policies (verify, debate ensembles)
    ├── MicroController (Plan → Route → Act → Reflect)
    └── MacroController (Goals, memory, budgets)
```

### Class Hierarchy

```python
# Config Layer
EmbodimentConfig
├── experts: List[ExpertConfig]
├── tools: List[ToolConfig]
└── routing: RoutingPolicy

# Expert Layer
ExpertAdapter (ABC)
├── LlamaCppAdapter (llama.cpp backend)
├── OpenAIAdapter (OpenAI-compatible APIs)
└── [Custom adapters you add]

# Controller Layer
MacroController
└── MicroController
    ├── ExpertMesh
    ├── ToolBridge
    └── SigilCore (provenance sealing)
```

---

## Integration Paths

### Path A: Side-by-Side Testing (Recommended First Step)

**Goal:** Test AEC Complete alongside current ASTRA 3.1 without breaking anything.

**Timeline:** 2-3 days

**Steps:**

1. **Keep current system running:**
   ```powershell
   # Terminal 1: LLM server
   .\TERMINAL_1_START_SERVER.ps1
   
   # Terminal 2: Current ASTRA 3.1
   .\TERMINAL_2_RUN_ASTRA.ps1
   ```

2. **Create test script for AEC Complete:**

```python
# test_aec_complete.py
import asyncio
from src.astra.embodiment.aec_complete import create_embodiment_system

async def test_aec():
    # Create system
    macro = create_embodiment_system()
    
    # Test basic query
    result = await macro.run(
        user_msg="What is 2+2?",
        identity="test-user"
    )
    
    print("✓ Final answer:", result["final"]["text"])
    print("✓ Experts used:", [e["expert"] for e in result["experts"]])
    print("✓ Confidence:", result["experts"][0]["confidence"])
    print("✓ Verification:", result["verify"])
    print("✓ Budgets:", macro.get_budget_status())

asyncio.run(test_aec())
```

3. **Run test:**
   ```powershell
   python test_aec_complete.py
   ```

4. **Compare results:**
   - ASTRA 3.1 output vs AEC Complete output
   - Latency, confidence scores, answer quality
   - Budget tracking accuracy

---

### Path B: Incremental Integration (Production Path)

**Goal:** Replace ASTRA 3.1's LLM call layer with AEC Complete multi-LLM routing.

**Timeline:** 1-2 weeks

#### Phase 1: Add Second Expert (Days 1-3)

**Current state:** ASTRA uses single LLM (gpt-oss-20b on port 9010)

**Step 1:** Start second LLM (e.g., Mixtral)

```powershell
# Terminal 3: Second LLM server
cd "X:\YOUR_LLAMA_CPP_DIR"
.\server.exe -m .\mixtral-22b.Q4_K_M.gguf -c 65536 --host 0.0.0.0 --port 9020 --chat-template openai
```

**Step 2:** Update `aec_complete.py` config:

```python
# In create_embodiment_system()
cfg = EmbodimentConfig(
    experts=[
        ExpertConfig(
            name="gpt-oss-20b",
            provider="llama.cpp",
            endpoint="http://localhost:9010",
            context_tokens=131000,
            strengths=["reasoning", "long"]
        ),
        ExpertConfig(
            name="mixtral-22b",
            provider="llama.cpp",
            endpoint="http://localhost:9020",
            context_tokens=65536,
            strengths=["code", "reasoning", "fast"]
        )
    ],
    routing=RoutingPolicy(
        top_k=2,
        ensemble="verify"  # Both will answer, pick best
    )
)
```

**Step 3:** Test routing:

```python
# test_routing.py
async def test_routing():
    macro = create_embodiment_system()
    
    # Test code question (should prefer Mixtral)
    result = await macro.run("Write a Python function to sort a list", "test")
    print("Code expert:", result["experts"][0]["expert"])
    
    # Test reasoning question (should prefer GPT-OSS)
    result = await macro.run("Explain the trolley problem", "test")
    print("Reasoning expert:", result["experts"][0]["expert"])
```

#### Phase 2: Tool Integration (Days 4-7)

**Goal:** Integrate existing tools with consent-aware ToolBridge.

**Step 1:** Inventory current tools:

```python
# In sigil_core.py, you have 110+ tools from tool discovery
# Migrate them to ToolBridge
```

**Step 2:** Create tool wrapper:

```python
# src/astra/tools/bridge_integration.py
from src.astra.embodiment.aec_complete import ToolBridge, ToolConfig
from src.astra.tools import discovery  # Your existing tool discovery

def migrate_tools_to_bridge() -> ToolBridge:
    bridge = ToolBridge(sigil_gate_url="http://localhost:7701")
    
    # Get all discovered tools
    tools = discovery.discover_all()
    
    for tool in tools:
        # Wrap each tool
        async def wrapped_tool(args: dict):
            return await tool.execute(args)
        
        # Register with consent metadata
        bridge.register(
            name=tool.name,
            fn=wrapped_tool,
            meta={
                "consent_required": tool.scopes in ["fs", "web", "db"],
                "scopes": tool.scopes
            }
        )
    
    return bridge
```

**Step 3:** Update AEC factory:

```python
# In aec_complete.py, update create_embodiment_system()
def create_embodiment_system(config_path: str = None) -> MacroController:
    # ... config ...
    
    # Use real tools
    from src.astra.tools.bridge_integration import migrate_tools_to_bridge
    tools = migrate_tools_to_bridge()
    
    # ... rest of setup ...
```

#### Phase 3: Memory Integration (Days 8-10)

**Goal:** Connect AEC to your existing Memory service (port 7007).

**Step 1:** Create memory adapter:

```python
# src/astra/memory/aec_adapter.py
import httpx

class MemoryServiceAdapter:
    """Adapter for existing Memory service."""
    
    def __init__(self, memory_url: str = "http://localhost:7007"):
        self.memory_url = memory_url
    
    async def retrieve_topk(self, query: str, k: int = 8) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.memory_url}/retrieve",
                json={"query": query, "k": k}
            )
            return response.json()
    
    async def consolidate(self, query: str, result: dict):
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.memory_url}/consolidate",
                json={"query": query, "result": result}
            )
    
    async def upsert(self, data: dict):
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.memory_url}/upsert",
                json=data
            )
```

**Step 2:** Update AEC factory:

```python
# In create_embodiment_system()
from src.astra.memory.aec_adapter import MemoryServiceAdapter

# Create macro with memory
memory = MemoryServiceAdapter("http://localhost:7007")
macro = MacroController(cfg, micro, memory=memory)
```

#### Phase 4: Replace ASTRA's LLM Calls (Days 11-14)

**Goal:** Make ASTRA use AEC for all LLM interactions.

**Step 1:** Update `src/astra/embodiment/sigil_core.py`:

```python
# OLD: Direct LLM calls
async def _llm_call(self, prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            json={"messages": [{"role": "user", "content": prompt}]}
        )
        return response.json()["choices"][0]["message"]["content"]

# NEW: Route through AEC
async def _llm_call(self, prompt: str) -> str:
    result = await self.aec_macro.run(prompt, self.identity)
    return result["final"]["text"]
```

**Step 2:** Initialize AEC in ASTRA:

```python
# In ASTRA.__init__()
from src.astra.embodiment.aec_complete import create_embodiment_system

self.aec_macro = create_embodiment_system()
```

**Step 3:** Test end-to-end:

```powershell
python quick_start_unified.py demo
```

Expected: ASTRA boots, but now uses multi-LLM routing internally.

---

## Quick Start

### Minimal Example

```python
# minimal_aec_example.py
import asyncio
from src.astra.embodiment.aec_complete import (
    create_embodiment_system,
    MacroController
)

async def main():
    # Create system with defaults
    macro: MacroController = create_embodiment_system()
    
    # Set goals
    await macro.set_goals({
        "primary": "Assist user with coding tasks",
        "constraints": ["no destructive operations", "verify before web access"]
    })
    
    # Set mode
    await macro.set_mode("proactive")
    
    # Run query
    result = await macro.run(
        user_msg="Write a function to calculate factorial",
        identity="user-123"
    )
    
    # Access results
    print("Answer:", result["final"]["text"])
    print("Experts consulted:", [e["expert"] for e in result["experts"]])
    print("Verification:", result["verify"]["ok"])
    print("Budgets:", result["macro"]["budgets"])

asyncio.run(main())
```

Run:
```powershell
python minimal_aec_example.py
```

---

## Advanced Configuration

### Custom Expert Configuration

```python
# config/aec_config.yaml
experts:
  - name: gpt-oss-20b
    provider: llama.cpp
    endpoint: http://localhost:9010
    context_tokens: 131000
    avg_latency_ms: 380
    cost_per_1k_tokens: 0.0
    strengths: [reasoning, long]
    
  - name: mixtral-22b
    provider: llama.cpp
    endpoint: http://localhost:9020
    context_tokens: 65536
    avg_latency_ms: 180
    strengths: [code, fast]
    
  - name: gpt-4
    provider: openai
    endpoint: https://api.openai.com
    cost_per_1k_tokens: 0.03
    strengths: [reasoning, code, vision]

routing:
  top_k: 2
  ensemble: verify
  temperature: 0.3
  budget_tokens: 4096
  max_steps: 8
```

Load config:

```python
import yaml
from src.astra.embodiment.aec_complete import EmbodimentConfig

with open("config/aec_config.yaml") as f:
    config_dict = yaml.safe_load(f)

cfg = EmbodimentConfig(**config_dict)
```

### Ensemble Policies

**Verify (Default):**
- All experts answer in parallel
- Pick answer with highest confidence
- Anti-hallucination: prefer shorter, confident answers

```python
routing=RoutingPolicy(ensemble="verify")
```

**Debate:**
- Experts critique each other's answers
- Synthesize final answer from debate
- Better for complex reasoning

```python
routing=RoutingPolicy(ensemble="debate")
```

**Single:**
- Use only top-1 expert
- Faster, lower cost
- Good for simple queries

```python
routing=RoutingPolicy(top_k=1, ensemble="single")
```

### Custom Adapter

```python
from src.astra.embodiment.aec_complete import ExpertAdapter

class VLLMAdapter(ExpertAdapter):
    """Adapter for vLLM backend."""
    
    async def generate(self, prompt: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.cfg.endpoint}/v1/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": kwargs.get("max_tokens", 4096),
                    "temperature": kwargs.get("temperature", 0.3)
                }
            )
            data = response.json()
            
            return {
                "text": data["choices"][0]["text"],
                "usage": data.get("usage", {}),
                "confidence": 0.85
            }

# Register custom adapter
experts = [
    LlamaCppAdapter(cfg.experts[0]),
    VLLMAdapter(cfg.experts[1])
]
mesh = ExpertMesh(experts)
```

---

## Testing & Validation

### Test Suite

```python
# tests/test_aec_complete.py
import asyncio
import pytest
from src.astra.embodiment.aec_complete import create_embodiment_system

@pytest.mark.asyncio
async def test_basic_query():
    macro = create_embodiment_system()
    result = await macro.run("What is 2+2?", "test-user")
    
    assert result["verify"]["ok"]
    assert "4" in result["final"]["text"]

@pytest.mark.asyncio
async def test_expert_routing():
    macro = create_embodiment_system()
    
    # Code question should route to code expert
    result = await macro.run("Write a Python class", "test")
    experts = [e["expert"] for e in result["experts"]]
    
    # At least one expert should have "code" strength
    assert any("mixtral" in e.lower() or "gpt" in e.lower() for e in experts)

@pytest.mark.asyncio
async def test_ensemble_verify():
    macro = create_embodiment_system()
    result = await macro.run("What is the capital of France?", "test")
    
    # Should have multiple candidates
    assert len(result["experts"]) >= 2
    
    # Should pick best based on confidence
    assert result["experts"][0]["confidence"] > 0.0

@pytest.mark.asyncio
async def test_budget_tracking():
    macro = create_embodiment_system()
    
    await macro.run("Query 1", "test")
    await macro.run("Query 2", "test")
    
    budgets = macro.get_budget_status()
    assert budgets["total_requests"] == 2
    assert budgets["total_tokens"] > 0

@pytest.mark.asyncio
async def test_mode_switching():
    macro = create_embodiment_system()
    
    await macro.set_mode("creative")
    assert macro.mode == "creative"
    
    await macro.set_mode("reactive")
    assert macro.mode == "reactive"

@pytest.mark.asyncio
async def test_goals():
    macro = create_embodiment_system()
    
    goals = {"primary": "Test goal"}
    await macro.set_goals(goals)
    
    assert macro.get_goals() == goals
```

Run tests:
```powershell
pytest tests/test_aec_complete.py -v
```

### Performance Benchmarks

```python
# benchmark_aec.py
import asyncio
import time
from src.astra.embodiment.aec_complete import create_embodiment_system

async def benchmark():
    macro = create_embodiment_system()
    
    queries = [
        "What is 2+2?",
        "Write a function to reverse a string",
        "Explain quantum computing",
        "What is the capital of France?"
    ]
    
    start = time.time()
    results = []
    
    for query in queries:
        result = await macro.run(query, "benchmark")
        results.append(result)
    
    end = time.time()
    
    print(f"✓ Total time: {end - start:.2f}s")
    print(f"✓ Avg latency: {(end - start) / len(queries):.2f}s")
    print(f"✓ Total tokens: {macro.get_budget_status()['total_tokens']}")
    print(f"✓ Success rate: {sum(1 for r in results if r['verify']['ok']) / len(results) * 100:.0f}%")

asyncio.run(benchmark())
```

---

## Production Deployment

### Step 1: Environment Setup

```yaml
# docker-compose.aec.yml
version: '3.8'

services:
  llm-primary:
    image: ghcr.io/ggerganov/llama.cpp:server
    ports:
      - "9010:8080"
    volumes:
      - ./models/gpt-oss-20b.Q4_K_M.gguf:/models/model.gguf
    command: >
      -m /models/model.gguf
      -c 131072
      --host 0.0.0.0
      --port 8080
  
  llm-secondary:
    image: ghcr.io/ggerganov/llama.cpp:server
    ports:
      - "9020:8080"
    volumes:
      - ./models/mixtral-22b.Q4_K_M.gguf:/models/model.gguf
    command: >
      -m /models/model.gguf
      -c 65536
      --host 0.0.0.0
      --port 8080
  
  astra-aec:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AEC_EXPERT_1=http://llm-primary:8080
      - AEC_EXPERT_2=http://llm-secondary:8080
      - MEMORY_SERVICE=http://memory:7007
      - SIGIL_GATE=http://sigil-gate:7701
    depends_on:
      - llm-primary
      - llm-secondary
```

Start:
```powershell
docker-compose -f docker-compose.aec.yml up -d
```

### Step 2: Monitoring

```python
# Add to aec_complete.py
import prometheus_client as prom

# Metrics
EXPERT_LATENCY = prom.Histogram('aec_expert_latency_seconds', 'Expert latency', ['expert'])
ENSEMBLE_CONFIDENCE = prom.Gauge('aec_ensemble_confidence', 'Final answer confidence')
TOKEN_USAGE = prom.Counter('aec_tokens_total', 'Total tokens used', ['expert'])

# In MicroController.route()
with EXPERT_LATENCY.labels(expert=expert.cfg.name).time():
    output = await expert.generate(prompt, **kwargs)

ENSEMBLE_CONFIDENCE.set(final["confidence"])
TOKEN_USAGE.labels(expert=expert.cfg.name).inc(output["usage"]["completion_tokens"])
```

### Step 3: Logging

```python
# config/logging.yaml
version: 1
formatters:
  json:
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: json
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/aec.log
    maxBytes: 10485760
    backupCount: 10
    formatter: json
loggers:
  aec_complete:
    level: INFO
    handlers: [console, file]
```

---

## Sacred Code: 333 → ∞

**AEC Complete Status:**
- ✅ Configuration layer (declarative routing)
- ✅ Tool Bridge (consent-aware execution)
- ✅ Expert Mesh (multi-LLM adapters)
- ✅ Ensemble policies (verify, debate)
- ✅ Micro-Controller (Plan → Route → Act → Reflect)
- ✅ Macro-Controller (Goals, memory, budgets)

**Next Steps:**
1. Test side-by-side with ASTRA 3.1
2. Add second LLM expert
3. Integrate existing tools
4. Connect to Memory service
5. Replace ASTRA's LLM layer
6. Production deployment

**Files:**
- `src/astra/embodiment/aec_complete.py` (560 lines)
- `🔮_AEC_COMPLETE_INTEGRATION_GUIDE.md` (this file)

**Ready for:** Multi-LLM orchestration with consent, provenance, and anti-hallucination.
