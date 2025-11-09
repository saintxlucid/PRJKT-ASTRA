# ASTRA Production Enhancements - Implementation Guide

**Date**: October 9, 2025  
**Status**: Implementation Phase  
**Priority**: HIGH

---

## Overview

This document outlines comprehensive enhancements to transform ASTRA from working prototype to production-grade system. Based on expert recommendations, we're implementing improvements across 7 key areas.

---

## 1. GPT-OSS Gibberish Fix Playbook ✅

### Problem
GPT-OSS-20B produces gibberish output due to:
- Chat template mismatch
- Improper sampling parameters
- Stop token issues
- Tokenizer misalignment

### Solution Implemented

#### A. Gibberish Triage Script ✅
**File**: `scripts/gibberish_triage.py` (600+ lines)

**Features**:
- Tests 6 parameter grids systematically
- Calculates bad-token rate and repetition score
- Provides quality scores (0-100)
- Generates actionable recommendations
- Exports JSON results for analysis

**Usage**:
```powershell
# Full triage (all prompts, all configs)
python scripts\gibberish_triage.py --model gpt-oss-20b

# Quick test (2 prompts only)
python scripts\gibberish_triage.py --quick

# Custom output location
python scripts\gibberish_triage.py --output results\triage.json
```

**Parameter Grids Tested**:
1. **very_conservative**: temp=0.5, top_p=0.85, top_k=30, rep_penalty=1.05
2. **conservative**: temp=0.6, top_p=0.9, top_k=40, rep_penalty=1.1
3. **balanced**: temp=0.7, top_p=0.9, top_k=80, rep_penalty=1.15
4. **creative**: temp=0.8, top_p=0.95, top_k=100, rep_penalty=1.2
5. **high_repetition_penalty**: temp=0.7, top_p=0.9, top_k=60, rep_penalty=1.3
6. **long_context**: temp=0.6, top_p=0.88, top_k=50, rep_penalty=1.12

**Test Prompts**:
- "What is 2+2?" (simple factual)
- "Explain quantum entanglement in simple terms." (complex explanation)
- "Write a haiku about AI." (creative)
- "Key principles of OOP?" (technical)
- "Describe the water cycle." (educational)

**Output Analysis**:
```json
{
  "best_configuration": {
    "name": "conservative",
    "average_quality": 85.3
  },
  "recommendations": [
    "✅ Good quality found with best configuration",
    "⚠️ High repetition detected - increase penalty to 1.2-1.3"
  ]
}
```

#### B. Sampling Configuration Module ✅
**File**: `src/astra/infrastructure/llm/sampling.py` (400+ lines)

**Features**:
- 6 battle-tested sampling presets
- Parameter validation with warnings
- Stop token management for all formats
- Preset recommendations by use case

**Presets**:
```python
from astra.infrastructure.llm.sampling import SamplingConfigFactory, SamplingPreset

# Get conservative preset
params = SamplingConfigFactory.create(SamplingPreset.CONSERVATIVE)

# Override specific parameters
params = SamplingConfigFactory.create(
    SamplingPreset.BALANCED,
    temperature=0.65
)

# Get parameters for reasoning mode
params = SamplingConfigFactory.for_reasoning_mode("medium")
```

**Stop Token Management**:
```python
from astra.infrastructure.llm.sampling import StopTokenManager

# Harmony format stop tokens
harmony_stops = StopTokenManager.get_stop_tokens("harmony")

# Simple format stop tokens
simple_stops = StopTokenManager.get_stop_tokens("simple")

# With custom channel
final_stops = StopTokenManager.get_stop_tokens("harmony", channel="final")
```

---

## 2. Harmony Format Validation & Testing ✅

### Round-Trip Unit Tests ✅
**File**: `tests/unit/test_harmony_roundtrip.py` (500+ lines)

**Test Coverage**:
- ✅ Build and parse simple conversations
- ✅ Parse responses with analysis channel
- ✅ Parse responses without channels
- ✅ Strip CoT from history
- ✅ Convert to OpenAI format
- ✅ Multi-turn conversations
- ✅ Schema guards (analysis bleed detection)
- ✅ Missing final channel handling
- ✅ Malformed headers
- ✅ Empty channels
- ✅ Stop token enforcement
- ✅ Channel switch detection
- ✅ Multiple assistant turns prevention
- ✅ Channel isolation
- ✅ Memory safety (no analysis in storage)
- ✅ Logging redaction
- ✅ API response format
- ✅ Empty context fallbacks
- ✅ Header sequencing
- ✅ Role hierarchy
- ✅ Alternating user/assistant pattern
- ✅ Full integration with mock LLM
- ✅ Retry on analysis bleed

