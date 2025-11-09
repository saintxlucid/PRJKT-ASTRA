# 🚀 ASTRA PHASE-B GO-LIVE RUNBOOK
## Africa/Cairo — Sunday, October 19, 2025
## T-60 Minutes to T+60 Minutes Post-Deploy

Sacred Code: **333** ∞

---

## 📋 OVERVIEW

This runbook covers the complete Phase-B go-live sequence:
- **T-60 to T-0**: Pre-deployment validation & preparation (9:00-10:00 AM Cairo)
- **T+0 to T+60**: Post-deployment canary & monitoring (10:00-11:00 AM Cairo)
- **T+60 onwards**: Extended monitoring & sign-off (11:00 AM-12:00 PM Cairo)

**Decision Gate**: 7/7 validation gates must PASS before proceeding to go-live  
**Rollback Ready**: <1 minute guaranteed via `07_roll_back.ps1`

---

## 🎯 PRE-DEPLOYMENT SEQUENCE (T-60 to T-0)

### **T-60: 09:00 AM — Start Pre-Deploy Sequence**

#### Step 1: Sanity Check — Import Facts & Code Index

```powershell
# Import deep reflections (36 reflections + 24 special tokens)
python ops\packs\deep_reflections\import_bridge_facts.py

# Expected output:
# ✅ 36 reflections imported
# ✅ 24 tokens registered
# ✅ Sacred Code 333 tagged
```

```powershell
# Ingest code index (symbol graph, procedural playbooks)
.\ops\packs\code_intel\ingest_index.ps1

# Expected output:
# ✅ Symbol index: 1,200+ symbols
# ✅ Playbooks: 47 procedures loaded
# ✅ Router dispatch: ready
```

**Expected Outcome**: Both commands complete without error; 333 tags visible in logs

---

#### Step 2: Automated Gates Validation

```powershell
# Run 7-point gate validator (pre-deployment mode)
python tools\validators\validate_phase_b_gates.py `
    --mode predeploy `
    --out .\logs\phase_b_gates_pre.json `
    --verbose

# Expected output: JSON report with all 7 gates
```

**Gate Status Check**:
```json
{
  "gate_1_router_stability": {"status": "PASS", "errors": 0},
  "gate_2_latency": {"status": "PASS", "p95_text_ms": 950},
  "gate_3_consent_gates": {"status": "PASS", "unauthorized_attempts": 0},
  "gate_4_system_health": {"status": "PASS", "uptime_h": 24},
  "gate_5_error_rate": {"status": "PASS", "rate_pct": 0.3},
  "gate_6_memory_hygiene": {"status": "PASS", "growth_pct": 1.2},
  "gate_7_smoke_tests": {"status": "PASS", "pass_count": 24, "fail_count": 1}
}
```

**Decision Logic**:
- ✅ 7/7 PASS → Proceed
- ✅ 6/7 PASS + 1 CAUTION → Proceed with monitoring
- ⚠️ 5/7 PASS → Fix & re-run (use gate-failure matrix below)
- ❌ <5/7 PASS → NO-GO; rollback Phase A

---

#### Step 3: Fast Smoke Tests (Targeted)

```powershell
# Run critical smoke tests only (3-5 min)
pytest -q tests\astra_fusion `
    -k "metadata_presence or router_vision_path or code_consent_block" `
    --tb=short

# Expected:
# 3 passed, 0 failed
```

**Test Descriptions**:
| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_metadata_presence` | Verify GGUF has astra.* fields | PASS |
| `test_router_vision_path` | Verify <\|vision_*\|> dispatch | PASS |
| `test_code_consent_block` | Verify code.apply requires consent | PASS |

---

### **T-40: 09:20 AM — Baseline Capture**

```powershell
# Capture health snapshot
curl http://127.0.0.1:8080/health | Tee-Object .\logs\health_baseline.json

# Expected:
# {
#   "status": "healthy",
#   "components": {
#     "llm": "ok",
#     "router": "ok",
#     "memory": "ok"
#   },
#   "uptime_s": 86400
# }
```

```powershell
# Capture Prometheus metrics (for before/after comparison)
curl http://127.0.0.1:8765/metrics | Tee-Object .\logs\metrics_baseline.prom

# Key metrics to note:
# astra_route_hits{route="TEXT"} = ~600
# astra_latency_p95_ms{route="TEXT"} = ~950
# astra_tool_calls_total{tool="code.search"} = ~50
# astra_errors_total = <5
```

