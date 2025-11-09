# 🚀 ASTRA CORE v1.0.0 - POST-LAUNCH ROADMAP

**Launch Date:** October 16, 2025  
**Current Status:** 🟢 Production Live - All Systems Operational  
**Roadmap Timeline:** T+0 → Month-1

---

## 📊 **T+0 → T+48 HOURS: STABILIZATION**

### **Golden Signal Monitoring**

**Watch Schedule:**
- **First 30 minutes:** Continuous monitoring
- **T+30min → T+2h:** Every 15 minutes
- **T+2h → T+48h:** Hourly checks

**Monitoring Commands:**
```powershell
# Quick health check (every check)
.\scripts\day0_watch.ps1

# Detailed metrics check (hourly)
curl http://127.0.0.1:8080/metrics | Select-String "astra_llm_latency_seconds"
curl http://127.0.0.1:8080/metrics | Select-String "astra_cache"
curl http://127.0.0.1:8080/metrics | Select-String "astra_circuit_breaker"
```

**Success Criteria:**
- ✅ **p95 latency:** ≤ 1.2s sustained
- ✅ **p99 latency:** ≤ 2.0s sustained
- ✅ **Cache hit:** 10% (cold) → 25-30% (warm by T+48h)
- ✅ **Breaker:** CLOSED (quiet, no sustained trips)
- ✅ **Error rate:** < 1%
- ✅ **Uptime:** > 99% over 48h

---

### **1. Tag & Lock Release** (After T+30min stable)

```powershell
# Tag production release
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 – Production Ready"
git push origin v1.0.0

# Set CI coverage gate (≥94% for all future PRs)
# Update CI configuration
notepad .github/workflows/ci.yml
# Add: --cov-fail-under=94
```

**CI Configuration Update:**
```yaml
# .github/workflows/ci.yml (if using GitHub Actions)
- name: Run Tests with Coverage
  run: |
    pytest tests/ -v --cov=src/astra --cov-report=xml --cov-fail-under=94
```

**Acceptance:**
- ✅ v1.0.0 tag pushed to origin
- ✅ CI gate set to ≥94% coverage
- ✅ Future PRs will fail if coverage drops

---

### **2. Close Test Gap: 46/49 → 49/49** (Priority 1)

**Current Failures:**
1. Time-based test failures (flaky timing)
2. Rate-limit test environment dependencies
3. Bridge import path stability

**Fix Strategy:**

#### **A. Time-Based Test Fixes**
```python
# tests/conftest.py or relevant test files
import pytest
from unittest.mock import patch
from datetime import datetime, timezone

@pytest.fixture
def freeze_time():
    """Freeze time for deterministic tests"""
    frozen_time = datetime(2025, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = frozen_time
        mock_datetime.utcnow.return_value = frozen_time
        yield frozen_time

# Usage in tests:
def test_time_sensitive_operation(freeze_time):
    # Time is now frozen, test will be deterministic
    result = function_that_uses_time()
    assert result.timestamp == freeze_time
```

#### **B. Rate-Limit Test Overrides**
```python
# tests/test_rate_limiting.py
@pytest.fixture
def test_rate_limit_config():
    """Override rate limits for testing"""
    with patch.dict(os.environ, {
        'ASTRA_RATE_LIMIT_REQUESTS': '1000',  # High limit for tests
        'ASTRA_RATE_LIMIT_WINDOW': '1'
    }):
        yield

def test_rate_limiting(test_rate_limit_config):
    # Test with overridden limits
    pass
```

#### **C. Bridge Import Stability**
```python
# Ensure consistent import paths
# tests/test_bridge.py
import sys
from pathlib import Path

# Add src to path if needed
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from astra.bridge import BridgeManager  # Now stable
```

**Execution Plan:**
```powershell
# 1. Identify failing tests
pytest tests/ -v --tb=short | Select-String "FAILED"

# 2. Fix tests iteratively
# Edit test files with fixes above

# 3. Verify fixes
pytest tests/ -v --cov=src/astra --cov-report=term-missing

# 4. Ensure 49/49 passing
pytest tests/ -v --cov=src/astra --cov-fail-under=94
```

**Acceptance:**
- ✅ All 49/49 tests passing
- ✅ Coverage ≥ 94%
- ✅ No flaky tests in 10 consecutive runs
- ✅ CI gate enforced

---

### **3. Snapshot & Restore Drill** (15 minutes)

**Purpose:** Verify backup/restore procedures work correctly

#### **Step 1: Create Backup**
```powershell
# Create backup script if not exists
# scripts/backup_production.ps1 already exists

# Run backup
.\scripts\backup_production.ps1

# Expected output:
# - data/database/astra.db → backup/YYYYMMDD_HHMMSS/
# - data/chromadb/ → backup/YYYYMMDD_HHMMSS/chromadb/
# - .env → backup/YYYYMMDD_HHMMSS/.env.backup
```

