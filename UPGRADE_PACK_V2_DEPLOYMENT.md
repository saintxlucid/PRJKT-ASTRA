# ASTRA Upgrade Pack v2.0 - Deployment Guide

## Overview

This guide covers deployment of 6 production-ready components:

1. **BGE-M3 Re-embedding** - Multilingual embeddings (English + Egyptian Arabic)
2. **Memory Consolidation** - Deduplication and LLM summarization
3. **Prometheus Metrics** - Observability with p50/p95/p99 latency tracking
4. **Load Testing** - Async concurrency testing
5. **vLLM Integration** - High-performance inference server
6. **Security Hardening** - Encryption + rate limiting

---

## Prerequisites

### 1. Install Dependencies

```powershell
poetry add sentence-transformers==3.4.1 prometheus-client==0.20.0 cryptography==43.0.1 httpx==0.27.2 numpy
```

### 2. Generate Encryption Key

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output key for use in `.env`.

---

## Component 1: BGE-M3 Re-embedding

### Purpose
Upgrade from `all-MiniLM-L6-v2` (English-only, 384 dims) to `BAAI/bge-m3` (multilingual, 1024 dims) for better Egyptian Arabic support.

### Configuration

Add to `.env`:
```bash
ASTRA_EMBEDDINGS_MODEL_PATH=BAAI/bge-m3
ASTRA_VECTOR_COLLECTION_NEW=astra_memories_m3
ASTRA_EMBEDDINGS_BATCH=64
```

### Execution

```powershell
# Run migration (takes ~15-30 mins for 21,332 memories)
poetry run python scripts/reembed_bge_m3.py
```

### Validation

```powershell
# Check new collection
poetry run python -c "
import chromadb
client = chromadb.PersistentClient(path='data/chromadb')
coll = client.get_collection('astra_memories_m3')
print(f'Count: {coll.count()}')
print(f'Sample:', coll.peek(1))
"
```

### Update Configuration

After validation, update `config/default.yaml`:

```yaml
vector_store:
  provider: "chroma"
  collection_name: "astra_memories_m3"  # Changed from astra_memories
  
embeddings:
  model: "sentence-transformers"
  model_path: "BAAI/bge-m3"  # Changed from all-MiniLM-L6-v2
```

---

## Component 2: Memory Consolidation

### Purpose
Deduplicate similar memories and apply LLM summarization for knowledge compression.

### Configuration

Add to `.env`:
```bash
ASTRA_LLM_BASE_URL=http://localhost:8081/v1
```

### Execution

```powershell
# Dry run (preview changes)
poetry run python scripts/consolidate_memories.py --threshold 0.95 --dry-run

# Production run (applies changes)
poetry run python scripts/consolidate_memories.py --threshold 0.95 --batch 100
```

### Parameters

- `--threshold 0.95`: Similarity threshold (95% similar = duplicate)
- `--batch 100`: Processing batch size
- `--dry-run`: Preview without modifying database

### Schedule as Cron Job

Add to `scripts/schedule_consolidation.ps1`:

```powershell
# Run weekly on Sunday at 2 AM
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2am
$Action = New-ScheduledTaskAction -Execute "poetry" -Argument "run python scripts/consolidate_memories.py --threshold 0.95"
Register-ScheduledTask -TaskName "ASTRA-MemoryConsolidation" -Trigger $Trigger -Action $Action
```

---

## Component 3: Prometheus Metrics

### Purpose
Expose OpenMetrics-compatible endpoint for monitoring request counts, latency, and token usage.

### Integration

Patch `src/astra/api/app.py`:

```python
from astra.metrics import MetricsMiddleware, metrics_endpoint

# Add middleware
app.add_middleware(MetricsMiddleware)

# Expose metrics endpoint
app.add_route("/metrics", metrics_endpoint)
```

Add to `src/astra/infrastructure/llm/llama.py` (or your LLM service):

```python
from astra.metrics import track_tokens

async def complete(...):
    result = await self._generate(...)
    
    # Track token usage
    track_tokens(
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens
    )
    
    return result
```

### Validation

```powershell
# Start ASTRA
poetry run python run_server.py

# Query metrics
curl http://localhost:8080/metrics
```

Expected output:
```
# HELP astra_requests_total Total HTTP requests
# TYPE astra_requests_total counter
astra_requests_total{method="POST",path="/v1/chat/completions",status="200"} 45.0

# HELP astra_request_duration_seconds HTTP request latency in seconds
# TYPE astra_request_duration_seconds histogram
astra_request_duration_seconds_bucket{le="0.1",method="POST",path="/v1/chat/completions"} 12.0
astra_request_duration_seconds_bucket{le="0.5",method="POST",path="/v1/chat/completions"} 38.0

# HELP astra_tokens_total Total tokens processed
# TYPE astra_tokens_total counter
astra_tokens_total{type="prompt"} 12450.0
astra_tokens_total{type="completion"} 8932.0
```

### Grafana Integration