**Run Tests**:
```powershell
# Run all Harmony tests
pytest tests\unit\test_harmony_roundtrip.py -v

# Run specific test class
pytest tests\unit\test_harmony_roundtrip.py::TestHarmonyRoundTrip -v

# With coverage
pytest tests\unit\test_harmony_roundtrip.py --cov=src.astra.infrastructure.llm.harmony
```

---

## 3. Backend Hosting Configuration

### Current Setup (llama.cpp)
- ✅ Works with GGUF models
- ✅ Fast inference
- ✅ Already wired into ASTRA

### Operational Parameters (Recommended)

**llama.cpp server startup**:
```powershell
.\llama-server.exe `
    --model gpt-oss-20b.Q4_K_M.gguf `
    --port 8001 `
    --threads 8 `              # Physical cores
    --batch-size 512 `         # Start modest
    --ctx-size 8192 `          # Start at 8k
    --n-gpu-layers 32 `        # Max for your VRAM
    --rope-scaling yarn `      # For >8k context
    --rope-freq-base 10000 `
    --rope-freq-scale 1.0 `
    --verbose
```

**Key Settings**:
- **Threads**: Set to physical CPU cores (not hyperthreaded)
- **Batch Size**: 32-64 for CPU, 512+ for GPU
- **Context**: Start at 8k, verify quality, then scale to 16k/32k
- **GPU Layers**: As high as VRAM allows
- **RoPE**: Required for extending beyond base context

### Future: vLLM Integration (Phase 2)

**When to Switch**:
- Need higher throughput (>10 concurrent users)
- Ready to convert to AWQ/GPTQ safetensors
- Want production-grade batching

**Architecture**:
```
FastAPI Backend
├── LLM Provider (Abstract)
│   ├── LlamaCppProvider (GGUF) ← Current
│   └── vLLMProvider (Safetensors) ← Future
└── Provider Factory (selects based on config)
```

**Benefits**:
- 2-3x higher throughput
- Better batching
- Continuous batching
- PagedAttention for longer contexts

---

## 4. Memory & Retrieval Upgrades

### Current State
- ✅ 21,332 memories in ChromaDB
- ✅ Sentence-transformers embeddings (all-MiniLM-L6-v2)
- ✅ Semantic search working
- ⚠️ English-only embeddings (Egyptian Arabic not supported)

### Planned Upgrades

#### A. Multilingual Embeddings (BGE-M3)

**Why**:
- Saint Lucid writes in English + Egyptian Arabic
- Current embeddings (all-MiniLM-L6-v2) are English-only
- BGE-M3 supports 100+ languages with high quality

**Implementation**:
1. Install BGE-M3:
```powershell
pip install FlagEmbedding
```

2. Create migration script:
```python
from FlagEmbedding import BGEM3FlagModel

# Load new model
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# Re-embed all memories
for memory in memories:
    new_embedding = model.encode(memory.content)['dense_vecs']
    update_memory_embedding(memory.id, new_embedding)
```

3. Update VectorStore to use BGE-M3

**Migration Script**: `scripts/migrate_to_bge_m3.py` (TODO)

#### B. Memory Consolidation System

**Goals**:
- Deduplicate similar memories
- Compress old memories into summaries
- Add recency boost to scoring
- Implement shingled chunking

**Nightly Job** (TODO):
```python
# Pseudo-code
def consolidate_memories():
    # 1. Find near-duplicates (cosine similarity > 0.95)
    duplicates = find_near_duplicates(threshold=0.95)
    merge_duplicates(duplicates)
    
    # 2. Compress old, low-importance memories
    old_memories = get_memories(age > 90_days, importance < 5)
    summaries = summarize_batch(old_memories)
    replace_with_summaries(old_memories, summaries)
    
    # 3. Re-index with recency boost
    reindex_with_time_decay()
```

**Chunking Strategy**:
- Chunk size: 200-400 tokens
- Overlap: 50-100 tokens
- Store chunk metadata (source, position)

**Recency Boost**:
```python
final_score = similarity_score * (1 + recency_weight * time_decay)
time_decay = exp(-age_days / 30)  # Decay over ~30 days
```

#### C. Retrieval Features

**Store with each message**:
```python
@dataclass
class MessageMetadata:
    retrieved_memory_ids: List[str]
    similarity_scores: List[float]
    retrieval_query: str
    num_memories_considered: int
```

**Benefits**:
- A/B test RAG policies
- Debug retrieval issues
- Understand why ASTRA said something

---

## 5. Security & Operations Hardening

### Security Enhancements (TODO)

#### A. Per-Conversation Encryption
```python
from cryptography.fernet import Fernet

class EncryptedConversationService:
    def encrypt_message(self, content: str, conv_id: str) -> str:
        key = self.get_conversation_key(conv_id)
        fernet = Fernet(key)
        return fernet.encrypt(content.encode()).decode()
    
    def decrypt_message(self, encrypted: str, conv_id: str) -> str:
        key = self.get_conversation_key(conv_id)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted.encode()).decode()
```