#### **Step 2: Restore to Temp Directory**
```powershell
# Create temp restore location
$tempRestore = "X:\TEMP_RESTORE_TEST"
New-Item -ItemType Directory -Path $tempRestore -Force

# Find latest backup
$latestBackup = Get-ChildItem ".\backup" | Sort-Object Name -Descending | Select-Object -First 1

# Restore files
Copy-Item "$($latestBackup.FullName)\*" -Destination $tempRestore -Recurse

# Verify contents
Get-ChildItem $tempRestore -Recurse | Measure-Object | Select-Object Count
```

#### **Step 3: Boot Test with Restored Data**
```powershell
# Update temp .env to point to restored DB
$tempEnv = Get-Content "$tempRestore\.env.backup"
$tempEnv = $tempEnv -replace "DATABASE_URL=.*", "DATABASE_URL=sqlite:///$tempRestore/astra.db"
$tempEnv | Set-Content "$tempRestore\.env.test"

# Test DB connectivity
& "X:/PROJECT_ASTRA_1.0 (ASTRA_CORE)/.venv/Scripts/python.exe" -c @"
import sqlite3
conn = sqlite3.connect('$tempRestore/astra.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM conversations')
count = cursor.fetchone()[0]
print(f'Conversations restored: {count}')
conn.close()
"@

# Cleanup temp
Remove-Item $tempRestore -Recurse -Force
```

**Acceptance:**
- ✅ Backup archive created successfully
- ✅ All critical files present in backup
- ✅ Restored database is readable
- ✅ Conversation count matches production
- ✅ ChromaDB collections intact

---

## 🔧 **DAYS 2-7: HARDENING + PERFORMANCE**

### **4. BGE-M3 Migration** (After 48h stable)

**Prerequisites:**
- ✅ System stable for 48+ hours
- ✅ 2GB+ free disk space
- ✅ No active incidents

#### **Phase 1: Dual Collection Setup**
```powershell
# Check disk space
Get-PSDrive X | Select-Object Used, Free

# Run BGE-M3 re-embedding (keeps MiniLM as fallback)
python scripts/reembed_bge_m3.py --migrate --dual-collection

# Expected output:
# - New collection: astra_memories_m3 (1536d embeddings)
# - Old collection: astra_memory (384d embeddings, preserved)
```

#### **Phase 2: A/B Testing (24 hours)**
```python
# src/astra/infrastructure/storage/vector_store.py
# Add A/B split logic

import random

class VectorStore:
    def __init__(self, config):
        self.collection_minilm = chroma_client.get_collection("astra_memory")
        self.collection_m3 = chroma_client.get_collection("astra_memories_m3")
        self.ab_split = 0.5  # 50/50 split
        
    def search(self, query, top_k=5):
        # A/B split
        use_m3 = random.random() < self.ab_split
        collection = self.collection_m3 if use_m3 else self.collection_minilm
        
        # Track which collection was used
        metrics.counter("vector_search_collection", 
                       {"collection": "m3" if use_m3 else "minilm"}).inc()
        
        # Perform search
        results = collection.query(query, n_results=top_k)
        
        # Track metrics
        metrics.histogram("vector_search_latency",
                         {"collection": "m3" if use_m3 else "minilm"})
        
        return results
```

#### **Phase 3: Metrics Analysis**
```powershell
# After 24 hours, compare metrics
curl http://127.0.0.1:8080/metrics | Select-String "vector_search"

# Analyze:
# - Precision@5: User feedback, relevance scores
# - Latency: p50, p95, p99 for both collections
# - Hit rate: Cache effectiveness with each collection
```

**Success Criteria:**
- ✅ **Relevance:** +15-20% improvement (measured via feedback)
- ✅ **Latency:** ≤10% increase over baseline
- ✅ **No regressions:** Error rates unchanged
- ✅ **Cache:** Hit rate maintained or improved

#### **Phase 4: Switch Default**
```python
# If success criteria met, switch default
# src/astra/config.py
ASTRA_EMBEDDINGS_MODEL = "BAAI/bge-m3-v2"  # Switch from MiniLM
ASTRA_EMBEDDINGS_DIM = 1536  # Update dimension
ASTRA_VECTOR_COLLECTION = "astra_memories_m3"  # Default collection
```

**Rollback Plan:**
```python
# If issues, instant rollback to MiniLM
ASTRA_VECTOR_COLLECTION = "astra_memory"
# Restart API server
```

---

### **5. Cache Tuning**