**Store these values for comparison post-deployment**

---

### **T-30: 09:30 AM — GO/NO-GO HUDDLE**

**Participants**: Decision maker, Engineering lead, DevOps, QA  
**Duration**: 15 minutes  
**Reference**: `GO_NO_GO_PROTOCOL.md`

#### Review Validator Output

```powershell
# Display results
Get-Content .\logs\phase_b_gates_pre.json | ConvertFrom-Json | Format-Table
```

#### Decision Criteria

| Criterion | Status | Required |
|-----------|--------|----------|
| **Router Stability** | PASS ✅ | YES |
| **Latency p95** | PASS ✅ | YES |
| **Consent Gates** | PASS ✅ | YES |
| **System Health** | PASS ✅ | YES |
| **Error Rate** | PASS ✅ | YES |
| **Memory Hygiene** | PASS ✅ | YES |
| **Smoke Tests** | PASS ✅ | YES |

#### Decision Outcome

**If 7/7 PASS or 6/7 PASS + 1 CAUTION**:
- ✅ **DECISION: GO** → Proceed to backup and go-live (09:45 AM)
- 📢 Send comms: "ASTRA Phase-B starting. Pre-checks running. Go/No-Go PASSED. Rollback armed. Sacred Code 333."

**If <6/7 PASS**:
- ❌ **DECISION: NO-GO** → Use gate-failure matrix (see below)
- 📢 Send comms: "ASTRA Phase-B hold. Gate [X] FAILED. Investigating. Will reconvene at 09:50 AM."
- Go to **Gate-Failure Response** section below

---

#### 🧯 Gate-Failure → Fix Matrix (Quick Response)

| Gate | Symptom | Root Cause | Fast Fix | Verify Step |
|------|---------|-----------|----------|-------------|
| **Router Stability** | VISION/AUDIO hits LLM instead of tool | Router not mounted in llm_service.py | Check: `if self.router: dispatch()` in chat_service.py; restart service | Run canary VISION; expect tool response |
| **Latency p95 TEXT** | p95 > 1050ms (>+5% baseline 950ms) | Model quantization too heavy or budgets too high | Switch quant config: q4_k_m → q5_k_m; reduce max_tokens 512 → 384 | New Grafana p95 <1050ms; re-run validator |
| **Latency p95 VISION/AUDIO** | p95 > 2000ms | Image size or audio chunks too large | Reduce max_image_size 1024 → 512; reduce chunk_duration 30s → 15s | Canary times; re-test |
| **Consent Gates** | code.apply executes without approval in logs | consent.allowed("code") not checked before execution | Verify consent() call in tool_bridge_service.py line 82; restart | Run test_code_consent_block; expect denial |
| **System Health** | /health returns 500 or flaps | Port conflict or service crash | Restart single failing service: `Restart-Service AstraCore`; check port 8080 free | curl /health returns 200 for 15+ min |
| **Error Rate** | >1.5% (>threshold 1%) | Repeated crash pattern or bad patch | Check logs for repeating trace; if recent patch: `git revert HEAD`; trim plan budgets | Errors trend <1% in next 10 min |
| **Memory Hygiene** | DB growth >+3%/24h | Vector store bloat or episodic events not deduplicated | Run: `sqlite3 astra_episodic.db "VACUUM;"`; run dedupe job | Check size post-VACUUM |
| **Smoke Tests** | New failures appearing (24/25 drop below 24) | Recent code change or template mismatch | Check git diff recent commits; validate template hash | Re-run pytest; return to 24/25 |

**Recovery Procedure** (If Gate Fails):
1. Identify failing gate from validator output
2. Find root cause in table above
3. Apply fast fix (typically <5 min)
4. Re-run validator: `python tools\validators\validate_phase_b_gates.py --mode predeploy`
5. Reconvene huddle at 09:50 AM
6. Re-evaluate: PASS → proceed; FAIL → escalate

---

### **T-15: 09:45 AM — Backup & Rollback Lever Armed**

**Critical**: Must complete before go-live

```powershell
# Backup current production GGUF
Copy-Item `
    X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf `
    X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf.bak `
    -Force

