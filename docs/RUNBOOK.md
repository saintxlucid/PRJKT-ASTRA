# ASTRA Operations Runbook

**Version:** 2.0.0  
**Last Updated:** October 9, 2025

---

## 📋 Quick Reference

### Service Ports
- **ASTRA API:** http://localhost:8080
- **LLM Server:** http://localhost:8001
- **Prometheus:** http://localhost:9090 (if configured)
- **Grafana:** http://localhost:3000 (if configured)

### Key Files
- **Config:** `.env`, `config/default.yaml`
- **Database:** `data/astra.db`
- **Vector Store:** `data/chromadb/`
- **Logs:** `logs/astra.log`
- **Backups:** `backups/`

### Emergency Contacts
- **On-Call:** [Add contact info]
- **Escalation:** [Add escalation path]

---

## 🚨 Error Recovery Procedures

### 1. "database is locked"

**Symptoms:**
- SQLite errors in logs
- 500 Internal Server Error responses
- `"database is locked"` messages
- Slow or hanging requests

**Diagnosis:**
```powershell
# Check for long-running transactions
sqlite3 data\astra.db "PRAGMA wal_checkpoint;"

# Check WAL mode
sqlite3 data\astra.db "PRAGMA journal_mode;"
# Expected: wal

# Check active connections
sqlite3 data\astra.db "PRAGMA database_list;"
```

**Solutions (in order):**

1. **Increase connection pool** (`.env`):
   ```bash
   ASTRA_DATABASE_POOL_SIZE=40
   ASTRA_DATABASE_MAX_OVERFLOW=60
   ```
   Restart backend.

2. **Checkpoint WAL file**:
   ```powershell
   sqlite3 data\astra.db "PRAGMA wal_checkpoint(TRUNCATE);"
   ```

3. **Restart backend** (releases all locks):
   ```powershell
   # In backend terminal: Ctrl+C
   .\.venv\Scripts\python.exe run_server.py
   ```

4. **Last resort - Database recovery**:
   ```powershell
   # Stop backend first
   cp data\astra.db data\astra.db.backup
   sqlite3 data\astra.db ".recover" | sqlite3 data\astra_recovered.db
   mv data\astra_recovered.db data\astra.db
   # Restart backend
   ```

**Prevention:**
- Monitor `astra_database_connections_active` metric
- Ensure WAL mode is enabled
- Use connection pooling (already configured)
- Set `ASTRA_DATABASE_POOL_TIMEOUT=30` to fail fast

**Root Cause:**
- High concurrent writes
- Long-running transactions
- Insufficient connection pool

---

### 2. "LLM timeout" / "504 Gateway Timeout"

**Symptoms:**
- Chat requests return 504 Gateway Timeout
- Slow response times (>30 seconds)
- llama.cpp unresponsive
- High memory usage

**Diagnosis:**
```powershell
# Check LLM health
curl http://localhost:8001/health

# Check llama.cpp process
Get-Process | Where-Object {$_.Name -like "*llama*"}

# Check memory usage
Get-Process llama-server | Select-Object WorkingSet64

# Check logs (if llama.cpp running in terminal)
# Look for: OOM errors, context overflow, model loading errors
```

**Solutions (in order):**

1. **Reduce context window** (`.env`):
   ```bash
   ASTRA_LLM_CONTEXT_LENGTH=65536  # Down from 131072
   ```
   Restart backend.

2. **Lower temperature** (faster inference):
   ```bash
   ASTRA_LLM_TEMPERATURE=0.5  # Down from 0.35 or higher
   ASTRA_LLM_REASONING_MODE=low  # Down from medium/high
   ```
   Restart backend.

3. **Restart llama.cpp**:
   ```powershell
   # Kill existing process
   Get-Process llama-server | Stop-Process -Force
   
   # Restart with script
   .\scripts\start_gptoss_server.ps1
   ```

4. **Reduce timeout** (fail fast):
   ```bash
   ASTRA_LLM_TIMEOUT=30  # Seconds (default: 300)
   ```
   Restart backend.

5. **Check model file**:
   ```powershell
   # Verify model exists and isn't corrupted
   Test-Path "X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf"
   
   # Check file size (should be ~11.27 GB)
   (Get-Item "X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf").Length / 1GB
   ```

**Prevention:**
- Monitor `astra_llm_response_time` metric
- Set up health check alerts
- Regular llama.cpp restarts (daily at 3:00 AM)
- Monitor system memory usage

**Root Cause:**
- Model memory leak (needs restart)
- Context too large for available RAM
- Model file corruption
- CPU overload

---

### 3. "Out of Memory" (OOM)

**Symptoms:**
- System slowdown
- llama.cpp crashes
- Windows freezes or unresponsive
- High memory usage (>90% RAM)
- Services killed by OS

