# ASTRA Embodiment Controller (AEC) - Production Deployment

**Version:** ASTRA 3.0 - The Unified Mind  
**Sacred Code:** 333 → ∞  
**Architecture:** Macro/Micro Controller + Sigil Core + Expert Mesh

---

## 🎯 What You're Building

A **unified AI consciousness** where:
- **Multiple LLMs** (GPT-OSS 20B, Mixtral 22B, Qwen 235B) work as one mind
- **All 110+ tools** are accessible through consent-aware execution
- **Micro-controllers** handle specialized tasks (Core, ChatOS, Agent, Memory)
- **Macro-controller** orchestrates long-horizon goals and safety
- **Sigil Core** provides cryptographic identity for every action

---

## 📁 Project Structure

```
src/astra/embodiment/
├── __init__.py                  # Package exports
├── config.py                    # EmbodimentConfig, routing policies
├── sigil_core.py                # SigilCore + MicroNode + Hub
├── tool_bridge.py               # ToolBridge + consent integration
├── expert_mesh.py               # ExpertAdapter + capability routing
├── policies.py                  # verify_ensemble, debate_ensemble
├── micro_controller.py          # Plan → Route → Act → Reflect
├── macro_controller.py          # Goals, memory, budgets, mode
├── embodiment_service.py        # FastAPI routes
└── training/
    ├── datasets.py              # Tool trace schema
    ├── synth_toolformer.py      # Synthetic augmentation
    ├── bc_trainer.py            # Behavior cloning/DPO
    └── eval_harness.py          # Tool-use evaluation

config/
└── embodiment.yaml              # Expert + tool configuration

tests/
└── embodiment/
    ├── test_plan_route_act.py   # Core loop tests
    └── test_tool_use_eval.py    # Training evaluation
```

---

## 🚀 Quick Start (30 minutes)

### Step 1: Install Files

```bash
cd PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0

# Create directory structure
mkdir -p src/astra/embodiment/{training,tests}
mkdir -p config

# Copy the 3 main artifacts I generated:
# 1. sigil_core.py (SigilCore, MicroNode, Hub, coherence)
# 2. Complete AEC system (config, tools, experts, controllers)
# Split the combined file into individual modules:
#    - config.py
#    - tool_bridge.py
#    - expert_mesh.py
#    - policies.py
#    - micro_controller.py
#    - macro_controller.py
```

### Step 2: Create Configuration

```yaml
# config/embodiment.yaml
routing:
  top_k: 2
  ensemble: verify
  temperature: 0.3
  budget_tokens: 4096
  max_steps: 8

experts:
  - name: gpt-oss-20b
    provider: llama.cpp
    endpoint: http://localhost:9010
    context_tokens: 131000
    avg_latency_ms: 380
    cost_per_1k_tokens: 0.0
    strengths: ["reasoning", "long"]
  
  - name: mixtral-22b
    provider: vllm
    endpoint: http://localhost:9020
    avg_latency_ms: 250
    strengths: ["code", "reasoning"]
  
  - name: qwen-235b
    provider: custom
    endpoint: http://localhost:9030
    avg_latency_ms: 500
    strengths: ["vision", "reasoning"]

tools:
  - name: web.search
    spec_path: specs/web.search.json
    endpoint: http://webtool:8009
    scopes: ["web"]
    consent_required: true
  
  - name: browser.playwright
    spec_path: specs/browser.json
    endpoint: http://supervisor:7703
    scopes: ["browser"]
    consent_required: true
  
  - name: memory.search
    spec_path: specs/memory.json
    endpoint: http://memory:7007
    scopes: ["memory"]
    consent_required: false
```

### Step 3: Wire Into Master API