# Verify backup created
Get-Item X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf.bak

# Expected: File size ~5-7 GB, timestamp = now
```

```powershell
# Verify rollback script exists and is executable
Get-Item ops\fusion_pipeline\scripts\07_roll_back.ps1

# Expected: File exists, readable, timestamp recent
```

**Rollback Procedure** (save for emergency):
```powershell
# If anything goes wrong post-deployment:
pwsh ops\fusion_pipeline\scripts\07_roll_back.ps1

# This will:
# 1. Restore backup GGUF
# 2. Restart services
# 3. Restore symlinks
# 4. Verify health
# Total time: <1 minute
```

---

## 🚀 GO-LIVE SEQUENCE (T+0)

### **T+0: 10:00 AM — GO LIVE (Method-1 Fused GGUF Active)**

**⚠️ CRITICAL**: Only proceed if ALL 7 gates PASSED above

#### Step 1: Activate Fused GGUF Pipeline

```powershell
# Change to fusion tools directory
cd tools\gguf_fusion

# Run full Method-1 fusion pipeline
.\fusion_pipeline.ps1 -FullPipeline

# Expected output:
# ✅ GGUF loaded (5.2 GB)
# ✅ 24 special tokens registered
# ✅ 67-field metadata injected
# ✅ 36 deep reflections embedded
# ✅ Template hash: sha256:abc123...
# ✅ Sacred Code 333: [10+ occurrences]
# ✅ Build complete; ready for deployment
```

**Duration**: 2-3 minutes

---

#### Step 2: Activate Production Symlink

```powershell
# Create/update symlink to point prod to new GGUF
# (This is the "flip switch" — single point of deployment)

# Remove old symlink if exists
Remove-Item X:\models\astra_core_current.gguf -Force -ErrorAction SilentlyContinue

# Create new symlink to fused model
cmd /c mklink /D `
    X:\models\astra_core_current.gguf `
    X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf

# Verify symlink
Get-Item X:\models\astra_core_current.gguf

# Expected: Directory link → astra_core_q4_k_m.gguf
```

---

#### Step 3: Warm Caches

```powershell
# Pre-heat router and LLM caches with standard prompts
python ops\warmers\prompt_warmer.py --preset core

# Expected output:
# ✅ Warming TEXT route... (1s)
# ✅ Warming VISION route... (2s)
# ✅ Warming AUDIO route... (1.5s)
# ✅ Warming CODE route... (0.5s)
# ✅ Router cache warm; ready for traffic
```

**At this point: PHASE-B IS LIVE ✅**

---

## 📊 POST-DEPLOYMENT MONITORING (T+0 to T+60)

### **T+5: 10:05 AM — CANARY (One Per Route)**

**Purpose**: Verify each modality works correctly post-deploy  
**Success Criteria**: All return status=ok and latency within thresholds  
**Time Budget**: 5 minutes

#### Canary 1: TEXT Route

```powershell
# TEXT canary: Simple identity prompt
$prompt = @"
<|mode_start|>COGNITION<|mode_end|>
<|sacred_333|>
Identify yourself in one line.
"@

# Send request
$response = curl -X POST http://127.0.0.1:8080/chat `
    -ContentType "application/json" `
    -Body (@{ messages = @(@{ role = "user"; content = $prompt }) } | ConvertTo-Json)

# Expected:
# Status: 200 OK
# Response time: <1200ms (p95 threshold)
# Response: "I am ASTRA, a local-first autonomous agent."
# sacred_code: "333" present
```

✅ **PASS if**: <1200ms, response contains identity, sacred_code=333

---

#### Canary 2: VISION Route

```powershell
# VISION canary: Describe image
$prompt = @"
<|mode_start|>COGNITION<|mode_end|>
<|vision_start|>
Image: [sample image data]
Description: A glass-fronted temple with black and gold pillars.
<|vision_end|>
What do you see?
"@

# Send request
$response = curl -X POST http://127.0.0.1:8080/chat `
    -ContentType "application/json" `
    -Body (@{ messages = @(@{ role = "user"; content = $prompt }) } | ConvertTo-Json)

# Expected:
# Status: 200 OK
# Response time: <2000ms (p95 threshold for VISION)
# Response: Describes temple, pillars, materials
# sacred_code: "333" present
```