#### **Current State:**
```powershell
# Check current cache settings
Get-Content .env | Select-String "CACHE"
# ASTRA_CACHE_TTL_SECONDS=600  # 10 minutes (default)
# ASTRA_CACHE_MAX_SIZE=1000
```

#### **Optimization Strategy:**
```powershell
# Phase 1: Increase TTL to 15 minutes
notepad .env
# Change: ASTRA_CACHE_TTL_SECONDS=900

# Restart API
.\scripts\stop.ps1
.\scripts\ship.ps1

# Monitor for 24 hours
.\scripts\day0_watch.ps1
```

#### **Add Cache Metrics** (if not present)
```python
# src/astra/services/memory_service.py
from prometheus_client import Counter

# Add missing metrics
cache_miss_total = Counter(
    'astra_memory_cache_miss_total',
    'Total number of cache misses'
)

ttl_expired_total = Counter(
    'astra_memory_cache_ttl_expired_total',
    'Total number of cache entries expired by TTL'
)

# Instrument cache operations
def get_from_cache(self, key):
    if key in self.cache:
        if self._is_expired(key):
            ttl_expired_total.inc()
            del self.cache[key]
            cache_miss_total.inc()
            return None
        return self.cache[key]
    cache_miss_total.inc()
    return None
```

**Target Metrics:**
- ✅ **Cache hit rate:** ≥30% sustained
- ✅ **TTL expired:** <20% of total cache operations
- ✅ **Cache miss:** Decreasing trend over time
- ✅ **Stale complaints:** Zero user reports

**Tuning Parameters:**
| Metric | Current | Target | Action |
|--------|---------|--------|--------|
| TTL | 600s | 900-1800s | Increase gradually |
| Max Size | 1000 | 2000 | Double if hit rate high |
| Eviction | LRU | LRU | Keep current |

---

### **6. Service Mode Rollout** (Optional)

**Purpose:** Auto-start ASTRA on system boot with automatic recovery

#### **Step 1: Install Service Wrapper**
```powershell
# Use existing service wrapper
.\ops\service_wrapper.ps1 -Action Install

# Expected services:
# - ASTRA-LLM-Server (llama.cpp)
# - ASTRA-API-Server (FastAPI/Uvicorn)
```

#### **Step 2: Configure Auto-Restart**
```powershell
# Set recovery options
sc.exe failure ASTRA-LLM-Server reset= 86400 actions= restart/60000/restart/60000/restart/60000
sc.exe failure ASTRA-API-Server reset= 86400 actions= restart/60000/restart/60000/restart/60000

# Verify configuration
sc.exe qfailure ASTRA-LLM-Server
sc.exe qfailure ASTRA-API-Server
```

#### **Step 3: Reboot Test**
```powershell
# Graceful restart
Restart-Computer -Force

# After reboot, verify services
Start-Sleep -Seconds 60
Get-Service | Where-Object {$_.Name -like "ASTRA-*"}

# Health checks
.\scripts\day0_watch.ps1
```

**Acceptance:**
- ✅ Services start automatically on boot
- ✅ Health checks pass within 2 minutes
- ✅ Services restart automatically on failure
- ✅ Logs show clean startup sequence

---

### **7. WAL Hygiene**

#### **Schedule Weekly Checkpoint**
```powershell
# Schedule WAL checkpoint (Sundays 02:00)
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\scripts\wal_checkpoint.py" `
    -WorkingDirectory "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2:00AM

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask -TaskName "ASTRA-WAL-Checkpoint" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Weekly WAL checkpoint for ASTRA database"

# Verify task
Get-ScheduledTask | Where-Object {$_.TaskName -eq "ASTRA-WAL-Checkpoint"}
```

#### **Log Rotation Setup**
```powershell
# Add log rotation to checkpoint script
# scripts/wal_checkpoint.py should include:
# - Archive logs older than 7 days
# - Compress archived logs
# - Keep last 4 weeks of archives
```

**Monitoring:**
```powershell
# Check WAL size weekly
Get-ChildItem ".\data\database" -Filter "*-wal" | Select-Object Name, Length

# Verify no lock errors
Get-Content .\data\logs\astra.log | Select-String "database is locked"
```

**Acceptance:**
- ✅ WAL checkpoint scheduled and running
- ✅ WAL size bounded (< 100MB typical)
- ✅ No "database is locked" events for 7+ days
- ✅ Logs rotated and archived automatically

---

## 🚀 **WEEKS 2-4: PHASE-2 FEATURES**

### **8. Semantic Cache Enhancement**

**Current:** Header-level cache stub  
**Target:** Full response + tool-aware caching

```python
# src/astra/services/cache_service.py
import hashlib
import json

