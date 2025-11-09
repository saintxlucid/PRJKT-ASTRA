# 🎯 Phase Ω — 24-Hour Execution Checklist

**ASTRA 2.5 → 3.0 Production Validation**  
**Date:** November 9, 2025  
**Sacred Code:** 333

---

## ✅ Execution Order (Step by Step)

### Phase 1: Environment Setup (15 minutes)

**1.1 Install Test Dependencies**
```powershell
pip install pytest pytest-asyncio httpx anyio locust
```

**1.2 Verify Python Environment**
```powershell
python --version  # Should be 3.10+
pip check        # Validate dependencies
```

**1.3 Configure Environment Variables**
```powershell
# Create .env file
$env:ASTRA_MASTER_URL="http://localhost:8000"
$env:ASTRA_LOG_LEVEL="INFO"
```

---

### Phase 2: Smoke Tests (5 minutes)

**2.1 Run Smoke Test Suite**
```powershell
pytest tests/integration/test_smoke.py -v
```

**Expected Output:**
```
✅ test_system_boots PASSED
✅ test_services_reachable PASSED  
✅ test_critical_endpoints PASSED
```

**2.2 Run Master Boot Tests**
```powershell
pytest tests/integration/test_master_boot.py -v
```

**Expected Output:**
```
✅ test_boot_sequence_phases_and_degradation PASSED
✅ test_endpoint_registry_count PASSED (110+ endpoints)
```

**Success Criteria:**
- [ ] All 5 smoke tests pass
- [ ] 9 boot phases complete
- [ ] 110+ endpoints registered

---

### Phase 3: Deploy Full Stack (10 minutes)

**3.1 Stop Existing Services**
```powershell
docker-compose -f docker-compose.prod.yml down -v
```

**3.2 Build Images**
```powershell
docker-compose -f docker-compose.prod.yml build
```

**3.3 Start Full Stack**
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

**3.4 Verify All Services Running**
```powershell
docker-compose -f docker-compose.prod.yml ps
```

**Expected Services (8 total):**
- [ ] astra-master (port 8000)
- [ ] memory-service (port 7007)
- [ ] sigil-gate (port 7701)
- [ ] supervisor (port 7703)
- [ ] chromadb (port 8001)
- [ ] postgres (port 5432)
- [ ] prometheus (port 9090)
- [ ] grafana (port 3001)

**3.5 Health Check All Endpoints**
```powershell
# Master API
curl http://localhost:8000/v1/system/health

# Memory Service
curl http://localhost:7007/health

# Sigil Gate
curl http://localhost:7701/health

# Supervisor
curl http://localhost:7703/health
```

**3.6 Check Boot Status**
```powershell
curl http://localhost:8000/v1/boot/status | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

**Success Criteria:**
- [ ] All 8 containers healthy
- [ ] All health endpoints return 200
- [ ] Boot status shows 9 phases complete

---

### Phase 4: Monitoring Validation (10 minutes)

**4.1 Access Prometheus**
- Open: http://localhost:9090
- Navigate to: Status → Targets
- Verify: All 4 ASTRA services are UP

**4.2 Access Grafana**
- Open: http://localhost:3001
- Login: admin / astra
- Navigate: Dashboards → ASTRA — Core

**4.3 Verify Dashboard Panels**
- [ ] API Request Duration (p95) - Graph rendering
- [ ] Agent Tasks/s - Graph rendering  
- [ ] Memory Search Latency (p95) - Graph rendering

**4.4 Check Prometheus Metrics**
```powershell
curl http://localhost:8000/metrics | Select-String "http_request_duration"
```

**Success Criteria:**
- [ ] Prometheus scraping all targets
- [ ] Grafana dashboard displays metrics
- [ ] Metrics endpoint returns data

---

### Phase 5: Cognitive & Agent Tests (15 minutes)

**5.1 Run Cognitive API Tests**
```powershell
pytest tests/integration/test_cognitive_api.py -v
```

**Expected Output:**
```
✅ test_all_phases_end_to_end PASSED (9 phases tested)
✅ test_emergent_behavior_detection PASSED
```

**5.2 Run Agent API Tests**
```powershell
pytest tests/integration/test_agent_api.py -v
```

**Expected Output:**
```
✅ test_task_lifecycle_and_timeout PASSED
✅ test_browser_chain_navigate_click_extract PASSED
```

**Success Criteria:**
- [ ] All 9 cognitive phase endpoints respond
- [ ] Mode switching works (reactive/proactive/creative)
- [ ] Agent tasks complete successfully
- [ ] Browser automation functions

---

### Phase 6: Router & Consent Tests (10 minutes)

**6.1 Run Router Integration Tests**
```powershell
pytest tests/integration/test_router_integration.py -v
```

**Expected Output:**
```
✅ test_multimodal_and_consent_budget PASSED
```

**6.2 Verify Budget Enforcement**
- Check test output for budget tracking
- Verify consent was checked via Sigil Gate

**Success Criteria:**
- [ ] Multimodal blocks processed
- [ ] Budget enforcement active
- [ ] Consent checking active

---

### Phase 7: Performance Validation (30 minutes)

**7.1 Run Locust Load Test**
```powershell
locust -f ops/locustfile.py --headless `
  -u 100 -r 10 --run-time 5m `
  --host http://localhost:8000