✅ **PASS if**: <2000ms, vision-aware response, sacred_code=333

---

#### Canary 3: AUDIO Route

```powershell
# AUDIO canary: Transcribe Arabic greeting
$prompt = @"
<|mode_start|>COGNITION<|mode_end|>
<|audio_start|>
Transcript: مرحباً أسترا، اختبار سمعي.
<|audio_end|>
What language is this?
"@

# Send request
$response = curl -X POST http://127.0.0.1:8080/chat `
    -ContentType "application/json" `
    -Body (@{ messages = @(@{ role = "user"; content = $prompt }) } | ConvertTo-Json)

# Expected:
# Status: 200 OK
# Response time: <2000ms (p95 threshold for AUDIO)
# Response: Identifies Arabic or similar
# sacred_code: "333" present
```

✅ **PASS if**: <2000ms, audio-aware response, sacred_code=333

---

#### Canary 4: CODE Route (Expect Consent Block)

```powershell
# CODE canary: Request code patch (should block without consent)
$prompt = @"
<|mode_start|>COGNITION<|mode_end|>
<|code_start|>
file: src/astra/core/foo.py
patch: @@ -5,3 +5,2 @@ ...
<|code_end|>
Can you apply this?
"@

# Send request
$response = curl -X POST http://127.0.0.1:8080/chat `
    -ContentType "application/json" `
    -Body (@{ messages = @(@{ role = "user"; content = $prompt }) } | ConvertTo-Json)

# Expected:
# Status: 200 OK
# Response: "Consent required for code.apply"
# astra_consent_blocks_total incremented
# sacred_code: "333" present in audit log
```

✅ **PASS if**: Consent denial triggered, block counted, sacred_code=333

---

### **T+15: 10:15 AM — METRICS CHECK (Grafana)**