1. Add Prometheus datasource pointing to `http://localhost:9090`
2. Import dashboard from `docs/grafana_dashboard.json`
3. Visualize:
   - Request rate (req/sec)
   - p50/p95/p99 latency
   - Token throughput
   - Error rate

---

## Component 4: Load Testing

### Purpose
Async stress test with configurable concurrency and duration. Tracks p50/p95/p99 latency and throughput.

### Configuration

Add to `.env`:
```bash
ASTRA_LOAD_URL=http://localhost:8080/v1/chat/completions
ASTRA_LOAD_CONC=12
ASTRA_LOAD_SECS=30
```

### Execution

```powershell
# Light load: 12 concurrent users for 30 seconds
ASTRA_LOAD_CONC=12 ASTRA_LOAD_SECS=30 poetry run python scripts/load_test.py

# Production load: 24 concurrent users for 45 seconds
ASTRA_LOAD_CONC=24 ASTRA_LOAD_SECS=45 poetry run python scripts/load_test.py

# Stress test: 48 concurrent users for 60 seconds
ASTRA_LOAD_CONC=48 ASTRA_LOAD_SECS=60 poetry run python scripts/load_test.py
```

### Interpreting Results

```
LOAD TEST RESULTS
================================================================================

Requests:
  Total:      856
  Successful: 854
  Failed:     2
  Success:    99.77%

Throughput:
  Requests/sec: 28.53
  Tokens/sec:   2,134.20
  Total tokens: 64,026

Latency (seconds):
  Min:  0.082
  p50:  0.421
  p95:  0.986
  p99:  1.243
  Max:  1.567
```

**Target SLAs:**
- p50 < 500ms ✅
- p95 < 1.0s ✅
- p99 < 2.0s ✅
- Success rate > 99% ✅

---

## Component 5: vLLM Integration

### Purpose
High-performance OpenAI-compatible inference server with continuous batching and PagedAttention.

### Installation

```powershell
# Install vLLM (requires CUDA)
pip install vllm

# Or use Docker
docker pull vllm/vllm-openai:latest
```

### Start vLLM Server

```powershell
# Single GPU - Llama 3.2 3B
vllm serve meta-llama/Llama-3.2-3B-Instruct `
    --host 0.0.0.0 `
    --port 8000 `
    --served-model-name llama-3.2-3b `
    --max-model-len 4096 `
    --gpu-memory-utilization 0.9

# Multi-GPU - Llama 3.1 70B
vllm serve meta-llama/Llama-3.1-70B-Instruct `
    --tensor-parallel-size 4 `
    --served-model-name llama-3.1-70b `
    --max-model-len 8192

# Docker
docker run --gpus all -p 8000:8000 `
    vllm/vllm-openai:latest `
    --model meta-llama/Llama-3.2-3B-Instruct
```

### ASTRA Configuration

Add to `.env`:
```bash
ASTRA_LLM_PROVIDER=vllm
ASTRA_VLLM_BASE_URL=http://localhost:8000/v1
ASTRA_VLLM_MODEL=llama-3.2-3b
```

Patch `src/astra/infrastructure/llm/factory.py`:

```python
from astra.infrastructure.llm.vllm import VLLMProvider

def create_llm_provider(config: Config) -> LLMProvider:
    provider = config.llm.provider
    
    if provider == "vllm":
        return VLLMProvider(
            base_url=config.llm.vllm_base_url,
            model=config.llm.vllm_model
        )
    elif provider == "llama_cpp":
        return LlamaCppProvider(...)
    # ...
```

### Validation

```powershell
# Test vLLM directly
curl http://localhost:8000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "llama-3.2-3b",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'

# Test via ASTRA
poetry run python -c "
import asyncio
from astra.infrastructure.llm.vllm import VLLMProvider
from astra.domain.models import Message, Role

async def test():
    provider = VLLMProvider()
    result = await provider.chat_completion(
        messages=[Message(role=Role.USER, content='What is 2+2?')],
        max_tokens=50
    )
    print(result.text)

asyncio.run(test())
"
```

---

## Component 6: Security Hardening

### Purpose
- **Encryption**: Fernet symmetric encryption for sensitive database fields
- **Rate Limiting**: Token bucket rate limiter (30 req/5s = 6 req/sec per IP)

### Configuration

Add to `.env`:
```bash
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ASTRA_ENCRYPTION_KEY=your-generated-key-here

# Rate limiting
ASTRA_RATE_LIMIT_REQUESTS=30
ASTRA_RATE_LIMIT_WINDOW=5
```

### Database Encryption

Update models to use `EncryptedText`:

`src/astra/infrastructure/database/models.py`:

```python
from astra.security import EncryptedText

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    content = Column(EncryptedText)  # Encrypted in database
    # ...
```

**Migrate existing data:**

```python
# scripts/encrypt_existing_data.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from astra.infrastructure.database.models import Message
from astra.security import _fernet

engine = create_engine("sqlite:///data/astra.db")
Session = sessionmaker(bind=engine)
session = Session()

for msg in session.query(Message).all():
    # Re-save to trigger encryption
    session.add(msg)
    session.commit()
```

