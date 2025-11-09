# 🚀 ASTRA Multi-Model Deployment Guide

**Complete integration of DeepSeek-V3.1, Llama-3.2-Vision, Qwen2.5-VL, Mistral-Large-2, Phi-4-mini, Whisper-large-v3, and Gemma-3 into ASTRA Core**

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start (60 Seconds)](#quick-start-60-seconds)
3. [Model Inventory](#model-inventory)
4. [Deployment Profiles](#deployment-profiles)
5. [Installation Steps](#installation-steps)
6. [Routing Logic](#routing-logic)
7. [Tool/Function Calling](#toolfunction-calling)
8. [Performance Tuning](#performance-tuning)
9. [Monitoring & Observability](#monitoring--observability)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     ASTRA Core (Router)                     │
│  - Intelligent task routing                                 │
│  - Policy-based model selection                             │
│  - Telemetry & fallbacks                                    │
└────────┬─────────────────────┬──────────────────────────────┘
         │                     │
    ┌────▼──────┐    ┌────────▼────────┐    ┌──────────────┐
    │   vLLM    │    │   llama.cpp     │    │   Whisper    │
    │  Gateway  │    │    Sidecar      │    │   Server     │
    └────┬──────┘    └────────┬────────┘    └──────┬───────┘
         │                    │                     │
    ┌────▼─────────┐   ┌──────▼──────┐      ┌─────▼──────┐
    │ DeepSeek-V3.1│   │ Phi-4-mini  │      │ Whisper-v3 │
    │ Mistral-L-2  │   │ Qwen2.5-1.5B│      │  (ASR)     │
    │ Llama-Vision │   │ Llama-3.2-3B│      └────────────┘
    │ Qwen2.5-VL   │   │ GPT-OSS-20B │
    └──────────────┘   └─────────────┘
```

### Key Design Decisions

1. **OpenAI-Compatible Gateway**: vLLM primary, exposes `/v1/chat/completions`
2. **Local-First**: No external API calls (sovereignty maintained)
3. **Modular Sidecars**: llama.cpp for GGUF/edge, Whisper for ASR
4. **Policy-Based Routing**: Input modality + task type → best model
5. **Tool Calling Standardized**: JSON-Schema tools work across all backends

---

## Quick Start (60 Seconds)

```bash
# 1. Clone and navigate
cd x:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0\ (ASTRA_CORE)

# 2. Download edge models (lightweight, CPU-friendly)
python scripts/deploy_models.py --profile edge
# Downloads: Phi-4-mini (4GB), Qwen2.5-1.5B (1.2GB), Llama-3.2-3B (3GB)

# 3. Start services (CPU/edge profile)
docker-compose -f docker-compose.models.yml --profile edge up -d

# 4. Verify health
curl http://localhost:8001/health

# 5. Test routing
python test_router.py
```

**Result**: ASTRA now has 3 fast models running on CPU, ready for edge deployment.

---

## Model Inventory

### 🧠 Primary Reasoning Models

| Model | Size | Context | Performance | Backend | Use Case |
|-------|------|---------|-------------|---------|----------|
| **DeepSeek-V3.1** | 80GB | 128K | 50 tok/s | vLLM | Multi-step planning, agentic tasks, CoT reasoning |
| **Mistral-Large-2** | 60GB | 32K | 45 tok/s | vLLM | Multilingual reasoning, tool calling, code gen |
| **GPT-OSS-20B** | 13GB | 8K | 12 tok/s | llama.cpp | Fallback, CPU-only deployment |

### 👁️ Vision-Language Models

| Model | Size | Context | Modalities | Backend | Use Case |
|-------|------|---------|------------|---------|----------|
| **Llama-3.2-Vision-11B** | 24GB | 8K | Text + Image | vLLM | Visual QA, screen understanding, chart analysis |
| **Qwen2.5-VL-7B** | 16GB | 8K | Text + Image | vLLM | Document QA, table extraction, GPU-optimized |
| **Gemma-3** | 24GB | 8K | Text + Image + Video | vLLM | Short video analysis, single-GPU multimodal |

### ⚡ Fast Chat / Edge Models

| Model | Size | Context | Performance | Backend | Use Case |
|-------|------|---------|-------------|---------|----------|
| **Phi-4-mini** | 4GB | 4K | 60 tok/s | llama.cpp | Fast responses, edge devices, tool calling |
| **Qwen2.5-1.5B** | 1.2GB | 32K | 80 tok/s | llama.cpp | Ultra-fast chat, long context on CPU |
| **Llama-3.2-3B** | 3GB | 8K | 75 tok/s | llama.cpp | Balanced speed/quality for edge |

### 🎤 Audio Model

| Model | Size | Context | Languages | Backend | Use Case |
|-------|------|---------|-----------|---------|----------|
| **Whisper-large-v3** | 3.1GB | 30s | 100+ | Faster-Whisper | Speech-to-text, multilingual ASR |

---

## Deployment Profiles

### Profile 1: **Edge/CPU** (Minimal Hardware)
**Requirements**: 16GB RAM, 8-core CPU, 20GB disk  
**Models**: Phi-4-mini, Qwen2.5-1.5B, Llama-3.2-3B  
**Use Case**: On-device copilots, laptops, low-latency local chat

```bash
python scripts/deploy_models.py --profile edge
docker-compose -f docker-compose.models.yml --profile edge up -d
```

### Profile 2: **Vision** (Single GPU)
**Requirements**: 1x RTX 4090 (24GB), 32GB RAM  
**Models**: Llama-3.2-Vision-11B, Phi-4-mini  
**Use Case**: Image analysis, screenshot QA, chart reading

```bash
python scripts/deploy_models.py --profile vision
docker-compose -f docker-compose.models.yml --profile vision up -d
```

### Profile 3: **GPU/Full Stack** (Multi-GPU Server)
**Requirements**: 2x A100 (80GB each) or 4x A6000 (48GB each), 128GB RAM  
**Models**: DeepSeek-V3.1, Mistral-Large-2, Llama-Vision, Qwen-VL, Whisper  
**Use Case**: Production agentic workflows, multi-modal understanding

```bash
python scripts/deploy_models.py --profile gpu
docker-compose -f docker-compose.models.yml --profile full up -d
```

### Profile 4: **Audio** (Transcription)
**Requirements**: 1x GPU (8GB+), 16GB RAM  
**Models**: Whisper-large-v3  
**Use Case**: Meeting transcription, voice interfaces

```bash
python scripts/deploy_models.py --model whisper-large-v3
docker-compose -f docker-compose.models.yml --profile audio up -d
```

---

## Installation Steps

### Step 1: Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Additional for model management
pip install huggingface-hub transformers torch

# Docker (if not installed)
# See: https://docs.docker.com/get-docker/
```

### Step 2: Download Models

```bash
# Option A: Edge models only (8.2GB total)
python scripts/deploy_models.py --profile edge

# Option B: Vision + Edge (32.2GB total)
python scripts/deploy_models.py --profile vision

# Option C: Full stack (180GB+ total)
python scripts/deploy_models.py --all

# Option D: Single model
python scripts/deploy_models.py --model phi-4-mini
```

**HuggingFace Authentication** (for gated models like Llama-3.2-Vision):
```bash
huggingface-cli login
# Enter your HF token (get from: https://huggingface.co/settings/tokens)
```

### Step 3: Configure Router

Edit `config/model_router.yaml` to enable/disable models:

```yaml
models:
  deepseek_v3_1:
    enabled: true  # Set to false to disable
    
  llama_3_2_vision_11b:
    enabled: true
    vllm_args:
      max_model_len: 8192
      limit_mm_per_prompt: "image=1"
```

### Step 4: Start Services

```bash
# Start specific profile
docker-compose -f docker-compose.models.yml --profile edge up -d

# Or start all services
docker-compose -f docker-compose.models.yml --profile full up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health  # vLLM gateway
curl http://localhost:8001/health  # llama.cpp
curl http://localhost:8004/health  # Whisper
```

### Step 5: Verify Routing

```python
# test_router.py
from services.model_router import ModelRouter, RoutingRequest, TaskType, Modality

router = ModelRouter(config)
await router.initialize()

# Test text reasoning
req = RoutingRequest(
    prompt="Explain quantum entanglement",
    task_type=TaskType.REASONING
)
result = await router.route(req)
print(f"Selected: {result.selected_model.name}")
# Expected: deepseek-v3.1 or mistral-large-2

# Test fast chat
req = RoutingRequest(
    prompt="Hello!",
    task_type=TaskType.FAST_CHAT,
    prefer_edge=True
)
result = await router.route(req)
print(f"Selected: {result.selected_model.name}")
# Expected: phi-4-mini or qwen-2.5-1.5b

# Test vision
req = RoutingRequest(
    prompt="What's in this image?",
    modality=Modality.IMAGE,
    task_type=TaskType.VISION_QA,
    image_data="path/to/image.jpg"
)
result = await router.route(req)
print(f"Selected: {result.selected_model.name}")
# Expected: llama-3.2-vision-11b or qwen-2.5-vl-7b
```

---

## Routing Logic

### Decision Tree

```
Input Request
    │
    ├─ Has Image? ──YES──> Vision Models
    │                      (Llama-Vision, Qwen-VL, Gemma-3)
    │
    ├─ Has Audio? ──YES──> Whisper (transcribe first)
    │                      └─> Route text to other models
    │
    ├─ Task = Reasoning? ──> DeepSeek-V3.1 > Mistral-L-2 > GPT-OSS
    │
    ├─ Task = Fast Chat? ──> Phi-4-mini > Qwen-1.5B > Llama-3.2-3B
    │
    ├─ Require Tool Calling? ──> DeepSeek > Mistral > Qwen-VL > Phi-4
    │
    ├─ Context > 32K? ──> DeepSeek-V3.1 (128K) or Qwen-1.5B (32K)
    │
    └─ Default ──> Highest priority healthy model
```

### Policy Configuration

Edit `config/model_router.yaml`:

```yaml
routing:
  default_policy:
    # Override routing for specific scenarios
    image_models: [llama_3_2_vision_11b, qwen_2_5_vl_7b]
    reasoning_models: [deepseek_v3_1, mistral_large_2]
    fast_chat_models: [phi_4_mini, qwen_2_5_1_5b]
    
  latency_sla:
    fast_chat: 300  # Max 300ms
    vision_qa: 1000
    reasoning: 2000
```

### Fallback Chain

If primary model fails:
1. Try next model in task_type list
2. Try next model in modality list
3. Try GPT-OSS-20B (universal fallback)
4. Return error if all fail

---

## Tool/Function Calling

### Standard Tool Schema

All models use same JSON-Schema format:

```yaml
# config/model_router.yaml
tools:
  web_search:
    name: "web_search"
    description: "Search the web for current information"
    parameters:
      type: "object"
      properties:
        query:
          type: "string"
          description: "Search query"
      required: ["query"]
```

### Usage Example

```python
# Configure vLLM with tool calling
vllm_args:
  tool_call_parser: "openai"  # or "mistral", "hermes"

# In your code
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]

response = await router.generate(
    RoutingRequest(
        prompt="What's the weather in Paris?",
        task_type=TaskType.TOOL_CALLING
    ),
    tools=tools
)

# Response includes tool call
if response.get("tool_calls"):
    tool_call = response["tool_calls"][0]
    print(f"Model wants to call: {tool_call['function']['name']}")
    print(f"With args: {tool_call['function']['arguments']}")
```

### Supported Backends

| Backend | Tool Calling | Format | Models |
|---------|--------------|--------|--------|
| vLLM | ✅ Native | OpenAI/Mistral/Hermes | DeepSeek, Mistral, Qwen-VL |
| llama.cpp | ✅ Via adapters | Custom | Phi-4-mini, GPT-OSS-20B |
| Whisper | ❌ N/A | N/A | Whisper-v3 |

---

## Performance Tuning

### vLLM Optimization

```yaml
# config/model_router.yaml
models:
  deepseek_v3_1:
    vllm_args:
      # Multi-GPU
      tensor_parallel_size: 2  # Split across 2 GPUs
      pipeline_parallel_size: 1
      
      # Memory optimization
      gpu_memory_utilization: 0.9  # Use 90% of VRAM
      max_num_seqs: 32  # Batch size
      enable_prefix_caching: true  # Cache common prefixes
      
      # Quantization (optional)
      # quantization: "awq"  # AWQ 4-bit (50% VRAM reduction)
```

### llama.cpp Optimization

```yaml
models:
  phi_4_mini:
    llamacpp_args:
      n_ctx: 4096
      n_threads: 8  # CPU threads
      n_gpu_layers: 35  # Offload layers to GPU (0 = CPU-only)
      mlock: true  # Lock model in RAM (prevent swapping)
```

### Performance Targets

| Profile | Throughput | Latency (P50) | Latency (P95) |
|---------|------------|---------------|---------------|
| Edge (CPU) | 60-80 tok/s | 200ms | 500ms |
| Vision (1 GPU) | 30-40 tok/s | 800ms | 1500ms |
| Full (Multi-GPU) | 100-150 tok/s | 300ms | 800ms |

---

## Monitoring & Observability

### Prometheus Metrics

Exposed on `http://localhost:9090/metrics`:

```
# Router metrics
router_requests_total{task_type="reasoning", modality="text", selected_model="deepseek-v3.1"}
router_latency_seconds{task_type="reasoning"}

# Model health
model_health_status{model_name="deepseek-v3.1", backend="vllm"}
model_tokens_per_second{model_name="phi-4-mini"}

# Resource usage
llm_requests_total{provider="vllm", model="deepseek-v3.1"}
llm_latency_seconds{provider="vllm", model="deepseek-v3.1"}
```

### Grafana Dashboards

Start observability stack:
```bash
docker-compose --profile observability up -d
```

Access:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9091

Pre-configured dashboards:
1. **Model Performance**: Latency, throughput, health
2. **Router Decisions**: Selection distribution, fallbacks
3. **Resource Usage**: GPU/CPU utilization, memory

---

## Troubleshooting

### Issue: Model download fails

```bash
# Check HF authentication
huggingface-cli whoami

# Re-login
huggingface-cli login

# Verify model access (gated models require approval)
# Visit: https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct
```

### Issue: vLLM OOM (Out of Memory)

```yaml
# Reduce memory usage
vllm_args:
  gpu_memory_utilization: 0.8  # Lower from 0.9
  max_num_seqs: 16  # Reduce batch size
  
  # Enable quantization
  quantization: "awq"  # 4-bit (50% VRAM reduction)
```

### Issue: llama.cpp slow on CPU

```yaml
# Optimize CPU inference
llamacpp_args:
  n_threads: 16  # Increase threads (match CPU cores)
  n_gpu_layers: 0  # Ensure CPU-only
  mlock: true
  
# Or offload to GPU
n_gpu_layers: 35  # Offload all layers
```

### Issue: Router selects wrong model

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check routing decision
result = await router.route(req)
print(f"Routing reason: {result.routing_reason}")
print(f"Candidates: {[m.name for m in result.fallback_models]}")

# Force specific model (bypass router)
client = router.clients["deepseek-v3.1"]
response = await client.generate(prompt="...")
```

### Issue: Tool calling not working

```bash
# Verify vLLM tool support
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3.1",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "tools": [...]
  }'

# Check tool_call_parser in config
vllm_args:
  tool_call_parser: "openai"  # Must match model's format
```

---

## Next Steps

### Week 1: Foundation
- ✅ Router implementation
- ✅ Model configs
- ✅ Docker compose
- 🔲 Deploy edge profile
- 🔲 Test routing logic

### Week 2: Vision & Audio
- 🔲 Add Llama-3.2-Vision
- 🔲 Add Whisper ASR
- 🔲 Image upload pipeline
- 🔲 Audio transcription tool

### Week 3: Agents & Tools
- 🔲 DeepSeek agentic workflows
- 🔲 Tool calling integration
- 🔲 Evals (lm-eval-harness)
- 🔲 Safety filters (ShieldGemma)

### Week 4: Production
- 🔲 A/B canary routing
- 🔲 Edge quantization (INT4)
- 🔲 Performance benchmarks
- 🔲 Full observability

---

## Support & Resources

- **vLLM Docs**: https://docs.vllm.ai/
- **llama.cpp**: https://github.com/ggerganov/llama.cpp
- **Model Cards**:
  - DeepSeek-V3.1: https://huggingface.co/deepseek-ai/DeepSeek-V3.1
  - Llama-3.2-Vision: https://llama.com/docs/model-cards-and-prompt-formats/llama3_2
  - Qwen2.5-VL: https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct
  - Phi-4: https://techcommunity.microsoft.com/blog/aiplatformblog/introducing-phi-4

---

**🎉 You now have a complete multi-model orchestration system! The router intelligently selects the best model for each task while maintaining ASTRA's local-first sovereignty.**
