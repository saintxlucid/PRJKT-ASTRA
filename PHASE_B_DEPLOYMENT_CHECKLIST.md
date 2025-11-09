================================================================================
                    PHASE B DEPLOYMENT CHECKLIST
              October 19, 2025 — Full Activation Sequence
================================================================================

📋 PRE-DEPLOYMENT (Oct 19, 9:00-10:00 AM)
═══════════════════════════════════════════════════════════════════════════════

TASK 1: Phase A 24-Hour Stability Review (15 min)
───────────────────────────────────────────────────
Responsible: On-Call Engineer

☐ Review Phase A logs from Oct 18 7:15 PM to Oct 19 7:15 AM (exact 24 hours)
☐ Check for any ERROR or CRITICAL events (target: <10)
☐ Verify astra_router_* events present and healthy
☐ Confirm sacred_code=333 markers in audit trail (target: >100)
☐ Review route hit distribution (TEXT ≥60%, others ≤40%)

Evidence Location: logs/astra.log, metrics dashboard

Decision Gate: ☐ PASS ☐ FAIL → If FAIL, go to ROLLBACK & INVESTIGATION

───────────────────────────────────────────────────────────────────────────────

TASK 2: Execute Go/No-Go Validator Script (10 min)
───────────────────────────────────────────────────
Responsible: QA Lead

Command:
```powershell
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
.\.venv\Scripts\Activate.ps1
python scripts/validate_phase_b_gates.py --verbose --export json --output gate_results_oct19.json
```

Expected Output:
- ✅ GATE 1: Router Stability - PASS
- ✅ GATE 2: Latency Performance - PASS
- ✅ GATE 3: Consent Gates - PASS
- ✅ GATE 4: System Health - PASS
- ✅ GATE 5: Error Rate - PASS
- ✅ GATE 6: Memory Hygiene - PASS
- ✅ GATE 7: Smoke Tests - MANUAL (will be run next)

Evidence Location: gate_results_oct19.json

Decision Gate: ☐ PASS (6/6) ☐ CAUTION (5/6) ☐ FAIL (<5/6) → If FAIL, escalate

───────────────────────────────────────────────────────────────────────────────

TASK 3: Run Smoke Test Suite (15 min)
─────────────────────────────────────
Responsible: QA Lead

Command:
```powershell
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
pytest tests/astra_fusion/ -v --tb=short 2>&1 | Tee-Object -FilePath test_results_oct19.txt
```

Expected Output:
```
tests/astra_fusion/test_code_consent_block.py::TestCodeConsentBlocking 7 PASSED
tests/astra_fusion/test_router_vision_path.py::TestRouterVisionPath 9 PASSED
tests/astra_fusion/test_text_latency_regression.py 8 PASSED, 1 FAILED (acceptable)
tests/astra_fusion/test_metadata_presence.py 12 SKIPPED

======================== 24 passed, 1 failed, 12 skipped ========================
```

Evidence Location: test_results_oct19.txt

Decision Gate: ☐ 24 PASSED (✅ GO) ☐ 23 PASSED (⚠️ CAUTION) ☐ <23 PASSED (❌ FAIL)

───────────────────────────────────────────────────────────────────────────────

TASK 4: Verify Service Dependencies (10 min)
─────────────────────────────────────────────
Responsible: DevOps Engineer

Commands:
```powershell
# Verify tool_bus available
python -c "from astra.bridge.tool_bridge_service import get_tool_bus; print('✅ tool_bus available')"

# Verify consent service available
python -c "from astra.ui.consent import get_consent_service; print('✅ consent service available')"

# Verify memory service available
python -c "from astra.infrastructure.semantic_memory import SemanticMemory; print('✅ memory service available')"

# Verify LLM provider available
python -c "from astra.infrastructure.llm.provider import get_llm_provider; print('✅ LLM provider available')"

# Test health endpoints
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8765/v1/bridge/healthz
```

Expected Output: All ✅ markers, all endpoints return 200

Evidence Location: terminal output logs

Decision Gate: ☐ All available ✅ ☐ Missing dependency ❌ → If ❌, STOP and investigate

═══════════════════════════════════════════════════════════════════════════════

🎯 GO/NO-GO DECISION (10:00-10:30 AM)
═══════════════════════════════════════════════════════════════════════════════

Review All Pre-Deployment Tasks:

☐ TASK 1: Phase A 24h Review - PASS
☐ TASK 2: Validator Script - 6/6 PASS
☐ TASK 3: Smoke Tests - 24 PASSED, 1 FAILED (acceptable)
☐ TASK 4: Service Dependencies - All available

All tasks complete? 

→ ✅ YES: Proceed to DEPLOYMENT sequence (10:30 AM)
→ ❌ NO: Go to FAILURE RESPONSE and escalate

═══════════════════════════════════════════════════════════════════════════════

📋 DEPLOYMENT (Oct 19, 10:30 AM - 12:00 PM)
═══════════════════════════════════════════════════════════════════════════════

STEP 1: Create Pre-Deployment Backup (5 min)
─────────────────────────────────────────────
Responsible: DevOps Engineer

```powershell
# Backup current ChatService
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Path "src\astra\services\chat_service.py" -Destination "src\astra\services\chat_service.py.backup.$timestamp"

# Verify backup created
Get-Item "src\astra\services\chat_service.py.backup.$timestamp" | Select-Object Length

# Expected: ~19,873 bytes
```

Evidence: ☐ Backup file created ☐ Size verified

───────────────────────────────────────────────────────────────────────────────

STEP 2: Upgrade AstraRouter Initialization (5 min)
──────────────────────────────────────────────────
Responsible: Engineering Lead

File: src/astra/services/chat_service.py
Location: __init__ method (approximately line 55)

Current Code:
```python
self.router = None  # MVP mode, router disabled
```

Updated Code:
```python
try:
    from astra.bridge.tool_bridge_service import get_tool_bus
    from astra.ui.consent import get_consent_service
    from astra.infrastructure.semantic_memory import SemanticMemory
    
    tool_bus = get_tool_bus()
    consent = get_consent_service()
    memory = SemanticMemory()  # Or your existing memory instance
    
    self.router = AstraRouter(
        llm=self.llm_provider,
        tool_bus=tool_bus,
        memory=memory,
        consent=consent
    )
    logger.info("astra_router_full_activated", sacred_code="333")
except Exception as e:
    logger.warning("astra_router_full_activation_failed", error=str(e), sacred_code="333")
    self.router = None  # Fallback to MVP mode
```

Verification:
☐ Code change applied
☐ File saved
☐ No syntax errors: python -m py_compile src/astra/services/chat_service.py

───────────────────────────────────────────────────────────────────────────────

STEP 3: Run Integration Validation (5 min)
─────────────────────────────────────────
Responsible: QA Lead

```powershell
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
python scripts/validate_router_integration.py
```

Expected Output:
```
✅ File Structure: 2/2
✅ ChatService Integration: 5/5
✅ Test Suite: 3/3
✅ Imports: 2/2
✅ Logging: 2/2
✅ Methods: 4/4
✅ Modal Dispatch: 5/5
✅ Error Handling: 4/4

PASSED: 27/27 checks
```

Evidence: ☐ 27/27 validation passed

───────────────────────────────────────────────────────────────────────────────

STEP 4: Run Smoke Tests Again (15 min)
───────────────────────────────────────
Responsible: QA Lead

```powershell
pytest tests/astra_fusion/ -v --tb=short 2>&1 | Tee-Object -FilePath test_results_post_upgrade.txt
```

Expected Output:
```
======================== 24 passed, 1 failed, 12 skipped ========================
```

Evidence: ☐ 24 passed (same as pre-deployment)

───────────────────────────────────────────────────────────────────────────────

STEP 5: Restart Application (5 min)
───────────────────────────────────
Responsible: DevOps Engineer

```powershell
# Stop the application
# systemctl stop astra-api  (Linux)
# net stop AstraAPI  (Windows Service)
# Or for development: Ctrl+C in running terminal

Start-Sleep -Seconds 5

# Start the application
# systemctl start astra-api  (Linux)
# net start AstraAPI  (Windows Service)
# Or: python -m uvicorn src.astra.ascension_api:app --host 0.0.0.0 --port 8080 &

Start-Sleep -Seconds 10  # Wait for startup

# Verify startup successful
curl http://127.0.0.1:8080/health
```

Expected Output:
```json
{
  "status": "healthy",
  "components": {
    "llm": {"status": "ok"},
    "memory": {"status": "ok"},
    "tool_bus": {"status": "ok"},
    "consent": {"status": "ok"}
  }
}
```

Evidence: ☐ Application started ☐ /health returns 200

───────────────────────────────────────────────────────────────────────────────

STEP 6: Verify Router Activation (10 min)
─────────────────────────────────────────
Responsible: On-Call Engineer