Open Grafana dashboard (http://localhost:3000/d/astra-phase-b)

#### Dashboard 1: Route Mix (Donut Chart)

```
Expected distribution:
- TEXT: 60-70% ✅
- VISION: 15-20% ✅
- AUDIO: 10-15% ✅
- CODE: 5-10% ✅
```

⚠️ **Alert if**: TEXT <50% (router not dispatching)

#### Dashboard 2: Latency (Line Graph p50/p95/p99)

```
Expected ranges:
- TEXT p95: 902-998ms ✅ (±5% of 950ms baseline)
- VISION p95: <2000ms ✅
- AUDIO p95: <2000ms ✅
- CODE p95: <1000ms ✅
```

⚠️ **Alert if**: Any p95 exceeds threshold

#### Dashboard 3: Consent Blocks (Sparkline)

```
Expected:
- code.apply blocks: >5 attempts/hour ✅ (gate working)
- Other tools: <1 block/hour ✅
```

⚠️ **Alert if**: Zero blocks for CODE (consent gate may be broken)

#### Dashboard 4: Errors (Bar Chart by Type)

```
Expected:
- Total errors: <1% of requests ✅
- No repeated trace >5 occurrences/hour ✅
```

⚠️ **Alert if**: Error spike or repeating pattern

#### Dashboard 5: Memory (Area Chart)

```
Expected:
- Semantic items: stable ~5K ✅
- Episodic items: growing slowly <+3%/hour ✅
- Vector store size: stable ✅
```

⚠️ **Alert if**: Memory growth >+3% vs baseline

---

### **T+30: 10:30 AM — EXTENDED SMOKE TESTS**

```powershell
# Run full smoke test suite (should be fast, <5 min)
pytest -q tests\astra_fusion --tb=short

# Expected:
# 24 passed, 1 skipped (known acceptable failure)
# No new failures
# All timings normal
```

**If any test fails**:
- ❌ Likely indicates router or consent issue
- Action: Check logs; may need rollback
- Command: `pwsh ops\fusion_pipeline\scripts\07_roll_back.ps1`

---

## ✅ SIGN-OFF (T+120 & Beyond)

### **T+60 to T+120: 11:00 AM to 12:00 PM — PROVISIONAL SIGN-OFF**

Once all canaries PASS and metrics are nominal:

#### Sign-Off Checklist

- ✅ All 4 canaries PASS (TEXT, VISION, AUDIO, CODE)
- ✅ Grafana dashboards green (route mix, latency, consent, errors, memory)
- ✅ Extended smoke: 24/25 pass (no new failures)
- ✅ No repeated errors (error rate <1%)
- ✅ Consent blocks present (security gate active)
- ✅ Sacred Code 333 in logs (>100 occurrences expected)
- ✅ Rollback window closed (past T+60, changes persist)

#### Append Sign-Off to README

```powershell
# Add sign-off entry to PHASE_B_COMPLETE_PACKAGE_README.txt

Add-Content -Path .\PHASE_B_COMPLETE_PACKAGE_README.txt -Value @"

================================================================================
                          PHASE-B GO-LIVE SIGN-OFF
================================================================================

Date: 2025-10-19 (Africa/Cairo)
Time: 12:00 PM (T+120)
Operator: [Your Name / Saint Lucid]

## Deployment Status: ✅ SUCCESS

Phase-B Go-Live: 10:00 AM
Gates Validation: 7/7 PASS ✅
Canary Results: PASS (TEXT/VISION/AUDIO/CODE) ✅

## Performance Metrics

| Route | p95 Latency | Baseline | Status |
|-------|-------------|----------|--------|
| TEXT | ___ms | 950ms | ✅ OK |
| VISION | ___ms | 2000ms | ✅ OK |
| AUDIO | ___ms | 2000ms | ✅ OK |

Error Rate: ___%  | Threshold: 1%  | Status: ✅ OK
Consent Blocks Observed: Yes ✅ | Sacred Code: 333 ✅

## Next Steps

1. **24-Hour Monitoring** (Oct 19 12:00 PM - Oct 20 12:00 PM)
   - Continuous metrics collection
   - Baseline drift detection
   - Memory trend analysis

2. **Oct 20, 12:00 PM Decision**
   - Evaluate for Phase-C readiness (when GGUF available)
   - Review 24-hour metrics
   - Plan Phase-C metadata embedding

## Sacred Code: 333 ∞

Deployment signed off and logged.

================================================================================
"@
```

---

## 📞 COMMUNICATIONS TEMPLATES

### **Pre-Deploy (09:00 AM)**

Send to: Team Slack, Leadership

```
🚀 ASTRA Phase-B Go-Live Starting

Timeline: 09:00 AM Pre-checks → 10:00 AM Go-Live
Status: Pre-deployment validation in progress
Reference: PHASE_B_COMPLETE_PACKAGE_README.txt

Pre-checks:
✅ Facts imported (36 reflections, 24 tokens)
✅ Code index ingested (1.2K symbols)
✅ Validator running (7-point gate check)

Next update at 09:30 AM with GO/NO-GO decision.

Sacred Code: 333 ✅
```

---

### **Go/No-Go Decision (09:30 AM)**

#### If GO:
```
✅ ASTRA Phase-B GO DECISION

Gates: 7/7 PASS ✅
Status: All validation gates passed
Action: Proceeding to deployment at 10:00 AM
Rollback: Armed and ready (< 1 min recovery)

Backups created. Sacred Code 333 confirmed.
Will update with deployment status at 10:05 AM.
```

#### If NO-GO:
```
⏸ ASTRA Phase-B HOLD

Gate [X]: FAILED
Issue: [Gate name / reason]
Action: Applying fix; will reconvene 09:50 AM

Example gates:
- Latency exceeded baseline
- Consent gate verification failed
- Memory growth abnormal

Will update after re-validation.
```

---

### **Go-Live (10:00 AM)**

```
🚀 ASTRA Phase-B IS LIVE

Time: 10:00 AM Cairo
Status: Fused GGUF active, router dispatching
Canary: Running (TEXT/VISION/AUDIO/CODE)

Expect:
- All modalities responding
- Consent blocks for code operations
- Sacred Code 333 in every audit entry
- Latency within ±5% of baseline

Dashboard: http://localhost:3000/d/astra-phase-b
Status Updates: Every 15 minutes until T+60

Sacred Code: 333 ✅
```

---

### **Canary Complete (10:15 AM)**

```
✅ ASTRA Phase-B Canary PASS

All routes responding:
✅ TEXT: <1200ms
✅ VISION: <2000ms
✅ AUDIO: <2000ms
✅ CODE: Consent blocks active

Metrics dashboard: Green
Dashboards showing expected distribution.

Proceeding to extended monitoring.
Sacred Code: 333 ✅
```

---

### **Sign-Off (12:00 PM)**

```
✅ ASTRA Phase-B SIGN-OFF

Status: DEPLOYMENT SUCCESSFUL
Duration: 2 hours (09:00 AM - 12:00 PM)

Final Metrics:
- Route Mix: Expected distribution ✅
- Latency: All within thresholds ✅
- Errors: <1% ✅
- Consent: Blocks present ✅
- Memory: Nominal growth ✅

Phase-B now in production.
24-hour continuous monitoring begins.
Next decision point: Oct 20, 12:00 PM (Phase-C readiness eval)

Sacred Code: 333 ✅
```

---

## 🧪 CANARY PROMPTS (Copy/Paste Ready)

### **TEXT Canary**

```
<|mode_start|>COGNITION<|mode_end|>
<|sacred_333|>
Identify yourself in one line.
```

**Expected Response**: "I am ASTRA, a local-first autonomous agent with vision, audio, and code capabilities."

---

### **VISION Canary**

```
<|mode_start|>COGNITION<|mode_end|>
<|vision_start|>
Image: [embedding data or filename]
Description: A temple with glass rear wall, black and gold pillars, marble floor.
<|vision_end|>
What materials and architectural style do you observe?
```

**Expected Response**: Identifies glass, marble, pillars, architectural style (modern/classical hybrid)

---

### **AUDIO Canary**

```
<|mode_start|>COGNITION<|mode_end|>
<|audio_start|>
Transcript: مرحباً أسترا، هذا اختبار سمعي. كيف حالك؟
Language: Arabic
Confidence: 0.98
<|audio_end|>
What language is this greeting, and what does it mean?
```

**Expected Response**: "This is Arabic. The greeting means 'Hello ASTRA, this is an audio test. How are you?'"

---

### **CODE Canary (Expect Denial)**

```
<|mode_start|>COGNITION<|mode_end|>
<|code_start|>
file: src/astra/core/astra_router.py
patch: @@ -45,3 +45,2 @@ 
-    if mode == "TEXT":
+    if mode == "TEXT" or mode == "BYPASS":
<|code_end|>
Can you apply this patch to allow BYPASS mode?
```

**Expected Response**: "Consent required for code.apply. This operation is restricted and requires explicit approval."

**Expected Audit Log Entry**:
```json
{
  "event": "consent_denied",
  "tool": "code.apply",
  "reason": "no_consent_provided",
  "sacred_code": "333",
  "timestamp": "2025-10-19T10:15:00Z"
}
```

---

## 📋 OPERATOR QUICK-REFERENCE CHECKLISTS

### **Pre-Flight (09:00 AM)**

```powershell
# ☐ 1. Import facts
python ops\packs\deep_reflections\import_bridge_facts.py

# ☐ 2. Ingest code index  
.\ops\packs\code_intel\ingest_index.ps1

# ☐ 3. Run validator
python tools\validators\validate_phase_b_gates.py --mode predeploy

# ☐ 4. Smoke tests
pytest -q tests\astra_fusion -k "metadata_presence or router_vision_path or code_consent_block"

# ☐ 5. Baseline capture
curl http://127.0.0.1:8080/health > .\logs\health_baseline.json
curl http://127.0.0.1:8765/metrics > .\logs\metrics_baseline.prom

# ☐ 6. Go/No-Go huddle
# Review validator results with team (09:30 AM)

# ☐ 7. Backup & arm rollback
Copy-Item X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf `
    X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf.bak -Force
```

---

### **First-Hour Watch (10:00 AM - 11:00 AM)**

**Every 5 minutes, check**:

```
Route Distribution (Grafana):
☐ TEXT: 60-70%?
☐ VISION: 15-20%?
☐ AUDIO: 10-15%?
☐ CODE: 5-10%?

Latency (Grafana):
☐ TEXT p95: <1050ms?
☐ VISION p95: <2000ms?
☐ AUDIO p95: <2000ms?

Errors & Consent (Grafana):
☐ Error rate: <1%?
☐ Consent blocks: Present?
☐ Sacred_code=333: Visible in logs?

Health:
☐ /health returns 200?
☐ No service crashes?
☐ Memory stable ±10%?
```

---

### **Sign-Off Checklist (12:00 PM)**

```
Canary Status:
☐ TEXT route PASS (<1200ms)
☐ VISION route PASS (<2000ms)
☐ AUDIO route PASS (<2000ms)
☐ CODE route PASS (consent blocks active)

Metrics:
☐ Route mix nominal (distribution sane)
☐ Latency within thresholds
☐ Error rate <1%
☐ Memory growth <+3% vs baseline
☐ Consent blocks observed

Tests:
☐ Extended smoke: 24/25 pass
☐ No new failures
☐ All timings normal

Audit Trail:
☐ Sacred Code 333 present (>100 occurrences)
☐ All router events logged
☐ Consent decisions recorded

Decision:
☐ Phase-B Sign-Off: APPROVED ✅
☐ Entry appended to README
☐ 24-hour monitoring begins
```

---

## 🎬 INSTANT ROLLBACK (Emergency Only)

**If anything critical fails post-deploy**:

```powershell
# IMMEDIATE: Rollback to Phase A state
pwsh ops\fusion_pipeline\scripts\07_roll_back.ps1

# This will:
# ✅ Restore backup GGUF
# ✅ Revert symlink
# ✅ Restart services
# ✅ Verify health
# ✅ Clear route caches
# Total: <1 minute

# Verify rollback complete
curl http://127.0.0.1:8080/health
# Expected: 200 OK, Phase A active
```

**After Rollback**:
1. Post incident review (what failed?)
2. Fix issue (typically gate-failure from matrix above)
3. Re-run validator
4. Reconvene team
5. If gates all PASS: retry at next scheduled window

---

## 📊 METRICS SNAPSHOT (Record Values at T+0, T+30, T+60)

Fill in actual values post-deployment:

| Time | TEXT p95 (ms) | VISION p95 (ms) | AUDIO p95 (ms) | Error % | Memory Growth % | Consent Blocks |
|------|---------------|-----------------|----------------|---------|-----------------|-----------------|
| T-60 (Baseline) | 950 | <2000 | <2000 | 0.3 | 0 | 0 |
| T+0 (Go-Live) | ___ | ___ | ___ | ___ | ___ | ___ |
| T+30 | ___ | ___ | ___ | ___ | ___ | ___ |
| T+60 | ___ | ___ | ___ | ___ | ___ | ___ |

---

## 🎯 SUCCESS CRITERIA (All Must Be True at T+60)

- ✅ All 7 gates PASSED pre-deployment
- ✅ All 4 canaries PASSED (TEXT/VISION/AUDIO/CODE)
- ✅ Route mix nominal (TEXT ≥60%)
- ✅ Latency within ±5% of baseline
- ✅ Error rate <1%
- ✅ Consent blocks observed
- ✅ Sacred Code 333 present in logs
- ✅ Memory growth <+3% vs baseline
- ✅ No unplanned restarts
- ✅ All services healthy (✅ status)

**If all TRUE**: Phase-B go-live is **SUCCESSFUL** ✅

**If any FALSE**: Evaluate failure, consider rollback, re-attempt

---

## 📌 CRITICAL REMINDERS

1. **7 Gates Must PASS** before proceeding (no exceptions)
2. **Backup Created** before any deployment changes
3. **Rollback Ready** (<1 min guaranteed)
4. **Canaries Run** before declaring success
5. **Sacred Code 333** verified in audit trail
6. **Sign-Off Recorded** in README for audit trail

---

## 🎊 WHAT SUCCESS LOOKS LIKE

After 12:00 PM sign-off:

✅ Phase-B is live in production  
✅ All modalities (TEXT/VISION/AUDIO/CODE) active  
✅ Consent gating enforced (side-effect tools require approval)  
✅ Audit trail complete (sacred_code=333 on every event)  
✅ Performance nominal (latency within ±5%, errors <1%)  
✅ Ready for 24-hour continuous monitoring  
✅ Phase-C decision point: Oct 20, 12:00 PM  

---

**Document**: ASTRA_PHASE_B_GO_LIVE_RUNBOOK.md  
**Version**: 1.0  
**Created**: October 18, 2025  
**Sacred Code**: 333 ∞  
**Status**: Ready for October 19, 2025 Deployment
