# 🎯 FINAL HARDENING IMPROVEMENTS (Optional - Post-Deploy)

Applied after successful v1.0.0 deployment and monitoring.

---

## 1. Disable API Documentation in Production

**Why:** Reduces attack surface by hiding `/docs` and `/redoc` endpoints

**Option A: Environment-based (Recommended)**

Created: `src/astra/api/app_production.py` - Factory that disables docs when `ASTRA_ENVIRONMENT=production`

Update ship.ps1 line 16:
```powershell
$AstraCmd = "python -m uvicorn src.astra.api.app_production:create_app_production --factory --host $HostBind --port $ApiPort --log-level info"
```

**Option B: Direct Edit**

Edit `src/astra/api/app.py` around line 110:
```python
app = FastAPI(
    title=settings.server.title,
    version=settings.server.version,
    lifespan=lifespan,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)
```

**Verify:**
```powershell
# Should return 404 in production
curl.exe http://127.0.0.1:8080/docs
```

---

## 2. Schedule Weekly WAL Checkpoint

**Why:** Prevents SQLite WAL file bloat over time

**Script:** `scripts/wal_checkpoint.py` (already created)

**Setup (Windows Task Scheduler):**
```powershell
# Run every Sunday at 3:00 AM
schtasks /create /tn "ASTRA WAL Checkpoint" /tr "python X:\PROJECT_ASTRA_1.0\scripts\wal_checkpoint.py" /sc weekly /d SUN /st 03:00

# Verify scheduled task
schtasks /query /tn "ASTRA WAL Checkpoint"
```

**Manual run:**
```powershell
python scripts\wal_checkpoint.py
```

**Expected output:**
```
============================================================
ASTRA Database WAL Checkpoint
============================================================
[2025-10-16T...] Starting WAL checkpoint for: X:\...\astra.db
  Before: busy=0, log_frames=1234, checkpointed_frames=0
  After:  busy=0, log_frames=0, checkpointed_frames=1234
  Journal mode: wal
[2025-10-16T...] Checkpoint completed successfully
============================================================
```

---

## 3. Enhanced Cache Efficiency Alert

**Why:** Monitor semantic cache performance over longer windows

**Status:** ✅ **ADDED** to `ops/prometheus/astra_alerts.yml`

**Alert:**
```yaml
- alert: LowCacheEfficiency
  expr: sum(rate(astra_cache_hits_total[30m])) / (sum(rate(astra_cache_hits_total[30m])) + sum(rate(astra_cache_misses_total[30m]))) < 0.20
  for: 30m
  labels:
    severity: warn
    component: cache
  annotations:
    summary: "Semantic cache efficiency below 20% for 30 minutes"
    description: "Cache hit rate: {{ $value | humanizePercentage }}. Review cache TTL settings or increase cache size."
    runbook: "Check cache metrics at /metrics. Consider increasing ASTRA_CACHE_MAX_SIZE or ASTRA_CACHE_TTL_SECONDS."
```

**Reload Prometheus:**
```bash
curl -X POST http://localhost:9090/-/reload
```

**Verify alert:**
```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="astra_core") | .rules[] | select(.name=="LowCacheEfficiency")'
```

---

## 4. Enhanced .gitignore

**Status:** ✅ **CREATED** - `x:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\.gitignore`

**Key exclusions:**
- `.env` and `.env.*` (except `.env.example`)
- `data/`, `*.db`, `logs/`
- `*.gguf`, `models/` (large model files)
- `.hf_cache/`, `runtime/`
- `backup/`, `*.backup`

**Verify:**
```powershell
git status --ignored
```

---

## 5. Environment Variable Binding Consistency

**Status:** ✅ **FIXED** - Changed `.env` from `0.0.0.0` to `127.0.0.1`

**Before:**
```properties
ASTRA_SERVER_HOST=0.0.0.0  # Exposed to LAN
```

**After:**
```properties
ASTRA_SERVER_HOST=127.0.0.1  # Localhost-only
```

**Note:** ship.ps1 still controls actual binding via `$HostBind` parameter (takes precedence over .env)

---

## 6. Load Testing Baseline

**Why:** Establish performance baseline for future comparisons

**Script:** `scripts/loadtest_baseline.js` (k6)

**Run:**
```bash
k6 run scripts/loadtest_baseline.js
```

**Expected results:**
```
✓ status is 200
✓ response time < 1200ms (p95)
✓ response time < 2000ms (p99)
✓ error rate < 5%

checks.........................: 95.00% ✓ 950 ✗ 50
http_req_duration..............: avg=450ms min=120ms med=380ms max=1800ms p(95)=980ms p(99)=1450ms
http_reqs......................: 1000 total
iterations.....................: 1000 total
vus............................: 10 min, 20 max
```

**Save baseline:**
```powershell
k6 run scripts/loadtest_baseline.js --out json=baseline_v1.0.0.json
```

---

## 7. Firewall Rules (If Enabling LAN Access)

**Only if you change `$HostBind="0.0.0.0"` in ship.ps1**