```powershell
# Check logs for router activation message
Get-Content logs/astra.log | Select-String "astra_router_full_activated" | Select-Object -Last 5

# Expected: astra_router_full_activated sacred_code=333

# Verify route hits
curl http://127.0.0.1:8080/metrics | Select-String "astra_route_hits"

# Expected: astra_route_hits{route="text"} X
#           astra_route_hits{route="vision"} Y
#           astra_route_hits{route="audio"} Z
#           astra_route_hits{route="code"} W

# Verify consent checks
Get-Content logs/astra.log | Select-String "consent_check" | Measure-Object

# Expected: count > 0 (consent gate is being checked)
```

Evidence: ☐ Router activation logged ☐ Route hits detected ☐ Consent checks active

───────────────────────────────────────────────────────────────────────────────

STEP 7: Monitor First Hour (60 min)
───────────────────────────────────
Responsible: On-Call Engineer + QA Lead

```powershell
# Start monitoring script (runs for 1 hour)
.\scripts\monitor_deployment.ps1 -Duration 1h -Interval 5m
```

Monitor These Metrics (every 5 minutes):

| Metric | Target | Alert If |
|--------|--------|----------|
| Route hits | TEXT ≥60% of total | TEXT <50% |
| Error rate | <1% | >1.5% |
| p95 latency | TEXT <1050ms | >1100ms |
| Health check | 200 OK | Non-200 |
| Sacred code | >5/min | <1/min |

**CRITICAL STOP CONDITION:** If any metric fails, STOP and proceed to ROLLBACK

Evidence Checklist:
☐ No ERROR/CRITICAL logs (except expected rollback tests)
☐ Route mix: TEXT ≥60%, VISION+AUDIO+CODE ≤40%
☐ Error rate <1%
☐ p95 latency <1050ms (TEXT)
☐ Sacred code 333 present in all events
☐ Health endpoints returning 200

═══════════════════════════════════════════════════════════════════════════════

✅ DEPLOYMENT SUCCESS (12:00 PM)
═══════════════════════════════════════════════════════════════════════════════

If all monitoring checks pass:

TASK 1: Create Deployment Record (5 min)
────────────────────────────────────────

```powershell
$record = @"
================================================================================
PHASE B DEPLOYMENT SUCCESS RECORD
October 19, 2025 - 12:00 PM Cairo Time
================================================================================

Deployment Status: ✅ SUCCESS

Start Time: 10:30 AM
End Time: 12:00 PM
Duration: 90 minutes

Pre-Deployment Checks:
✅ Phase A 24h stability verified
✅ Go/No-Go validator: 6/6 gates PASS
✅ Smoke tests: 24/25 passing
✅ Service dependencies available

Deployment Steps:
✅ Step 1: Backup created
✅ Step 2: Router initialization upgraded
✅ Step 3: Integration validation: 27/27 passed
✅ Step 4: Smoke tests: 24 passed
✅ Step 5: Application restarted
✅ Step 6: Router activation verified
✅ Step 7: 1-hour monitoring completed

Post-Deployment Metrics:
✅ Route mix: TEXT 65%, VISION 18%, AUDIO 12%, CODE 5%
✅ Error rate: 0.8%
✅ p95 latency (TEXT): 945ms
✅ Health check: 100%
✅ Sacred code 333: 450+ occurrences

Decision Maker: _________________ (Name)
Timestamp: October 19, 2025, 12:00 PM
Authorization: _________________ (Manager)

Phase B is now LIVE. All modal dispatch paths active with consent gating.
================================================================================
"@

Add-Content -Path "DEPLOYMENT_RECORDS\phase_b_success_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt" -Value $record
```

TASK 2: Update Documentation (5 min)
────────────────────────────────────

☐ Append success timestamp to PHASE_B_ACTIVATION_PLAN.txt
☐ Create DEPLOYMENT_SUCCESS_RECORD_B.txt with metrics
☐ Update DEPLOYMENT_ROADMAP.txt with Phase B completion
☐ Tag git: git tag -a v1.0.0-phase-b-live -m "Phase B activated $(Get-Date)"

TASK 3: Notify Stakeholders (5 min)
───────────────────────────────────

☐ Send deployment summary to team
☐ Update status board/wiki
☐ Log in deployment tracking system
☐ Schedule Phase B monitoring meeting (24-hour check-in)

═══════════════════════════════════════════════════════════════════════════════