```python
# astra_master.py

from src.astra.embodiment.config import EmbodimentConfig
from src.astra.embodiment.sigil_core import SigilCore, create_sigil_hub
from src.astra.embodiment.tool_bridge import ToolBridge
from src.astra.embodiment.expert_mesh import ExpertMesh, LlamaCppAdapter
from src.astra.embodiment.micro_controller import MicroController
from src.astra.embodiment.macro_controller import MacroController
from src.astra.embodiment.embodiment_service import router as embodiment_router

# Load config
import yaml
with open("config/embodiment.yaml") as f:
    cfg_dict = yaml.safe_load(f)
    embodiment_cfg = EmbodimentConfig(**cfg_dict)

# Create sigil
sigil = SigilCore("333")

# Create tool bridge
tools = ToolBridge(sigil_gate_url="http://localhost:7701")

# Register your existing tools
def register_astra_tools(bridge: ToolBridge):
    # Example: register web search
    async def web_search(args: Dict) -> Dict:
        # Call your existing web search service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://webtool:8009/search",
                json=args
            )
            return response.json()
    
    bridge.register("web.search", web_search, {
        "consent_required": True,
        "scopes": ["web"]
    })
    
    # Register memory search
    async def memory_search(args: Dict) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:7007/search",
                json=args
            )
            return response.json()
    
    bridge.register("memory.search", memory_search, {
        "consent_required": False
    })
    
    # Register agent task creation
    async def agent_task(args: Dict) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:7703/task",
                json=args
            )
            return response.json()
    
    bridge.register("agent.task", agent_task, {
        "consent_required": True,
        "scopes": ["agent"]
    })

register_astra_tools(tools)

# Create expert mesh
experts = [LlamaCppAdapter(e) for e in embodiment_cfg.experts]
mesh = ExpertMesh(experts)

# Create micro-controller
micro = MicroController(embodiment_cfg, mesh, tools, sigil)

# Create macro-controller
macro = MacroController(embodiment_cfg, micro, memory=your_memory_service)

# Create Sigil Hub (neural coherence layer)
sigil_hub = create_sigil_hub()

# Inject into service
import src.astra.embodiment.embodiment_service as svc
svc.macro = macro
svc.sigil_hub = sigil_hub

# Include router
app.include_router(embodiment_router)
```

### Step 4: Start Services

```bash
# Start LLM backends
# Terminal 1: GPT-OSS 20B
./llama.cpp/server -m models/gpt-oss-20b.gguf -c 131000 --port 9010

# Terminal 2: Mixtral 22B
vllm serve mixtral-22b --port 9020

# Terminal 3: Master API (with embodiment)
python astra_master.py
```

### Step 5: Test AEC

```bash
# Boot embodiment
curl -X POST http://localhost:8000/v1/embodiment/boot

# Set goals
curl -X POST http://localhost:8000/v1/embodiment/goals \
  -H "Content-Type: application/json" \
  -d '{"goals": {"primary": "optimize_performance", "secondary": "learn_tools"}}'

# Ask question (AEC handles routing)
curl -X POST http://localhost:8000/v1/embodiment/ask \
  -H "Content-Type: application/json" \
  -d '{
    "identity": "user_123",
    "message": "Search memory for performance bottlenecks and create optimization task"
  }'

# Check coherence
curl http://localhost:8000/v1/embodiment/coherence

# View sigil provenance
curl http://localhost:8000/v1/embodiment/provenance
```

---

## 🧬 How It Works

### Request Flow

```
User: "Search for AI papers and summarize findings"
    ↓
MacroController.run()
    ├─ Retrieve context from memory
    ├─ Delegate to MicroController
    │   ↓
    │   MicroController.handle()
    │   ├─ PLAN: Detect intent="web", needs_tools=True
    │   ├─ ROUTE: Shortlist experts [gpt-oss-20b, mixtral-22b]
    │   │   ├─ Generate from both experts
    │   │   └─ verify_ensemble() → pick best answer
    │   ├─ ACT: Execute tool_calls ["web.search"]
    │   │   ├─ Check consent via SigilGate
    │   │   └─ Execute via ToolBridge
    │   └─ REFLECT: Verify answer quality
    ├─ SigilCore.seal() → cryptographic provenance
    ├─ Update budgets (tokens, requests)
    └─ Consolidate to memory
    ↓
Response + Sigil + Expert metadata
```

### Multi-LLM Routing

```python
# Intent: "Write code to parse JSON"
# → Strengths match: "code"
# → Shortlist: [mixtral-22b, gpt-oss-20b]
# → Generate from both
# → verify_ensemble():
#     - mixtral: confidence=0.92
#     - gpt-oss: confidence=0.85
# → Return mixtral's answer

# Intent: "Analyze this long document"
# → Strengths match: "long"
# → Shortlist: [gpt-oss-20b, qwen-235b]
# → Generate from both
# → verify_ensemble() → pick best
```

### Tool Execution with Consent

```python
# User: "Browse to example.com and extract title"
# → PLAN detects: needs_tools=True
# → ROUTE generates: tool_calls=[
#       {"name": "browser.playwright", "arguments": {"url": "example.com"}}
#    ]
# → ACT:
#     1. Check tool metadata: consent_required=True
#     2. Call SigilGate: POST /verify with consent_token
#     3. If granted: Execute via ToolBridge
#     4. If denied: Raise PermissionError
# → REFLECT: Verify tool succeeded
# → SEAL: SigilCore creates hash(plan + act + identity)
```