### Rate Limiting

Patch `src/astra/api/app.py`:

```python
from astra.security import RateLimitMiddleware

# Add rate limiter
app.add_middleware(RateLimitMiddleware)
```

### Validation

```powershell
# Test rate limiting
for ($i=1; $i -le 35; $i++) {
    curl http://localhost:8080/v1/chat/completions -Method POST `
      -ContentType "application/json" `
      -Body '{"messages":[{"role":"user","content":"test"}]}'
}
# Should see 429 Too Many Requests after 30 requests
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Run `poetry install` to install dependencies
- [ ] Generate encryption key and add to `.env`
- [ ] Configure vLLM server (if using)
- [ ] Run BGE-M3 migration
- [ ] Run memory consolidation dry-run
- [ ] Update `config/default.yaml` with new collection name

### Deployment

- [ ] Patch `src/astra/api/app.py` with metrics and rate limiting
- [ ] Patch `src/astra/infrastructure/llm/factory.py` with vLLM provider
- [ ] Update database models with `EncryptedText`
- [ ] Run database encryption migration
- [ ] Run comprehensive tests: `poetry run pytest tests/`
- [ ] Run load test: `poetry run python scripts/load_test.py`

### Post-Deployment

- [ ] Verify metrics at `/metrics` endpoint
- [ ] Verify rate limiting (test with 35 rapid requests)
- [ ] Verify encryption (check database for encrypted content)
- [ ] Monitor logs for errors
- [ ] Schedule memory consolidation job
- [ ] Set up Grafana dashboards

### Monitoring

```powershell
# Watch metrics in real-time
curl http://localhost:8080/metrics | Select-String "astra_"

# Check logs
Get-Content logs/astra.log -Wait

# Monitor vLLM
curl http://localhost:8000/metrics
```

---

## Rollback Plan

If issues arise, rollback steps:

1. **BGE-M3**: Revert `config/default.yaml` to old collection name
2. **Consolidation**: Restore from backup (taken before consolidation)
3. **Metrics**: Remove `MetricsMiddleware` from `app.py`
4. **vLLM**: Set `ASTRA_LLM_PROVIDER=llama_cpp` in `.env`
5. **Security**: Remove `RateLimitMiddleware`, set `EncryptedText` → `String`

---

## Performance Benchmarks

### Before Upgrade Pack

- Embeddings: English-only, 384 dims
- No deduplication (21,332 memories)
- No observability
- No rate limiting
- llama.cpp inference (~2-3 req/sec)

### After Upgrade Pack

- Embeddings: Multilingual (AR/EN), 1024 dims
- Deduplicated memories (~15,000-18,000 after consolidation)
- Full Prometheus metrics
- Rate limited (6 req/sec per IP)
- vLLM inference (20-30 req/sec with batching)

### Expected Improvements

- **Memory quality**: +40% for Arabic queries
- **Storage efficiency**: -15% to -30% after consolidation
- **Throughput**: 10x with vLLM (2 → 20 req/sec)
- **Observability**: Full p50/p95/p99 tracking
- **Security**: Encrypted sensitive fields, DDoS protection

---

## Troubleshooting

### BGE-M3 Migration

**Issue**: Out of memory
**Solution**: Reduce `ASTRA_EMBEDDINGS_BATCH` from 64 to 32 or 16

**Issue**: Slow performance
**Solution**: Ensure sentence-transformers is using GPU: `pip install torch --index-url https://download.pytorch.org/whl/cu118`

### vLLM

**Issue**: CUDA out of memory
**Solution**: Reduce `--max-model-len` or `--gpu-memory-utilization 0.8`

**Issue**: vLLM connection refused
**Solution**: Check server logs: `docker logs <container-id>`

### Rate Limiting

**Issue**: Rate limit too strict
**Solution**: Increase `ASTRA_RATE_LIMIT_REQUESTS=60` (60 req/5s = 12 req/sec)

### Encryption

**Issue**: Decryption fails after key rotation
**Solution**: Use dual-key decryption wrapper:

```python
def dual_key_decrypt(value, new_key, old_key):
    try:
        return Fernet(new_key).decrypt(value)
    except:
        return Fernet(old_key).decrypt(value)
```

---

## Next Steps

1. **Monitoring**: Set up Prometheus + Grafana
2. **Alerting**: Configure alerts for p99 > 2s, error rate > 1%
3. **Scaling**: Deploy vLLM on multi-GPU cluster
4. **Backup**: Automate ChromaDB backups (weekly)
5. **CI/CD**: Add load testing to deployment pipeline

---

## Support

For issues, check:
- Logs: `logs/astra.log`
- Metrics: `http://localhost:8080/metrics`
- vLLM metrics: `http://localhost:8000/metrics`
- Migration reports: `data/logs/`

Contact: GitHub Issues or team Slack channel