class SemanticCache:
    def generate_cache_key(self, prompt, memory_ids, settings):
        """
        Generate cache key from prompt + context + settings
        """
        key_data = {
            'prompt': prompt,
            'memory_ids': sorted(memory_ids),  # Top-k memory IDs
            'temperature': settings.get('temperature'),
            'max_tokens': settings.get('max_tokens'),
            'model': settings.get('model')
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def cache_response(self, key, response, tool_calls=None):
        """
        Cache complete response including tool calls
        """
        cache_entry = {
            'response': response,
            'tool_calls': tool_calls or [],
            'timestamp': datetime.utcnow(),
            'ttl': self.ttl
        }
        self.cache[key] = cache_entry
        metrics.counter('semantic_cache_set_total').inc()
```

**Metrics to Add:**
```python
semantic_cache_hits_total = Counter('astra_semantic_cache_hits_total')
semantic_cache_misses_total = Counter('astra_semantic_cache_misses_total')
semantic_cache_key_collisions_total = Counter('astra_semantic_cache_key_collisions_total')
```

---

### **9. Circuit Breaker Configuration**

**Make thresholds environment-driven:**

```python
# src/astra/infrastructure/circuit_breaker.py
class CircuitBreaker:
    def __init__(self):
        self.failure_threshold = int(os.getenv('ASTRA_BREAKER_THRESHOLD', '5'))
        self.recovery_time = int(os.getenv('ASTRA_BREAKER_RECOVERY_TIME', '30'))
        self.timeout = int(os.getenv('ASTRA_BREAKER_TIMEOUT', '10'))
        self.half_open_max_calls = int(os.getenv('ASTRA_BREAKER_HALF_OPEN_CALLS', '3'))
        
    def half_open_probe(self):
        """
        Allow limited traffic in HALF_OPEN state to test recovery
        """
        if self.state == State.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
        return False
    
    def jittered_backoff(self):
        """
        Add jitter to prevent thundering herd
        """
        base_delay = self.recovery_time
        jitter = random.uniform(0, base_delay * 0.3)
        return base_delay + jitter
```

**.env additions:**
```properties
# Circuit Breaker Configuration
ASTRA_BREAKER_THRESHOLD=5           # Failures before OPEN
ASTRA_BREAKER_RECOVERY_TIME=30      # Seconds before HALF_OPEN
ASTRA_BREAKER_TIMEOUT=10            # Request timeout
ASTRA_BREAKER_HALF_OPEN_CALLS=3     # Test calls in HALF_OPEN
```

---

### **10. PII Redaction (Pre-Persist)**

```python
# src/astra/services/pii_redactor.py
import re
from typing import Dict, List
from prometheus_client import Counter

redactions_total = Counter(
    'astra_pii_redactions_total',
    'Total number of PII redactions',
    ['pii_type']
)

class PIIRedactor:
    """Redact PII before persisting to memory"""
    
    PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        'ip_address': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    }
    
    def redact(self, text: str) -> tuple[str, List[str]]:
        """
        Redact PII from text
        Returns: (redacted_text, list_of_redacted_types)
        """
        redacted = text
        found_types = []
        
        for pii_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(redacted)
            if matches:
                redacted = pattern.sub(f'[REDACTED_{pii_type.upper()}]', redacted)
                found_types.append(pii_type)
                redactions_total.labels(pii_type=pii_type).inc(len(matches))
        
        return redacted, found_types

# Integration into memory service
class MemoryService:
    def __init__(self):
        self.redactor = PIIRedactor()
    
    def store_memory(self, text: str):
        # Redact PII before storing
        redacted_text, pii_types = self.redactor.redact(text)
        if pii_types:
            logger.info("PII redacted before storage", pii_types=pii_types)
        
        # Store redacted version
        self.vector_store.add(redacted_text)
```

**Unit Tests:**
```python
# tests/test_pii_redaction.py
def test_redact_ssn():
    redactor = PIIRedactor()
    text = "My SSN is 123-45-6789"
    redacted, types = redactor.redact(text)
    assert redacted == "My SSN is [REDACTED_SSN]"
    assert 'ssn' in types

def test_redact_email():
    redactor = PIIRedactor()
    text = "Contact me at user@example.com"
    redacted, types = redactor.redact(text)
    assert redacted == "Contact me at [REDACTED_EMAIL]"
```

---

### **11. Memory Consolidation Job**

**Purpose:** Weekly deduplication and decay of old memories

```python
# scripts/consolidate_memories.py
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from prometheus_client import Counter

mem_consolidated_total = Counter(
    'astra_memory_consolidated_total',
    'Total memories consolidated',
    ['action']
)

