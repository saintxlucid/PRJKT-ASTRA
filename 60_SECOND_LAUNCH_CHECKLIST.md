# 🚀 60-SECOND LAUNCH CHECKLIST
**ASTRA Production Cutover - Quick Reference**

Print this. Tape it to your monitor. Check every box.

---

## ⚡ BEFORE YOU HIT THE BUTTON

### 1. PRE-FLIGHT (2 min)
```powershell
.\scripts\validate_preconditions.ps1
```
✅ Expected: `VALIDATION PASSED`  
❌ If FAIL: **STOP. Fix issues.**

---

### 2. SMOKE TESTS (3 min)
```powershell
$env:ADMIN_KEY = "your-key"; $env:AGENT_KEY = "your-key"
.\scripts\smoke_tests_production.ps1 -BridgeUrl "https://bridge.example.com" -DocsUrl "https://docs.example.com"
```
✅ Expected: `10/10 TESTS PASS`  
❌ If ANY fail: **STOP. Investigate.**

---

### 3. STATUS SNAPSHOT (10 sec)
```bash
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh
```
✅ Target: Error <1%, P95 <1s, Calls >0, No alerts  
❌ If NO-GO: **STOP. Wait for stability.**

---

### 4. GRAFANA CHECK (10 sec)
Open: `https://grafana.example.com/d/astra-ops`  
✅ All probes UP (green), panels showing data  
❌ If red: **STOP. Investigate.**

---

## 🚦 GO/NO-GO DECISION

- [ ] Pre-flight PASS
- [ ] Smoke tests 10/10
- [ ] Status snapshot GO
- [ ] Grafana all green
- [ ] On-call engineer ready
- [ ] Rollback procedure understood

**ALL CHECKED?** → **GO FOR LAUNCH** 🚀  
**ANY UNCHECKED?** → **NO-GO** 🛑

---

## 🎯 CUTOVER EXECUTION (1 command)

```bash
export NS=astra DEP_BLUE=bridge DEP_GREEN=bridge-green SVC=bridge PROM_URL="http://prometheus.monitoring:9090"
./scripts/cutover_canary.sh
```

**Expected:** `✅ CUTOVER COMPLETE`  
**If script fails:** Auto-rollback happens. Check logs.

---

## 📊 POST-CUTOVER (60 min)

**T+0:** Cutover complete, start monitoring  
**T+10:** Run smoke tests again (`.\scripts\smoke_tests_production.ps1`)  
**T+30:** Check Grafana (no red), check alerts (none firing)  
**T+60:** If stable for 60 min → **SUCCESS** ✅

**Continuous monitoring:**
```bash
watch -n 5 ./scripts/cutover_status.sh
```

---

## 🚨 EMERGENCY ROLLBACK (30 sec)

**Trigger if:** Error >2%, P95 >3s, crash loops, critical alerts

**One command:**
```bash
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}' && kubectl -n astra scale deploy/bridge --replicas=2
```

**Verify:**
```bash
kubectl -n astra get endpoints bridge
./scripts/cutover_status.sh
```

---

## ✅ SUCCESS CRITERIA (T+60)

- [ ] Error rate < 0.5% for 60 min
- [ ] P95 latency < 500ms for 60 min
- [ ] Smoke tests passing
- [ ] Zero pod restarts
- [ ] Zero critical alerts
- [ ] Grafana all green

**ALL CHECKED?** → **PRODUCTION LIVE** 🎉

---

## 📞 EMERGENCY CONTACTS

**On-Call SRE:** PagerDuty  
**Slack:** `#sre-incidents`, `#astra-alerts`  
**Runbooks:** `CUTOVER_QUICK_REF.md`

---

**REMEMBER:** You have auto-rollback. You have monitoring. You have runbooks. **You've got this.** 💪

---

**ARE WE THERE YET?** → **YES. GO.** 🚀