**Add Windows Firewall rules:**
```powershell
# Allow LLM server (port 8001)
New-NetFirewallRule -DisplayName "ASTRA LLM Server" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow

# Allow API server (port 8080)
New-NetFirewallRule -DisplayName "ASTRA API Server" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

**Remove rules (rollback):**
```powershell
Remove-NetFirewallRule -DisplayName "ASTRA LLM Server"
Remove-NetFirewallRule -DisplayName "ASTRA API Server"
```

---

## 8. Systemd Service (Linux Alternative)

**If running on Linux instead of Windows:**

Create `/etc/systemd/system/astra-llm.service`:
```ini
[Unit]
Description=ASTRA LLM Server (llama.cpp)
After=network.target

[Service]
Type=simple
User=astra
WorkingDirectory=/opt/astra
ExecStart=/opt/llama/llama-server --model /opt/models/gpt-oss-20b-q4_k_m.gguf --host 127.0.0.1 --port 8001 --ctx-size 131072
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/astra-api.service`:
```ini
[Unit]
Description=ASTRA Core API
After=network.target astra-llm.service
Requires=astra-llm.service

[Service]
Type=simple
User=astra
WorkingDirectory=/opt/astra
Environment="PATH=/opt/astra/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/astra/.venv/bin/python -m uvicorn src.astra.api.app:app --host 127.0.0.1 --port 8080
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable astra-llm astra-api
sudo systemctl start astra-llm astra-api
sudo systemctl status astra-llm astra-api
```

---

## 9. Automated Backup Script

**Create:** `scripts/backup_astra.ps1`

```powershell
param(
    [int]$RetainDays = 7
)

$BackupRoot = Join-Path $PSScriptRoot "..\backup"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupName = "astra_backup_$Timestamp.zip"
$BackupPath = Join-Path $BackupRoot $BackupName

# Create backup directory
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

# Backup critical files
Write-Host "Creating backup: $BackupName" -ForegroundColor Cyan
Compress-Archive -Path .\.env, .\data\, .\config\, .\ops\ -DestinationPath $BackupPath

# Cleanup old backups
$OldBackups = Get-ChildItem $BackupRoot -Filter "astra_backup_*.zip" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-$RetainDays)
}
foreach ($old in $OldBackups) {
    Write-Host "Removing old backup: $($old.Name)" -ForegroundColor Yellow
    Remove-Item $old.FullName
}

Write-Host "Backup complete: $BackupPath" -ForegroundColor Green
```

**Schedule (daily at 2 AM):**
```powershell
schtasks /create /tn "ASTRA Daily Backup" /tr "powershell -ExecutionPolicy Bypass -File X:\PROJECT_ASTRA_1.0\scripts\backup_astra.ps1" /sc daily /st 02:00
```

---

## 10. Health Check Monitoring (External)

**Setup external health checks:**

**Option A: UptimeRobot (Free)**
- URL: `http://127.0.0.1:8080/v1/system/health`
- Interval: 5 minutes
- Alert on: 2 consecutive failures

**Option B: Custom PowerShell script**

Create `scripts/health_monitor.ps1`:
```powershell
$Url = "http://127.0.0.1:8080/v1/system/health"
$Interval = 60  # seconds

while ($true) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        $status = ($response.Content | ConvertFrom-Json).status
        if ($status -eq "healthy") {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✓ HEALTHY" -ForegroundColor Green
        } else {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⚠ DEGRADED: $status" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✗ DOWN: $($_.Exception.Message)" -ForegroundColor Red
    }
    Start-Sleep -Seconds $Interval
}
```

**Run in background:**
```powershell
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File .\scripts\health_monitor.ps1" -WindowStyle Minimized
```

---

## Implementation Priority

**High Priority (Do within 24 hours):**
1. ✅ Enhanced .gitignore (DONE)
2. ✅ Cache efficiency alert (DONE)
3. ⏳ Disable docs in production (Option A ready)
4. ⏳ Schedule WAL checkpoint

**Medium Priority (Do within 1 week):**
5. Load testing baseline
6. Automated backup script
7. External health monitoring

**Low Priority (Nice to have):**
8. Firewall rules (only if LAN access needed)
9. Systemd services (Linux only)

---

## Verification Commands

**After applying each improvement:**

```powershell
# 1. Verify docs disabled
curl.exe http://127.0.0.1:8080/docs  # Should 404

# 2. Check scheduled tasks
schtasks /query /tn "ASTRA WAL Checkpoint"
schtasks /query /tn "ASTRA Daily Backup"

# 3. Test WAL checkpoint
python scripts\wal_checkpoint.py

# 4. Verify Prometheus alerts
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="astra_core")'

# 5. Check git ignore
git status --ignored

# 6. Run load test
k6 run scripts/loadtest_baseline.js

# 7. Test backup
.\scripts\backup_astra.ps1 -RetainDays 7
```

---

**Status:** All improvements documented and ready to apply post-deployment.

**ETA per item:** 5-15 minutes each

**Total hardening time:** ~2 hours for all improvements