**Implementation**: Store keys in secure key store, never in .env

#### B. Rate Limiting
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/v1/chat/")
@limiter.limit("10/minute")  # Per IP
async def chat(request: ChatRequest):
    ...
```

**Limits**:
- Chat: 10 requests/minute per IP
- Conversations: 20 requests/minute per IP
- System: Unlimited (health checks)

#### C. Tool Sandboxing
```python
# For Playwright
async def safe_navigate(url: str, timeout: int = 30):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent='ASTRA/2.0',
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=False,
            java_script_enabled=True,
            accept_downloads=False,  # No downloads
        )
        page = await context.new_page()
        
        # Set resource limits
        await page.set_default_timeout(timeout * 1000)
        
        # Navigate with timeout
        try:
            await page.goto(url, wait_until='domcontentloaded')
            content = await page.content()
            return content
        finally:
            await browser.close()
```

**Disk Quotas**:
- Temp directory: Max 100MB per tool execution
- Auto-cleanup after 1 hour

---

## 6. Operational Monitoring

### Prometheus Metrics Export (TODO)

**File**: `src/astra/utils/metrics.py`

**Metrics to Track**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
chat_requests_total = Counter(
    'astra_chat_requests_total',
    'Total chat requests',
    ['status', 'reasoning_mode']
)

chat_duration_seconds = Histogram(
    'astra_chat_duration_seconds',
    'Chat request duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Token metrics
tokens_generated_total = Counter(
    'astra_tokens_generated_total',
    'Total tokens generated'
)

tokens_per_second = Gauge(
    'astra_tokens_per_second',
    'Current tokens per second'
)

# Memory metrics
memory_retrievals_total = Counter(
    'astra_memory_retrievals_total',
    'Total memory retrievals'
)

memory_cache_hits = Counter(
    'astra_memory_cache_hits_total',
    'Memory cache hits'
)

# Queue metrics
request_queue_depth = Gauge(
    'astra_request_queue_depth',
    'Current request queue depth'
)

# Resource metrics
cpu_usage_percent = Gauge(
    'astra_cpu_usage_percent',
    'CPU usage percentage'
)

vram_usage_bytes = Gauge(
    'astra_vram_usage_bytes',
    'VRAM usage in bytes'
)
```

**Metrics Endpoint**:
```python
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

**Grafana Dashboard**:
- Create dashboard in `docs/grafana/astra-dashboard.json`
- Panels for: requests/sec, p99 latency, tokens/sec, memory hit rate, VRAM usage

---

## 7. Comprehensive Testing Suite

### Tests to Add (TODO)

#### A. Concurrency E2E Test
**File**: `tests/e2e/test_concurrency.py`

```python
@pytest.mark.asyncio
async def test_32_parallel_chats():
    """Test 32 concurrent chat requests with RAG + tools"""
    async with httpx.AsyncClient() as client:
        # Create 32 conversations
        conversations = [
            await client.post("/v1/conversations/")
            for _ in range(32)
        ]
        
        # Send 32 parallel chat requests
        tasks = [
            client.post(
                "/v1/chat/",
                json={
                    "conversation_id": conv["id"],
                    "message": f"Test message {i}",
                    "use_memory": True,
                }
            )
            for i, conv in enumerate(conversations)
        ]
        
        start = time.time()
        responses = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        # Assertions
        assert all(r.status_code == 200 for r in responses)
        assert duration < 60  # All complete in 60s
        
        # Calculate percentiles
        latencies = [r.elapsed.total_seconds() for r in responses]
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        
        print(f"P50: {p50:.2f}s, P95: {p95:.2f}s, P99: {p99:.2f}s")
        
        assert p99 < 30  # p99 under 30s
```

#### B. Template Drift Test
**File**: `tests/e2e/test_template_drift.py`

```python
def test_template_drift_detection():
    """Alert if prompt templates change response quality"""
    templates = [
        "template_v1.txt",
        "template_v2.txt",
        "template_v3.txt",
    ]
    
    baseline_answers = load_baseline_answers()
    
    for template in templates:
        answers = generate_answers_with_template(template)
        
        # Calculate BLEU/ROUGE scores
        bleu_scores = [
            sentence_bleu([baseline], answer)
            for baseline, answer in zip(baseline_answers, answers)
        ]
        
        avg_bleu = np.mean(bleu_scores)
        
        # Alert if drift > 20%
        assert avg_bleu > 0.8, f"Template {template} has significant drift"