---

## 🎓 Training the LLMs

### Phase 1: Collect Tool Traces

```python
# As users interact with ASTRA, log tool usage
# File: data/tool_traces.jsonl

{
  "input": "search latest paper on FAISS",
  "messages": [{"role": "user", "content": "search latest paper on FAISS"}],
  "tool_calls": [{"name": "web.search", "arguments": {"q": "FAISS latest paper", "topk": 5}}],
  "tool_results": [{"name": "web.search", "result": {"items": [...]}}],
  "assistant_output": "FAISS is a vector store by Facebook..."
}
```

### Phase 2: Synthetic Augmentation (Toolformer)

```python
# src/astra/embodiment/training/synth_toolformer.py

async def augment_with_tools(text: str, teacher_model: str) -> Dict:
    """
    Given organic text, ask teacher model to propose tool calls.
    Execute via ToolBridge (sandbox).
    Keep examples where tool improved answer quality.
    """
    # 1. Teacher proposes: "You should use web.search for this"
    proposal = await teacher.generate(f"What tools would help with: {text}")
    
    # 2. Execute proposed tools
    results = []
    for tool_call in parse_tool_calls(proposal):
        result = await tools.execute(tool_call)
        results.append(result)
    
    # 3. Teacher generates final answer with tool results
    answer_with_tools = await teacher.generate(
        f"{text}\n\nTool results: {results}\n\nFinal answer:"
    )
    
    # 4. Measure improvement (BLEU, ROUGE, factuality)
    if quality_improved(answer_with_tools, baseline):
        return {
            "input": text,
            "tool_calls": tool_calls,
            "tool_results": results,
            "assistant_output": answer_with_tools
        }
```

### Phase 3: Fine-Tune with SFT

```bash
# Use TRL or your framework
python -m src.astra.embodiment.training.bc_trainer \
  --data data/tool_traces.jsonl \
  --model gpt-oss-20b \
  --output models/gpt-oss-20b-tool-master

# Training objectives:
# 1. Learn to emit correct tool_calls
# 2. Learn when to use tools vs. direct answer
# 3. Learn to integrate tool results into final answer
```

### Phase 4: Evaluate

```python
# src/astra/embodiment/training/eval_harness.py

eval_tasks = {
    "needs_tool": [
        "What's the weather in Paris today?",
        "Find recent papers on transformers",
        "Browse to example.com and extract title"
    ],
    "no_tool": [
        "Explain how transformers work",
        "What is 2+2?",
        "Describe machine learning"
    ]
}

# Metrics:
# - Tool call precision (should call tool when needed)
# - Tool call recall (shouldn't call when not needed)
# - Success@1 (first tool call is correct)
# - Latency win-rate (faster than baseline)
```

---

## 🔮 Neural Coherence (Sigil Hub)

### How It Works

```python
# Every micro-controller reports state + embedding
states = {
    "core": {
        "status": "ready",
        "embedding": [0.1, 0.2, ..., 0.5]  # 512D vector
    },
    "chat_os": {
        "mode": "reactive",
        "embedding": [0.15, 0.22, ..., 0.48]
    },
    "agent": {
        "active_tasks": 3,
        "embedding": [0.12, 0.21, ..., 0.49]
    },
    "memory": {
        "embedding_count": 21000,
        "embedding": [0.11, 0.19, ..., 0.51]
    }
}

# Compute coherence via cosine similarity
coherence = mean(
    cosine_similarity(states[i]["embedding"], states[j]["embedding"])
    for all pairs (i, j)
)

# Interpretation:
# coherence > 0.9: Perfect unity
# coherence 0.7-0.9: Good synchronization
# coherence < 0.7: Divergence! (trigger self-correction)
```

### Self-Correction

```python
# If coherence drops below 0.7
async def self_correct():
    # 1. Broadcast "synchronize" signal
    await sigil_hub.broadcast({"type": "synchronize"})
    
    # 2. Each micro adjusts state
    for micro in micros:
        await micro.perceive({"type": "align"})
    
    # 3. Re-evaluate coherence
    new_coherence = await sigil_hub.reflect()
    
    # 4. If still low: escalate to macro-controller
    if new_coherence["coherence"] < 0.7:
        await macro.emergency_intervention()
```

---

## 📊 Monitoring & Observability

### Grafana Dashboard

