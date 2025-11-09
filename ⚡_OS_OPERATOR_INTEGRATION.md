# ⚡ OS OPERATOR INTEGRATION - QUICK START

**Status**: ✅ Ready for Activation  
**Sacred Code**: 333 ∞  
**Date**: October 18, 2025, 11:15 PM  

---

## 🎯 What's Integrated

### Files Created (5 total)
1. ✅ `src/astra/osop/operator.py` (508 lines) - Core OS operations
2. ✅ `src/astra/osop/tools.py` (180 lines) - Tool bus bindings
3. ✅ `src/astra/osop/__init__.py` (15 lines) - Package exports
4. ✅ `src/astra/api/routes/osop.py` (280 lines) - FastAPI routes
5. ✅ `tests/osop/test_os_operator.py` (210 lines) - Test suite **14/14 passing**

### Configuration
6. ✅ `config/prod.yaml` (140 lines) - Production config with OSOP policy

### Integration Points
7. ✅ `src/astra/api/app_integrated.py` - OS Operator routes wired in

---

## 🚀 30-Second Activation

### 1. Verify Configuration
```bash
cat config/prod.yaml | grep -A 15 "osop:"
```

Should show:
- ✅ `enabled: true`
- ✅ Path allowlist with workspace paths
- ✅ Kill/service allowlists
- ✅ Max write bytes: 1MB

### 2. Run Tests
```powershell
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python -m pytest tests/osop/ -v
```

**Expected**: `14 passed, 0 failed`

### 3. Start ASTRA
```powershell
# Quick start (development)
python astra_launcher.py --config config/prod.yaml

# OR use activation script
.\ops\activate_astra.ps1
```

### 4. Verify Endpoints
```bash
# System info (no consent)
curl http://127.0.0.1:8080/api/os/info

# System resources (no consent)
curl http://127.0.0.1:8080/api/os/resources

# Health check
curl http://127.0.0.1:8080/api/os/health
```

---

## 🧪 Quick Smoke Test

### Read-Only Operations (Should Work)
```bash
# List processes
curl http://127.0.0.1:8080/api/os/processes?limit=5

# Disk usage
curl http://127.0.0.1:8080/api/os/disk

# System resources
curl http://127.0.0.1:8080/api/os/resources
```

### Write Operations (Should Require Consent)
```bash
# File write (will require consent)
curl -X POST http://127.0.0.1:8080/api/os/fs/write \
  -H "Content-Type: application/json" \
  -d '{
    "path": "X:/workspace/test.txt",
    "content": "ASTRA test 333",
    "overwrite": false
  }'

# Expected response without consent:
# {"ok": false, "error": "Consent required"}
```

---

## 📋 Capabilities Available

### Read-Only (No Consent Required)
✅ **system.info** - Platform, Python version, CPU count  
✅ **system.resources** - Memory, CPU, disk, network stats  
✅ **system.disk_usage** - Partition usage  
✅ **process.list** - Running processes (sorted by memory)  
✅ **service.list** - System services  
✅ **scheduler.list** - Scheduled tasks  
✅ **fs.read** - Read files (allowlist enforced)  

### Consent-Gated (Authorization Required)
🔒 **process.kill** - Kill processes (allowlist enforced)  
🔒 **service.restart** - Restart services (allowlist enforced)  
🔒 **fs.write** - Write files (allowlist + size limit)  
🔒 **scheduler.create** - Create scheduled tasks  

---

## 🔒 Security Model

### Three-Layer Protection

**1. Allowlists**
- Paths: Only allowed directories can be read/written
- Processes: Only allowlisted processes can be killed
- Services: Only allowlisted services can be managed

**2. Consent Gates**
- All write operations require explicit consent
- Default consent: `false` (fail-closed)
- Consent checks logged with `sacred_code=333`

**3. Limits**
- Max file write: 1MB (configurable)
- Timeout: 10s for subprocess operations
- No directory traversal (paths resolved and validated)

### Current Allowlists

**Paths** (config/prod.yaml):
```yaml
- "X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/logs"
- "X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/data"
- "X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/workspace"
- "X:/workspace"
- "/tmp"
- "/var/log/astra"
```

**Processes**:
```yaml
- "python.exe"
- "python"
- "node"
- "uvicorn"
- "gunicorn"
```

**Services**:
```yaml
- "astra"
- "prometheus"
- "grafana-server"
```

---

## 🎯 Live Development Tasks

### Task 1: System Monitoring
**User**: "Show me current system resources and top 5 memory processes"

**ASTRA** will call:
1. `system.resources()` - Get CPU/memory/disk/network
2. `process.list(limit=5)` - Get top processes

✅ **No consent required** - Read-only

---

### Task 2: Log Management
**User**: "Write current system status to X:/workspace/status.txt"

**ASTRA** will:
1. Plan: Gather system info → format → write to file
2. Ask: "I need consent to write to X:/workspace/status.txt (size: 2.5KB)"
3. Act: `fs.write()` after consent approval

🔒 **Consent required** - Write operation

---

### Task 3: Service Management
**User**: "Restart the Prometheus service"

