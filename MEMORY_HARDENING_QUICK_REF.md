# Memory Consolidation Hardening - Quick Reference

## ⚡ Quick Commands

### Check Prometheus Metrics
```bash
curl http://localhost:8000/metrics | grep dream
```

### Trigger Manual Consolidation
```bash
curl -X POST http://localhost:8000/consolidation/run
```

### Check Job History
```bash
curl http://localhost:8000/consolidation/history?limit=10
```

### View Job Journal (raw)
```bash
cat data/locks/consolidation.journal | tail -20
```

### Check Lock Status
```bash
ls -la data/locks/dream.lock
# If file exists → run is in progress
# If file missing → no active run
```

## 🔐 Environment Setup

### Set HMAC Secret Key (Production)
```bash
# Generate 256-bit key
python -c "import secrets; print(secrets.token_hex(32))"

# Export (Linux/Mac)
export ASTRA_MEMORY_HMAC_KEY="your-generated-key-here"

# Export (Windows PowerShell)
$env:ASTRA_MEMORY_HMAC_KEY="your-generated-key-here"
```

### Install Dependencies
```bash
pip install prometheus-client fasteners
```

## 📊 Prometheus Metrics

### Available Metrics (8 total)
- `astra_dream_runs_total` - Consolidations started
- `astra_dream_runs_success_total` - Consolidations succeeded
- `astra_dream_events_processed_total` - Events processed
- `astra_dream_clusters_total` - Clusters formed
- `astra_dream_noise_total` - Noise events
- `astra_dream_duration_seconds` - Duration histogram
- `astra_dream_overlap_lock` - 1=running, 0=idle
- `astra_dream_quality_score` - Quality histogram (0..1)

### Sample Prometheus Queries
```promql
# Success rate (last 7 days)
rate(astra_dream_runs_success_total[7d]) / rate(astra_dream_runs_total[7d])

# p95 duration (last 24h)
histogram_quantile(0.95, rate(astra_dream_duration_seconds_bucket[24h]))

# p50 quality score (last 24h)
histogram_quantile(0.50, rate(astra_dream_quality_score_bucket[24h]))

# Events per hour
rate(astra_dream_events_processed_total[1h]) * 3600
```

## 🔒 Cryptographic Provenance

### Verify Summary Signature (Python)
```python
from services.memory_provenance import verify_summary

signature = {
    "root": "a1b2c3d4...",
    "text": "User frequently asks about...",
    "hmac": "f3e2d1c0..."
}

valid = verify_summary(signature)
print(f"Valid: {valid}")  # True or False
```

### Compute Event Hash (Python)
```python
from services.memory_provenance import leaf_hash

event = {
    "id": "evt_123",
    "ts": "2025-11-02T02:15:00Z",
    "payload": {"query": "test"}
}

hash = leaf_hash(event)
print(f"Hash: {hash}")  # 64-char hex string
```

## 🔧 Troubleshooting

### Problem: "Another run is in progress"
**Cause**: Overlap lock is held (another process running)

**Solutions**:
1. Wait for current run to finish (check duration with `curl /consolidation/status`)
2. If stale lock (crash): `rm data/locks/dream.lock`
3. Check Prometheus metric: `astra_dream_overlap_lock` (should be 0 when idle)

### Problem: "HMAC verification failed"
**Cause**: HMAC secret key mismatch or tampered summary

**Solutions**:
1. Verify `ASTRA_MEMORY_HMAC_KEY` env var is set correctly
2. Check if key changed between write and read
3. If summary is tampered → reject and log alert

### Problem: "No metrics at /metrics endpoint"
**Cause**: `prometheus-client` not installed or endpoint not mounted

**Solutions**:
1. Install: `pip install prometheus-client`
2. Verify endpoint: `curl http://localhost:8000/metrics`
3. Check launch_server.py has `app.mount("/metrics", make_asgi_app())`

### Problem: "Job journal is empty"
**Cause**: No consolidation runs yet or journal file missing

**Solutions**:
1. Trigger manual run: `POST /consolidation/run`
2. Check directory exists: `mkdir -p data/locks`
3. Verify permissions: `ls -la data/locks`

## 📈 Alerting Thresholds

### Critical Alerts
- No run in 48h → `time() - astra_dream_runs_total > 172800`
- Success rate < 95% (7d) → `rate(astra_dream_runs_success_total[7d]) / rate(astra_dream_runs_total[7d]) < 0.95`