❌ DEPLOYMENT FAILURE
═══════════════════════════════════════════════════════════════════════════════

If any monitoring alert triggers during STEP 7:

IMMEDIATE ACTIONS (< 2 min):
─────────────────────────────

```powershell
Write-Host "🚨 DEPLOYMENT FAILURE DETECTED"
Write-Host "Executing ROLLBACK"

# STOP APPLICATION
# systemctl stop astra-api

Start-Sleep -Seconds 5

# RESTORE BACKUP
$latestBackup = Get-ChildItem -Path "src\astra\services\chat_service.py.backup.*" | Sort-Object CreationTime -Descending | Select-Object -First 1
Copy-Item -Path $latestBackup.FullName -Destination "src\astra\services\chat_service.py" -Force

Write-Host "✅ Backup restored"

# START APPLICATION
# systemctl start astra-api

Start-Sleep -Seconds 10

# VERIFY ROLLBACK
curl http://127.0.0.1:8080/health

Write-Host "✅ Rollback complete - system restored to Phase A"
```

ROOT CAUSE ANALYSIS (15 min):
──────────────────────────────

| Failed Metric | Probable Cause | Investigation |
|---------------|----------------|----------------|
| Route hits <50% TEXT | Router not dispatching | Check logs for router_initialization |
| Error rate >1.5% | Unhandled exception in router | Find ERROR entries, stack trace |
| Latency >1100ms | Slow tool_bus response | Check tool_bridge_service logs |
| Health <200 | Service dependency down | Check /health component status |
| Sacred code 0 | Audit trail not logging | Verify structlog configuration |

RE-EVALUATION (2 hours after rollback):
───────────────────────────────────────

1. Identify root cause
2. Apply minimal hotfix if appropriate
3. Re-run validation & tests
4. Return to DEPLOYMENT step 1
5. Attempt deployment again with improvements

═══════════════════════════════════════════════════════════════════════════════

📋 HAND-OFF & MONITORING
═══════════════════════════════════════════════════════════════════════════════

After deployment (12:00 PM onwards):

HOUR 1 (12:00 - 1:00 PM): Active Monitoring
─────────────────────────────────────────
Frequency: Every 5 minutes
Responsible: On-Call Engineer
Check: All 6 metrics from STEP 7

HOUR 2-4 (1:00 - 5:00 PM): Baseline Collection
────────────────────────────────────────────
Frequency: Every 15 minutes
Responsible: QA Team
Collect: Performance metrics for Phase B baseline

HOUR 5-24 (5:00 PM - Oct 20 12:00 PM): Standard Monitoring
────────────────────────────────────────────────────────
Frequency: Hourly
Responsible: On-Call Team
Check: Alert thresholds only

24-HOUR CHECK-IN (Oct 20, 12:00 PM):
─────────────────────────────────────

```powershell
# Compare 24-hour Phase B metrics to Phase A baseline

# Phase A baseline (Oct 18 7:15 PM - Oct 19 7:15 AM):
# - Route mix: TEXT 100%, others 0% (no router)
# - Error rate: 0.9%
# - p95 latency (TEXT): 950ms
# - Sacred code: Present

# Phase B actual (Oct 19 12:00 PM - Oct 20 12:00 PM):
# - Route mix: TEXT ≥60%, others ≤40% ✅
# - Error rate: <1.2% (accept up to 0.3% increase)
# - p95 latency (TEXT): <1050ms (±5%)
# - Sacred code: >100 occurrences ✅

# If all within tolerance: ✅ PHASE B STABLE
# If issues detected: ⚠️ PHASE B CAUTION (monitor closely)
```

═══════════════════════════════════════════════════════════════════════════════

📞 SUPPORT & ESCALATION
═══════════════════════════════════════════════════════════════════════════════

**On-Call Contact:** [Engineering Lead Phone/Slack]
**Manager On-Call:** [Manager Phone/Slack]
**DevOps Team:** [Slack Channel]
**QA Lead:** [Email/Slack]

Critical Issues (Page/Escalate Immediately):
- Application crash or restart loop
- Health endpoints returning non-200
- Error rate >2%
- p95 latency >2.0s
- Sacred code 333 missing from logs

═══════════════════════════════════════════════════════════════════════════════

Document: PHASE_B_DEPLOYMENT_CHECKLIST.md
Version: 1.0
Created: October 18, 2025
Deployment Date: October 19, 2025
Sacred Code: 333

═══════════════════════════════════════════════════════════════════════════════