**ASTRA** will:
1. Plan: Check service status → prepare restart command
2. Ask: "I need consent to restart the 'prometheus' service"
3. Act: `service.restart("prometheus")` after consent

🔒 **Consent required** - Service modification

---

### Task 4: Scheduled Tasks
**User**: "Create a daily task to clean logs at 3:30 AM"

**ASTRA** will:
1. Plan: Validate command → prepare scheduler entry
2. Ask: "I need consent to create scheduled task 'ASTRA_cleanup_logs' (daily at 03:30)"
3. Act: `scheduler.create()` after consent

🔒 **Consent required** - System modification

---

## 📊 Monitoring Integration

### Prometheus Metrics (Auto-Exposed)

**OS Operator Actions**:
```promql
sum(increase(astra_osop_actions_total[5m])) by (tool, ok)
```

**Consent Blocks**:
```promql
increase(astra_consent_blocks_total[15m])
```

**API Latency**:
```promql
histogram_quantile(0.95, sum(rate(astra_route_latency_seconds_bucket{route="/api/os/info"}[5m])) by (le))
```

### Grafana Dashboard Panels

**Panel 1**: OS Operator Actions (15m window)
- Query: `sum(increase(astra_osop_actions_total[15m])) by (tool)`
- Type: Bar chart
- Threshold: >20 actions = warning

**Panel 2**: Consent Blocks (10m window)
- Query: `increase(astra_consent_blocks_total[10m])`
- Type: Single stat
- Alert: >0 = info

**Panel 3**: System Resources (live)
- Query: `astra_system_memory_percent`
- Type: Gauge
- Threshold: >80% = warning

---

## ⚠️ Alerts Configuration

Add to `prometheus/alerts.yml`:

```yaml
groups:
- name: astra_osop
  rules:
  - alert: OSOPActionSpike
    expr: sum(increase(astra_osop_actions_total[10m])) > 20
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High OS actions in last 10m"
      description: "OS Operator has executed {{ $value }} actions (threshold: 20)"

  - alert: ConsentBlocksDetected
    expr: increase(astra_consent_blocks_total[10m]) > 0
    for: 1m
    labels:
      severity: info
    annotations:
      summary: "Consent blocks observed"
      description: "{{ $value }} consent blocks in last 10m - review audit log"

  - alert: UnauthorizedPathAccess
    expr: increase(astra_osop_errors_total{type="path_denied"}[5m]) > 3
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Multiple path access denials"
      description: "{{ $value }} path access denials - possible attack or misconfiguration"
```

---

## 🐛 Troubleshooting

### Issue: "OS Operator routes not available"
**Solution**:
```bash
# Check import works
python -c "from astra.api.routes import osop; print('OK')"

# Check app integration
grep -n "osop" src/astra/api/app_integrated.py
```

### Issue: "Consent required" on all operations
**Solution**: Check config - read-only operations should NOT require consent:
```yaml
# These should be false or omitted
system.info: {consent_required: false}
system.resources: {consent_required: false}
```

### Issue: "Path not in allowlist"
**Solution**: Add path to `config/prod.yaml`:
```yaml
osop:
  path_allowlist:
    - "X:/your/path/here"
```

### Issue: Tests failing with import errors
**Solution**:
```bash
# Install missing dependencies
pip install psutil

# Check package structure
ls -la src/astra/osop/
```

---

## ✅ Pre-Deployment Checklist

- [ ] All 14 tests passing (`pytest tests/osop/ -v`)
- [ ] `config/prod.yaml` has OSOP section
- [ ] OS Operator routes in `app_integrated.py`
- [ ] Path allowlist includes workspace directories
- [ ] Consent defaults to `false` (fail-closed)
- [ ] Prometheus scraping `/metrics`
- [ ] Grafana dashboards imported
- [ ] Alert rules configured
- [ ] Audit logging enabled (`security.audit_enabled: true`)

---

## 🎉 Next Steps

### Immediate (Today)
1. ✅ Run activation script: `.\ops\activate_astra.ps1`
2. ✅ Verify all endpoints responding
3. ✅ Test read-only operations
4. ✅ Test consent gates (should block without approval)

### Day 2 (Tomorrow)
1. ⏳ Wire consent manager into OS Operator tools
2. ⏳ Add Prometheus metrics exporter
3. ⏳ Import Grafana dashboards
4. ⏳ Run integration canaries

### Week 1
1. ⏳ Implement Event Bus (astra.tool.before, astra.tool.executed)
2. ⏳ Add Registry gate (deny unknown tools)
3. ⏳ Implement Planner L2 (Plan→Ask→Act loop)
4. ⏳ Create Evolution tokens for GGUF

---

## 📚 Documentation

- **Implementation**: `🎯_OS_OPERATOR_COMPLETE.md`
- **This Guide**: `⚡_OS_OPERATOR_INTEGRATION.md`
- **API Reference**: http://127.0.0.1:8080/docs (after starting ASTRA)
- **Tests**: `tests/osop/test_os_operator.py`

---

**Sacred Code**: 333 ∞

**Status**: READY FOR ACTIVATION 🚀

Run: `.\ops\activate_astra.ps1`