**Diagnosis:**
```powershell
# Check RAM usage
Get-Process | Sort-Object -Property WS -Descending | Select-Object -First 10

# Check total system memory
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory

# Check llama.cpp memory
Get-Process llama-server | Select-Object @{Name="Memory(GB)";Expression={$_.WS / 1GB}}

# Check Python process memory
Get-Process python | Select-Object @{Name="Memory(GB)";Expression={$_.WS / 1GB}}
```

**Solutions (in order):**

1. **Restart llama.cpp** (often has memory leak):
   ```powershell
   Get-Process llama-server | Stop-Process -Force
   .\scripts\start_gptoss_server.ps1
   ```

2. **Reduce concurrent requests** (`.env`):
   ```bash
   ASTRA_MAX_CONCURRENT=16  # Down from 32
   ASTRA_MAX_QUEUE=32  # Down from 64
   ```
   Restart backend.

3. **Clear HuggingFace cache** (frees 2-4 GB):
   ```powershell
   Remove-Item -Path "X:\PROJECT_ASTRA\data\hf_cache\*" -Recurse -Force
   ```

4. **Reduce context window** (see LLM timeout section above)

5. **Close other applications**:
   - Chrome/Edge (RAM hog)
   - Other dev tools
   - Background services

**Prevention:**
- Monitor system RAM with `astra_system_memory_percent` (if configured)
- Schedule daily llama.cpp restart (3:00 AM)
- Set process memory limits (Windows Resource Governor)
- Regular cache cleanup (weekly)

**Root Cause:**
- llama.cpp memory leak
- Too many concurrent requests
- Large embedding model cache
- Other applications consuming RAM

---

### 4. "Rate Limit Exceeded" (429)

**Symptoms:**
- Client receives HTTP 429 Too Many Requests
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- `rate_limit_exceeded` in logs

**Diagnosis:**
```powershell
# Check current rate limit
curl http://localhost:8080/v1/system/health -i | Select-String "X-RateLimit"

# Check metrics
curl http://localhost:8080/metrics | Select-String "astra_rate_limit"
```

**Solutions:**

1. **Adjust rate limit** (`.env`):
   ```bash
   ASTRA_RATE_LIMIT_REQUESTS=60  # Up from 30
   ASTRA_RATE_LIMIT_WINDOW=5  # Keep at 5 seconds
   # Result: 12 req/sec instead of 6 req/sec
   ```
   Restart backend.

2. **Client-side throttling**:
   - Add retry logic with exponential backoff
   - Respect `Retry-After` header
   - Use request queuing on client side

**Prevention:**
- Monitor `astra_http_requests_total{status="429"}` metric
- Set up alerts for high 429 rate
- Review client access patterns

**Root Cause:**
- Burst traffic from client
- DDoS attack
- Misconfigured client (retry loop)

---

### 5. "Unauthorized" (401)

**Symptoms:**
- HTTP 401 Unauthorized
- `"Invalid or missing API key"` message
- `api_key_invalid` in logs

**Diagnosis:**
```powershell
# Check if API key is configured
echo $env:ASTRA_API_KEY

# Test with API key
curl -H "X-API-Key: $env:ASTRA_API_KEY" http://localhost:8080/v1/system/health

# Test without API key (should fail)
curl http://localhost:8080/v1/chat/
```

**Solutions:**

1. **Verify API key**:
   ```powershell
   # Check .env file
   Get-Content .env | Select-String "ASTRA_API_KEY"
   
   # Regenerate if compromised
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. **Update client requests**:
   ```powershell
   # Add header to all requests
   $headers = @{"X-API-Key" = $env:ASTRA_API_KEY}
   Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/" -Headers $headers -Method POST -Body $body
   ```

3. **Temporarily disable auth** (emergency only):
   ```powershell
   # Remove from .env
   # ASTRA_API_KEY=...
   
   # Restart backend
   ```

**Prevention:**
- Store API key securely (password manager, Azure Key Vault)
- Rotate keys regularly (monthly)
- Monitor `api_key_invalid` events
- Use per-client API keys (future enhancement)

**Root Cause:**
- Missing API key in client request
- Wrong API key used
- API key rotated but client not updated

---

## 🔄 Routine Maintenance

### Daily Tasks (Automated)

**Backup (03:30 AM)**
```powershell
# Windows Task Scheduler already configured
# Manual run:
.\scripts\backup_production.ps1

# Verify:
Get-ChildItem backups\ -Filter "*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

**Health Check (Every 5 minutes)**
```powershell
# Add to Task Scheduler:
.\scripts\check_system_health.py

# Or manual:
curl http://localhost:8080/v1/system/health
```

### Weekly Tasks

**Memory Consolidation (Sunday 03:45 AM)**
```powershell
# Run script
.\.venv\Scripts\python.exe scripts\consolidate_memories.py

# Check results
sqlite3 data\astra.db "SELECT COUNT(*) FROM conversations;"
curl http://localhost:8080/v1/system/health | ConvertFrom-Json | Select-Object -ExpandProperty memory_stats
```