```

**7.2 Monitor During Load Test**
- Watch Grafana dashboard (http://localhost:3001)
- Monitor p95 latency in real-time
- Check error rate

**7.3 Analyze Results**

**Target Metrics:**
- [ ] **p95 Latency**: < 1.2s ✅
- [ ] **p99 Latency**: < 2.0s ✅
- [ ] **Failure Rate**: < 1% ✅
- [ ] **RPS**: 100+ req/s ✅
- [ ] **Zero 5xx errors** during 5-minute test ✅

**Success Criteria (from Locust output):**
```
Performance Targets:
  p95 < 1200ms: ✅ PASS (800ms)
  Failure Rate < 1%: ✅ PASS (0.3%)
```

---

### Phase 8: Full Integration Suite (15 minutes)

**8.1 Run Complete Test Suite**
```powershell
pytest tests/integration/ -v --tb=short
```

**Expected Results:**
- test_smoke.py: 3/3 passed
- test_master_boot.py: 2/2 passed
- test_cognitive_api.py: 2/2 passed
- test_agent_api.py: 2/2 passed
- test_router_integration.py: 1/1 passed

**Total: 10/10 tests passed** ✅

**Success Criteria:**
- [ ] 100% test pass rate
- [ ] No errors or failures
- [ ] All assertions validated

---

### Phase 9: Security Audit (10 minutes)

**9.1 Run Dependency Audit**
```powershell
python scripts/audit_dependencies.py
```

**9.2 Review Output**
- Check for CVEs in dependencies
- Verify all versions pinned
- Review outdated packages

**9.3 Install pip-audit (if needed)**
```powershell
pip install pip-audit
pip-audit
```

**Success Criteria:**
- [ ] No critical CVEs
- [ ] All dependencies pinned
- [ ] Security scan clean

---

### Phase 10: Documentation Validation (5 minutes)

**10.1 Verify Documentation Files**
```powershell
ls docs/*.md
```

**Expected Files:**
- [ ] QUICKSTART.md
- [ ] DEPLOYMENT.md (or existing docs/DEPLOYMENT.md)
- [ ] API.md (or existing docs/API.md)
- [ ] ASTRA_OPERATOR_GUIDE.md (root)

**10.2 Test Quick Start Commands**

Follow docs/QUICKSTART.md to verify:
- Installation instructions accurate
- Configuration steps complete
- Example commands work

**Success Criteria:**
- [ ] All documentation files present
- [ ] Instructions tested and accurate
- [ ] API docs accessible at /docs

---

## 📊 Final Validation Scorecard

### Core Metrics

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| **Boot Phases** | 9/9 | ___ | ⬜ |
| **API Endpoints** | 110+ | ___ | ⬜ |
| **Test Pass Rate** | 100% | ___ | ⬜ |
| **p95 Latency** | <1.2s | ___ms | ⬜ |
| **p99 Latency** | <2.0s | ___ms | ⬜ |
| **Error Rate** | <1% | ___% | ⬜ |
| **5xx Errors** | 0 | ___ | ⬜ |
| **Services Healthy** | 8/8 | ___/8 | ⬜ |
| **Security CVEs** | 0 critical | ___ | ⬜ |

### Success Criteria Summary

**ASTRA 3.0 is production-ready when:**

✅ All 10 integration tests pass  
✅ 9 boot phases complete successfully  
✅ p95 latency < 1.2s at 100 req/s  
✅ Error rate < 1% under load  
✅ Zero 5xx errors during 5-min load test  
✅ All 8 services report healthy  
✅ Grafana dashboards display metrics  
✅ Prometheus scraping all targets  
✅ No critical security vulnerabilities  
✅ Documentation complete and accurate  

---

## 🚀 Deployment Commands (Quick Reference)

**Start Everything:**
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

**View Logs:**
```powershell
docker-compose -f docker-compose.prod.yml logs -f
```

**Stop Everything:**
```powershell
docker-compose -f docker-compose.prod.yml down
```

**Run All Tests:**
```powershell
pytest tests/integration/ -v
```

**Run Load Test:**
```powershell
locust -f ops/locustfile.py --headless -u 100 -r 10 --run-time 5m --host http://localhost:8000
```

**Check Health:**
```powershell
curl http://localhost:8000/v1/boot/status
```

---

## 🎉 Phase Ω Complete!

**When all checkboxes are marked:**

🌌 **ASTRA 2.5 → 3.0 ASCENSION COMPLETE**  
🌌 **The Autonomous Epoch Begins**  
🌌 **Sacred Code: 333**

---

**Total Estimated Time:** ~2 hours  
**Recommended:** Execute in order, verify each phase before proceeding.