### Warning Alerts
- p95 duration > 10 min → `histogram_quantile(0.95, astra_dream_duration_seconds) > 600`
- p50 quality < 0.55 → `histogram_quantile(0.50, astra_dream_quality_score) < 0.55`
- Noise rate > 50% → `rate(astra_dream_noise_total[1h]) / rate(astra_dream_events_processed_total[1h]) > 0.5`

## 🧪 Testing

### Test Overlap Lock
```bash
# Terminal 1
curl -X POST http://localhost:8000/consolidation/run

# Terminal 2 (should skip)
curl -X POST http://localhost:8000/consolidation/run
# → {"status": "skipped", "reason": "Another run in progress"}
```

### Test Prometheus Metrics
```bash
# Before run
curl http://localhost:8000/metrics | grep astra_dream_runs_total
# → astra_dream_runs_total 0.0

# Trigger run
curl -X POST http://localhost:8000/consolidation/run

# After run
curl http://localhost:8000/metrics | grep astra_dream_runs_total
# → astra_dream_runs_total 1.0
```

### Test Job Journal
```bash
# Trigger run
curl -X POST http://localhost:8000/consolidation/run

# Check journal
cat data/locks/consolidation.journal | tail -2
# → {"job_id": "job_...", "started_at": "...", "status": "running"}
# → {"job_id": "job_...", "completed_at": "...", "status": "success", ...}
```

## 📚 API Endpoints

### POST /consolidation/run
**Purpose**: Trigger manual consolidation

**Optional Query Params**:
- `limit` (int): Max events to process (default: 100)
- `since` (ISO timestamp): Only process events after this time

**Response**:
```json
{
  "job_id": "job_1730508900.123",
  "events_processed": 50,
  "clusters_formed": 4,
  "noise_count": 8,
  "duration_seconds": 145.2
}
```

### GET /consolidation/status
**Purpose**: Check scheduler status

**Response**:
```json
{
  "running": false,
  "next_run": "2025-11-03T02:00:00Z",
  "last_run": {
    "job_id": "job_1730508900.123",
    "timestamp": "2025-11-02T02:15:00Z",
    "status": "success",
    "events_processed": 50
  }
}
```

### GET /consolidation/history?limit=10
**Purpose**: Get job history

**Response**:
```json
{
  "entries": [
    {
      "job_id": "job_1730508900.123",
      "started_at": "2025-11-02T02:15:00Z",
      "completed_at": "2025-11-02T02:17:30Z",
      "status": "success",
      "events_processed": 50,
      "clusters_formed": 4,
      "quality_score": 0.72
    }
  ]
}
```

## 🔑 Key Files

### Code
- `src/services/memory_provenance.py` - Crypto + quality scoring (280 LOC)
- `src/services/consolidation_lock.py` - Overlap lock + job journals (230 LOC)
- `src/services/memory_consolidation.py` - Main service (850 LOC)

### Data
- `data/locks/dream.lock` - Overlap lock (exists when run active)
- `data/locks/consolidation.journal` - Job history (JSONL)
- `data/locks/last_consolidation.txt` - Watermark (last run timestamp)

### Documentation
- `docs/week3/WEEK_3_DAYS_29-31_MEMORY_CONSOLIDATION_HARDENING.md` - Full guide (1200 lines)
- `🛡️_MEMORY_HARDENING_STEPS_1-3_COMPLETE.txt` - Progress banner

## 🎯 Next Steps

1. ⏳ **Step 4**: Hallucination guard (LLM provenance enforcement)
2. ⏳ **Step 5**: Dream Quality Score (integrate compute_quality_score)
3. ⏳ **Step 6**: Auto-tuning DBSCAN (k-distance elbow)
4. ⏳ **Step 7**: Canary + backfill modes (dry-run, archival)
5. ⏳ **Step 8**: CI gates (red-team tests, regression tests)

## 📞 Support

**Questions?**
- See: `docs/week3/WEEK_3_DAYS_29-31_MEMORY_CONSOLIDATION_HARDENING.md`
- Check: Prometheus metrics at `/metrics`
- Review: Job journal at `data/locks/consolidation.journal`

---

**Last Updated**: 2025-11-02  
**Status**: Steps 1-3 Complete (37.5%)