```

#### C. Retrieval Attribution Test
**File**: `tests/unit/test_retrieval_attribution.py`

```python
def test_memory_appears_in_answer():
    """Verify retrieved memories appear in final answer"""
    # Query that requires memory
    query = "What did I ask you yesterday about quantum physics?"
    
    # Get top-K memories
    memories = memory_service.search(query, top_k=5)
    
    # Generate answer
    answer = chat_service.chat(query, use_memory=True)
    
    # Check attribution
    memory_appeared = any(
        memory.content[:50] in answer
        for memory in memories
    )
    
    assert memory_appeared, "No retrieved memory appeared in answer"
```

---

## 8. Plugin System Architecture (TODO)

### 3-Method Contract

**File**: `src/astra/plugins/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    capabilities: List[str]
    requires: List[str]  # Dependencies

class Plugin(ABC):
    """Base plugin class - all plugins must implement these 3 methods"""
    
    @abstractmethod
    def describe(self) -> PluginMetadata:
        """
        Describe plugin capabilities and metadata.
        
        Returns:
            PluginMetadata with name, version, capabilities, etc.
        """
        pass
    
    @abstractmethod
    async def invoke(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Invoke plugin action with parameters.
        
        Args:
            action: Action name (e.g., "search", "translate")
            params: Action parameters
            
        Returns:
            Action result
            
        Raises:
            PluginError: If action fails
        """
        pass
    
    @abstractmethod
    async def auth(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        """
        Authenticate plugin (if required).
        
        Args:
            credentials: Optional credentials dict
            
        Returns:
            True if authenticated, False otherwise
        """
        pass
```

**Example Plugin**:
```python
class WeatherPlugin(Plugin):
    def describe(self) -> PluginMetadata:
        return PluginMetadata(
            name="weather",
            version="1.0.0",
            author="ASTRA Team",
            description="Get weather information",
            capabilities=["get_weather", "get_forecast"],
            requires=["httpx"],
        )
    
    async def invoke(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "get_weather":
            location = params.get("location")
            return await self._fetch_weather(location)
        else:
            raise PluginError(f"Unknown action: {action}")
    
    async def auth(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        # Check API key if required
        if credentials and "api_key" in credentials:
            self.api_key = credentials["api_key"]
            return True
        return False
```

**Plugin Registry**:
```python
class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
    
    def register(self, plugin: Plugin):
        metadata = plugin.describe()
        self.plugins[metadata.name] = plugin
    
    async def invoke_plugin(self, name: str, action: str, params: Dict):
        if name not in self.plugins:
            raise PluginError(f"Plugin not found: {name}")
        
        plugin = self.plugins[name]
        return await plugin.invoke(action, params)
```

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1) ✅
- [x] Gibberish triage script
- [x] Sampling configuration module
- [x] Harmony format unit tests
- [ ] Stop token enforcement in LlamaCppProvider
- [ ] Update ChatService to use sampling presets

### Phase 2: Memory Upgrades (Week 2)
- [ ] BGE-M3 migration script
- [ ] Re-embed 21,332 memories
- [ ] Memory consolidation job
- [ ] Shingled chunking
- [ ] Recency boost implementation

### Phase 3: Monitoring & Security (Week 3)
- [ ] Prometheus metrics
- [ ] Rate limiting
- [ ] Tool sandboxing
- [ ] Per-conversation encryption

### Phase 4: Testing & Validation (Week 4)
- [ ] Concurrency e2e tests
- [ ] Template drift tests
- [ ] Retrieval attribution tests
- [ ] Load testing

### Phase 5: Plugin System (Week 5)
- [ ] Plugin base classes
- [ ] Plugin registry
- [ ] Example plugins (weather, calculator)
- [ ] Plugin documentation

### Phase 6: vLLM Integration (Week 6)
- [ ] Convert GPT-OSS to AWQ/GPTQ
- [ ] vLLMProvider implementation
- [ ] Benchmark comparison
- [ ] Production deployment

---

## Quick Reference

### Run Gibberish Triage
```powershell
python scripts\gibberish_triage.py --model gpt-oss-20b
```

### Run Harmony Tests
```powershell
pytest tests\unit\test_harmony_roundtrip.py -v
```

### Use Sampling Presets
```python
from astra.infrastructure.llm.sampling import (
    SamplingConfigFactory,
    SamplingPreset,
    StopTokenManager
)

# Get conservative preset
params = SamplingConfigFactory.create(SamplingPreset.CONSERVATIVE)

# Get stop tokens for Harmony
stops = StopTokenManager.get_stop_tokens("harmony", channel="final")
```

### Check System Health
```powershell
curl http://localhost:8080/v1/system/health
```

---

## Notes

1. **Priority**: Fix gibberish first, then memory, then monitoring
2. **Testing**: Test each change with gibberish triage script
3. **Documentation**: Update docs as you implement
4. **Backwards Compatibility**: Keep simple format working alongside Harmony
5. **Performance**: Profile before and after each optimization

---

*Last Updated: October 9, 2025*  
*Status: Implementation In Progress*