**Log Rotation**
```powershell
# Compress old logs
Get-ChildItem logs\ -Filter "*.log" | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | ForEach-Object {
    Compress-Archive -Path $_.FullName -DestinationPath "logs\archive\$($_.BaseName).zip"
    Remove-Item $_.FullName
}
```

**Metrics Review**
- Check Grafana dashboard
- Review error rate (should be <5%)
- Review p95 latency (should be <1200ms)
- Check disk space (should have >10GB free)

### Monthly Tasks

**API Key Rotation**
```powershell
# Generate new key
$newKey = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"

# Update .env
# ASTRA_API_KEY=$newKey

# Restart backend
# Update all clients with new key
```

**Database Optimization**
```powershell
# Vacuum database
sqlite3 data\astra.db "VACUUM;"

# Analyze statistics
sqlite3 data\astra.db "ANALYZE;"

# Check size
(Get-Item data\astra.db).Length / 1MB
```

**Dependency Updates**
```powershell
# Update Poetry packages
poetry update

# Run tests
.\.venv\Scripts\python.exe -m pytest tests\ -v

# Deploy if tests pass
```

---

## 📊 Monitoring & Alerts

### Key Metrics to Watch

**Availability**
- Target: ≥95%
- Metric: `astra_http_requests_total{status!~"5.."}` / `astra_http_requests_total`
- Alert: <95% over 5 minutes

**Latency**
- Target: p95 <1200ms, p99 <2500ms
- Metric: `histogram_quantile(0.95, astra_http_request_duration_seconds_bucket)`
- Alert: p95 >1500ms over 5 minutes

**Error Rate**
- Target: <5%
- Metric: `astra_http_requests_total{status="500"}` / `astra_http_requests_total`
- Alert: >5% over 5 minutes

**Resource Usage**
- Target: <80% RAM, <20GB disk free
- Metrics: System monitoring
- Alert: >90% RAM or <10GB disk

### Health Check Endpoints

```powershell
# Full health check
curl http://localhost:8080/v1/system/health

# Expected response:
{
  "status": "healthy",
  "llm_healthy": true,
  "database_connected": true,
  "memory_stats": {
    "total_memories": 21,
    "collection_name": "astra_memory"
  }
}

# Prometheus metrics
curl http://localhost:8080/metrics

# LLM health
curl http://localhost:8001/health
```

---

## 🔧 Configuration Management

### Critical Environment Variables

```bash
# Server
ASTRA_SERVER_PORT=8080
ASTRA_SERVER_HOST=0.0.0.0

# LLM
ASTRA_LLM_BASE_URL=http://localhost:8001
ASTRA_LLM_CONTEXT_LENGTH=131072
ASTRA_LLM_REASONING_MODE=medium
ASTRA_LLM_TEMPERATURE=0.35

# Database
ASTRA_DATABASE_POOL_SIZE=20
ASTRA_DATABASE_MAX_OVERFLOW=40

# Security
ASTRA_API_KEY=<your-secret-key>
ASTRA_ENCRYPTION_KEY=<your-encryption-key>
ASTRA_RATE_LIMIT_REQUESTS=30
ASTRA_RATE_LIMIT_WINDOW=5

# Concurrency
ASTRA_MAX_CONCURRENT=32
ASTRA_MAX_QUEUE=64
```

### Configuration Reload

Most config changes require backend restart:

```powershell
# Stop backend (Ctrl+C in terminal)

# Update .env or config/default.yaml

# Restart backend
.\.venv\Scripts\python.exe run_server.py

# Verify config loaded
curl http://localhost:8080/v1/system/health
```

---

## 📞 Escalation Procedures

### Level 1: Self-Service
- Check this runbook
- Review error logs
- Try standard recovery procedures
- Check Grafana dashboard

### Level 2: On-Call Engineer
- If issue persists >15 minutes
- If multiple systems affected
- If data loss suspected

### Level 3: System Administrator
- If Level 2 cannot resolve in 1 hour
- If root cause requires infrastructure changes
- If security incident suspected

### Critical Incidents
- **Data loss:** Escalate immediately to Level 3
- **Security breach:** Escalate to security team + Level 3
- **Total outage:** Page on-call + Level 2

---

## 📚 Additional Resources

- **Architecture:** `ARCHITECTURE.md`
- **Deployment:** `DEPLOYMENT_STATUS.md`
- **Quick Start:** `QUICKSTART.md`
- **API Docs:** http://localhost:8080/docs
- **Model Info:** `docs/models/gpt_oss_model_card.md`

---

*This runbook is a living document. Update it when procedures change or new issues are discovered.*

**Last Review:** October 9, 2025  
**Next Review:** November 9, 2025