class MemoryConsolidator:
    def __init__(self, vector_store, threshold=0.95):
        self.vector_store = vector_store
        self.similarity_threshold = threshold
        
    def find_duplicates(self):
        """Find near-duplicate memories"""
        memories = self.vector_store.get_all()
        duplicates = []
        
        for i, mem1 in enumerate(memories):
            for mem2 in memories[i+1:]:
                similarity = self.cosine_similarity(mem1, mem2)
                if similarity > self.similarity_threshold:
                    duplicates.append((mem1, mem2, similarity))
        
        return duplicates
    
    def consolidate_duplicates(self, duplicates):
        """Merge duplicate memories"""
        for mem1, mem2, similarity in duplicates:
            # Keep the one with more metadata/context
            keep = mem1 if len(mem1.metadata) >= len(mem2.metadata) else mem2
            remove = mem2 if keep == mem1 else mem1
            
            # Merge access counts
            keep.metadata['access_count'] = (
                keep.metadata.get('access_count', 0) + 
                remove.metadata.get('access_count', 0)
            )
            
            # Delete duplicate
            self.vector_store.delete(remove.id)
            mem_consolidated_total.labels(action='deduped').inc()
            
            logging.info(f"Consolidated duplicate: {remove.id} -> {keep.id}")
    
    def decay_old_memories(self, days=90):
        """Apply decay to old, rarely accessed memories"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        memories = self.vector_store.get_all()
        
        for mem in memories:
            created = mem.metadata.get('created_at')
            access_count = mem.metadata.get('access_count', 0)
            
            if created < cutoff and access_count < 5:
                # Either delete or reduce importance score
                mem.metadata['importance'] *= 0.5
                self.vector_store.update(mem)
                mem_consolidated_total.labels(action='decayed').inc()

# Schedule weekly
if __name__ == "__main__":
    consolidator = MemoryConsolidator(vector_store)
    
    # Find and consolidate duplicates
    duplicates = consolidator.find_duplicates()
    consolidator.consolidate_duplicates(duplicates)
    
    # Apply decay to old memories
    consolidator.decay_old_memories(days=90)
```

**Schedule:**
```powershell
# Schedule weekly (Sundays 03:00, after WAL checkpoint)
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\scripts\consolidate_memories.py" `
    -WorkingDirectory "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3:00AM

Register-ScheduledTask -TaskName "ASTRA-Memory-Consolidation" `
    -Action $action -Trigger $trigger
```

---

### **12. Observability Polish: Grafana Dashboards**

**Create Grafana dashboard JSON:**

```json
{
  "dashboard": {
    "title": "ASTRA Core v1.0.0 - Production Monitoring",
    "panels": [
      {
        "title": "LLM Latency (p95, p99)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(astra_llm_latency_seconds_bucket[5m]))",
          "legendFormat": "p95"
        }, {
          "expr": "histogram_quantile(0.99, rate(astra_llm_latency_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }]
      },
      {
        "title": "Cache Performance",
        "targets": [{
          "expr": "rate(astra_memory_cache_hits_total[5m])",
          "legendFormat": "hits/sec"
        }, {
          "expr": "rate(astra_memory_cache_queries_total[5m])",
          "legendFormat": "queries/sec"
        }]
      },
      {
        "title": "Circuit Breaker Status",
        "targets": [{
          "expr": "astra_circuit_breaker_state",
          "legendFormat": "state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)"
        }]
      },
      {
        "title": "Memory Operations",
        "targets": [{
          "expr": "rate(astra_memory_consolidated_total[1h])",
          "legendFormat": "consolidations/hour"
        }]
      }
    ],
    "annotations": {
      "list": [{
        "name": "Deployments",
        "datasource": "-- Grafana --",
        "tags": ["deploy"]
      }]
    }
  }
}
```

**Alert Runbook Links:**
Add to Prometheus alert definitions:
```yaml
annotations:
  runbook_url: "https://docs.astra.internal/runbooks/high-latency"
  summary: "p95 latency exceeded 1.2s"
```

---

## 🎨 **PRODUCT & UX (PARALLEL TRACKS)**

### **13. Desktop UX Smoke Tests**

```powershell
# Manual test checklist
# 1. End-to-end conversation
#    - Launch astra-desktop-simple
#    - Send 5 messages
#    - Verify responses received
#    - Check streaming works

# 2. Settings persistence
#    - Change temperature, max tokens
#    - Close and reopen app
#    - Verify settings saved

# 3. Reconnect after API restart
#    - Start conversation
#    - Restart API: .\scripts\stop.ps1; .\scripts\ship.ps1
#    - Continue conversation
#    - Verify reconnection successful
```

**Automated Smoke Test:**
```javascript
// astra-desktop-simple/tests/smoke.test.js
describe('Desktop UX Smoke Tests', () => {
  test('End-to-end conversation', async () => {
    const app = await launchApp();
    await app.sendMessage('Hello ASTRA');
    const response = await app.waitForResponse();
    expect(response).toBeTruthy();
  });
  
  test('Settings persistence', async () => {
    const app = await launchApp();
    await app.setTemperature(0.9);
    await app.close();
    
    const app2 = await launchApp();
    const temp = await app2.getTemperature();
    expect(temp).toBe(0.9);
  });
});
```

---

### **14. Bridge/Tooling Enablement**

**Enable 2 safe tools:**

```python
# src/astra/bridge/tools/file_tools.py
@tool("read_file")
def read_file(path: str, max_size: int = 10000) -> str:
    """
    Read and summarize a file (safe, read-only)
    Max size: 10KB to prevent abuse
    """
    # Validate path (no traversal)
    if '..' in path or path.startswith('/'):
        raise ValueError("Invalid path")
    
    # Check file size
    if os.path.getsize(path) > max_size:
        return f"File too large (>{max_size} bytes)"
    
    # Read and return
    with open(path, 'r') as f:
        content = f.read()
    
    # Track usage
    metrics.counter('tool_usage_total', {'tool': 'read_file'}).inc()
    
    return content

@tool("calculator")
def calculator(expression: str) -> float:
    """
    Safe calculator (no eval, only basic math)
    """
    # Use ast.literal_eval for safety
    import ast
    try:
        result = ast.literal_eval(expression)
        metrics.counter('tool_usage_total', {'tool': 'calculator'}).inc()
        return result
    except:
        return "Invalid expression"
```

**Tool Guardrails:**
```python
# src/astra/bridge/guardrails.py
class ToolGuardrails:
    def __init__(self):
        self.rate_limiter = RateLimiter(max_calls=10, window=60)  # 10/min
        
    def can_execute(self, tool_name: str, user_id: str) -> bool:
        """Check if tool execution is allowed"""
        # Rate limiting
        if not self.rate_limiter.allow(f"{user_id}:{tool_name}"):
            metrics.counter('tool_rate_limited_total').inc()
            return False
        
        # Whitelist check
        if tool_name not in ['read_file', 'calculator']:
            return False
        
        return True
```

---

### **15. Feedback Loop**

```python
# src/astra/services/feedback_service.py
class FeedbackService:
    """Simple thumbs-up/down feedback storage"""
    
    def record_feedback(self, message_id: str, rating: str, user_comment: str = None):
        """
        Record user feedback
        rating: 'up' or 'down'
        """
        feedback = {
            'message_id': message_id,
            'rating': rating,
            'comment': user_comment,
            'timestamp': datetime.utcnow()
        }
        
        # Store in episodic memory for later eval
        self.memory_service.store_episodic(feedback)
        
        # Track metrics
        metrics.counter('user_feedback_total', {'rating': rating}).inc()
        
        return feedback

# API endpoint
@app.post("/v1/feedback")
async def submit_feedback(
    message_id: str,
    rating: Literal['up', 'down'],
    comment: Optional[str] = None
):
    feedback_service.record_feedback(message_id, rating, comment)
    return {"status": "recorded"}
```

---

## 🔐 **SECURITY & OPS (CONTINUING)**

### **16. Key Rotation Script**

```powershell
# scripts/rotate_api_key.ps1
param([switch]$Force)

Write-Host "[*] ASTRA API Key Rotation" -ForegroundColor Cyan

if (-not $Force) {
    $confirm = Read-Host "This will invalidate all current API keys. Continue? (yes/no)"
    if ($confirm -ne 'yes') {
        Write-Host "[X] Aborted" -ForegroundColor Red
        exit 1
    }
}

# Generate new key
$newKey = $(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Backup current .env
Copy-Item .env .env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')

# Update .env
$content = Get-Content .env
$content = $content -replace 'ASTRA_API_KEYS=.*', "ASTRA_API_KEYS=$newKey"
$content | Set-Content .env

Write-Host "[OK] New API key generated" -ForegroundColor Green
Write-Host "     Key: $($newKey.Substring(0, 12))...***" -ForegroundColor Gray
Write-Host "`n[!] IMPORTANT: Update all clients with new key" -ForegroundColor Yellow
Write-Host "     Desktop apps, scripts, integrations, etc." -ForegroundColor Gray
Write-Host "`n[*] Restart required: .\scripts\stop.ps1; .\scripts\ship.ps1" -ForegroundColor Cyan
```

**Runbook Entry:**
```markdown
## API Key Rotation Procedure

**Frequency:** Quarterly or on suspected compromise

**Steps:**
1. Run: `.\scripts\rotate_api_key.ps1`
2. Update all client applications with new key
3. Restart API server
4. Verify clients can connect
5. Monitor for authentication failures
6. Remove backup keys after 24h grace period
```

---

### **17. Least-Privilege Verification**

```powershell
# scripts/security_audit.ps1
Write-Host "[*] ASTRA Security Audit" -ForegroundColor Cyan

# 1. Check .env permissions (should be restricted)
$envAcl = Get-Acl .env
Write-Host "`n[*] .env Permissions:" -ForegroundColor White
$envAcl.Access | Format-Table IdentityReference, FileSystemRights

# 2. Verify localhost binding
$bindConfig = Get-Content scripts\ship.ps1 | Select-String "HostBind"
Write-Host "`n[*] Network Binding:" -ForegroundColor White
Write-Host "     $bindConfig" -ForegroundColor Gray
if ($bindConfig -match "0.0.0.0") {
    Write-Host "     [!] WARNING: Binding to 0.0.0.0 (all interfaces)" -ForegroundColor Yellow
} else {
    Write-Host "     [OK] Secure localhost binding" -ForegroundColor Green
}

# 3. Check for exposed secrets in git
$gitSecrets = git grep -i "password\|secret\|key" -- '*.py' '*.js' ':!tests/'
if ($gitSecrets) {
    Write-Host "`n[!] Potential secrets in code:" -ForegroundColor Yellow
    $gitSecrets
} else {
    Write-Host "`n[OK] No obvious secrets in code" -ForegroundColor Green
}
```

---

### **18. DR Tabletop Exercise**

**Scenario:** LLM server outage simulation

```powershell
# DR Drill Script
Write-Host "[*] DR DRILL: Simulating LLM outage" -ForegroundColor Yellow

# 1. Stop LLM server (simulate outage)
Get-Process | Where-Object {$_.Name -like "*llama*"} | Stop-Process -Force
Write-Host "[*] LLM server stopped (simulated outage)" -ForegroundColor Red

# 2. Observe circuit breaker behavior
Start-Sleep -Seconds 5
curl http://127.0.0.1:8080/v1/chat/completions -Method POST `
    -Body '{"messages":[{"role":"user","content":"test"}]}'

# Expected: Circuit breaker OPEN, graceful 503

# 3. Check cache serves requests
curl http://127.0.0.1:8080/metrics | Select-String "cache_hits"

# 4. Recovery
Write-Host "`n[*] Restarting LLM server (recovery)" -ForegroundColor Green
.\scripts\ship.ps1

# 5. Verify recovery
Start-Sleep -Seconds 30
.\scripts\day0_watch.ps1
```

**Acceptance:**
- ✅ Circuit breaker opens automatically
- ✅ Graceful 503 responses (no crashes)
- ✅ Cache continues serving
- ✅ Recovery on LLM restart
- ✅ All metrics resume normal

---

## 📋 **READY-MADE TICKETS**

Copy these into your issue tracker:

### **Week-1 Tickets:**

```markdown
## [Perf] BGE-M3 Dual-Index A/B Test
**Priority:** P1
**Timeline:** Days 3-7
**Description:** 
- Set up dual collection (MiniLM + BGE-M3)
- Run 50/50 A/B split for 24 hours
- Measure: Precision@5, latency, cache hit rate
**Acceptance:** 
- +15-20% relevance improvement
- ≤10% latency impact
- Switch default if successful

## [QA] Close Test Gap 46/49 → 49/49
**Priority:** P0
**Timeline:** Day 1-2
**Description:**
- Fix time-based test flakes (freeze time)
- Fix rate-limit test env overrides
- Ensure bridge import stability
**Acceptance:**
- All 49/49 tests passing
- CI gate set to ≥94% coverage
- No flaky tests in 10 runs

## [Ops] Schedule WAL Checkpoint + Log Rotation
**Priority:** P1
**Timeline:** Day 2
**Description:**
- Schedule weekly WAL checkpoint (Sun 02:00)
- Add log rotation (keep 4 weeks)
- Monitor for "database locked" errors
**Acceptance:**
- Task scheduled and verified
- WAL size bounded <100MB
- Zero lock errors for 7 days

## [Obs] Add Cache Metrics + Grafana Dashboard
**Priority:** P2
**Timeline:** Week-1
**Description:**
- Add cache_miss_total, ttl_expired_total metrics
- Create Grafana dashboard (latency, cache, breaker, memory)
- Add alert runbook links
**Acceptance:**
- All metrics instrumented
- Dashboard deployed
- Runbook links functional
```

### **Week 2-4 Tickets:**

```markdown
## [Sec] Add PII Redaction Pre-Persist
**Priority:** P1
**Timeline:** Week-2
**Description:**
- Implement regex/NER filter for SSN, email, phone, CC, IP
- Add redactions_total counter
- Unit tests for common patterns
**Acceptance:**
- All PII types detected
- Metrics tracking redactions
- Zero PII in stored memories (audit)

## [Reliability] Circuit Breaker Env-Config + Half-Open
**Priority:** P2
**Timeline:** Week-2
**Description:**
- Make thresholds environment-driven
- Add half-open state with probes
- Add jittered backoff
**Acceptance:**
- All config in .env
- Half-open probes working
- Graceful recovery demonstrated

## [UX] Desktop End-to-End Flows
**Priority:** P2
**Timeline:** Week-3
**Description:**
- End-to-end conversation test
- Settings persistence test
- Reconnect after API restart
**Acceptance:**
- All manual tests pass
- Automated smoke tests added
- No UX regressions

## [DX] Key Rotation Script + Runbook
**Priority:** P2
**Timeline:** Week-3
**Description:**
- Create rotate_api_key.ps1 script
- Document rotation procedure
- Add to security runbook
**Acceptance:**
- Script functional and safe
- Runbook entry complete
- Tested with successful rotation
```

---

## 🎯 **SUCCESS METRICS**

### **Week-1 Summary (Target):**
- ✅ **p95 latency:** ≤ 1.2s sustained
- ✅ **Cache hit:** ≥ 30% 
- ✅ **Error rate:** < 0.5%
- ✅ **Uptime:** > 99.5%
- ✅ **Tests:** 49/49 passing (100%)
- ✅ **Coverage:** ≥ 94%
- ✅ **Backups:** Verified restorable
- ✅ **Alerts:** Zero false positives

### **Month-1 Summary (Target):**
- ✅ **BGE-M3:** Live and default (+20% precision)
- ✅ **Tests:** 100% passing, CI gate enforced
- ✅ **Service mode:** Enabled with auto-restart
- ✅ **Phase-2 safeguards:** PII redaction, circuit breaker config, semantic cache
- ✅ **Documentation:** Complete runbooks
- ✅ **Monitoring:** Grafana dashboards operational
- ✅ **Security:** Key rotation tested, least-privilege verified
- ✅ **DR:** Tabletop exercise completed

---

## 📊 **TRACKING DASHBOARD**

Create a simple tracking sheet:

| Milestone | Target Date | Status | Notes |
|-----------|-------------|--------|-------|
| v1.0.0 Tagged | Oct 16 | ✅ DONE | Production launch |
| 48h Stable | Oct 18 | 🟡 In Progress | Monitoring |
| Tests 49/49 | Oct 17 | 🔴 Todo | Fix 3 failing |
| WAL Scheduled | Oct 17 | 🔴 Todo | Task Scheduler |
| BGE-M3 A/B | Oct 20-21 | 🔴 Todo | After 48h stable |
| Cache Metrics | Oct 20 | 🔴 Todo | Add missing counters |
| Service Mode | Oct 22 | 🔴 Todo | Optional |
| PII Redaction | Oct 30 | 🔴 Todo | Week-2 |
| Grafana Dashboard | Nov 1 | 🔴 Todo | Week-2 |
| Month-1 Review | Nov 16 | 🔴 Todo | Full assessment |

---

**Status Legend:**
- ✅ **DONE** - Complete and verified
- 🟢 **On Track** - In progress, no blockers
- 🟡 **At Risk** - Needs attention
- 🔴 **Todo** - Not started
- ❌ **Blocked** - Requires unblocking

---

## 🚀 **NEXT IMMEDIATE ACTIONS**

### **Right Now (T+0 → T+30min):**
1. ✅ Continue monitoring with `.\scripts\day0_watch.ps1` every 5-10 minutes
2. ✅ Watch logs for any ERROR/CRITICAL entries
3. ✅ Verify cache is warming up (10% → 15%+)

### **After T+30min Stable:**
4. Tag v1.0.0 release
5. Push tag to origin
6. Update CI configuration (coverage gate ≥94%)

### **Day-1 (Tomorrow):**
7. Fix 3 failing tests (time-based, rate-limit, bridge import)
8. Verify 49/49 passing
9. Schedule WAL checkpoint task
10. Begin BGE-M3 preparation (check disk space)

### **Days 2-7:**
11. Continue hourly monitoring
12. Run BGE-M3 A/B test
13. Add cache metrics if missing
14. Create Grafana dashboard
15. Optional: Enable service mode

---

**You're on the path to production excellence! 🎉**

See you at Month-1 review with a fully hardened, optimized ASTRA Core v1.0.0! 🚀