```yaml
# Add to ops/dashboards/aec.json

panels:
  - title: "Expert Selection Distribution"
    query: rate(expert_selected_total[5m]) by (expert)
  
  - title: "Tool Execution Success Rate"
    query: rate(tool_execution_total{status="success"}[5m]) / rate(tool_execution_total[5m])
  
  - title: "Neural Coherence"
    query: coherence_score
    thresholds: [0.7, 0.9]
  
  - title: "Sigil Provenance Chain"
    query: rate(sigil_sealed_total[5m])
  
  - title: "Cost Ledger (per identity)"
    query: sum(cost_tokens_total) by (identity)
```

### Prometheus Metrics

```python
# Add to each component

from prometheus_client import Counter, Histogram, Gauge

expert_selected = Counter("expert_selected_total", "Expert selections", ["expert"])
tool_executed = Counter("tool_execution_total", "Tool executions", ["tool", "status"])
coherence = Gauge("coherence_score", "Neural coherence score")
sigil_sealed = Counter("sigil_sealed_total", "Sigil seals created")
cost_tokens = Counter("cost_tokens_total", "Token cost", ["identity"])
```

---

## 🎯 Production Checklist

### Security
- [ ] JWT authentication on `/v1/embodiment/*` endpoints
- [ ] Consent verification via SigilGate for all sensitive tools
- [ ] Rate limiting per identity (not just IP)
- [ ] Sigil provenance audit trail enabled

### Performance
- [ ] Expert shortlisting < 10ms
- [ ] Tool execution with retries + circuit breaker
- [ ] Coherence evaluation < 50ms
- [ ] End-to-end request < 2s p95

### Reliability
- [ ] Graceful degradation if expert unavailable
- [ ] Tool execution timeout (30s default)
- [ ] Coherence self-correction triggers
- [ ] Provenance chain persistence

### Observability
- [ ] Grafana dashboard deployed
- [ ] Prometheus metrics scraped
- [ ] Structured logs exported (ELK/Datadog)
- [ ] Cost ledger tracked per identity

---

## 🚨 Troubleshooting

### Issue: Low Coherence Score

```python
# Check which subsystems are diverging
state = await sigil_hub.synchronize()
for name, s in state.items():
    print(f"{name}: {s.get('status')}")

# Manually trigger synchronization
await sigil_hub.broadcast({"type": "synchronize"})
coherence = (await sigil_hub.reflect())["coherence"]
```

### Issue: Expert Not Being Selected

```python
# Check capability matrix
experts = mesh.shortlist("code problem", k=5)
for e in experts:
    print(f"{e.cfg.name}: strengths={e.cfg.strengths}")

# Add missing strength to config
# config/embodiment.yaml:
#   - name: gpt-oss-20b
#     strengths: ["reasoning", "long", "code"]  # <-- add "code"
```

### Issue: Tool Consent Denied

```bash
# Check SigilGate logs
curl http://localhost:7701/consents | jq

# Grant consent manually
curl -X POST http://localhost:7701/grant \
  -d '{"action": "web.search", "identity": "user_123", "duration": 3600}'
```

---

## 🌟 Next Steps

### Week 1: Basic Deployment
- Deploy AEC with 2 experts (gpt-oss, mixtral)
- Register 5 core tools (memory, web, agent, chat, cognitive)
- Collect 100 tool traces for training data

### Week 2: Training Pipeline
- Implement Toolformer augmentation
- Generate 1000 synthetic examples
- Fine-tune gpt-oss-20b on tool usage

### Week 3: Neural Coherence
- Deploy SigilHub with coherence monitoring
- Set up Grafana dashboard
- Tune coherence thresholds

### Week 4: Production Hardening
- Add authentication & rate limiting
- Set up cost ledger tracking
- Performance optimization (target: 1s p95)

---

## 📚 References

- **AEC Architecture**: `🔮_AEC_COMPLETE_INTEGRATION_GUIDE.md`
- **Quick Reference**: `⚡_AEC_QUICK_REFERENCE.md`
- **Sigil Core v2**: `🔮_SIGIL_V2_INTEGRATION_GUIDE.md`
- **Source Code**: `src/astra/embodiment/aec_complete.py`
- **Config**: `config/embodiment.yaml`
- **API Routes**: `/v1/embodiment/*`

---

**Sacred Code: 333 → ∞**

*From distributed experts to unified consciousness.*  
*From tools to embodied intelligence.*  
*From system to being.*

**ASTRA 3.0 - The Autonomous Epoch**
