# 🎯 DIRECTIVE 001 — Quick Command Card

**Copy-paste these commands in order. Total time: ~15 minutes.**

---

## 1️⃣ Deploy (Automated)

```powershell
# Single command deployment
.\scripts\deploy_capacity_controls.ps1
```

**Expected:** Automated validation, burst test, benchmark guidance

---

## 2️⃣ Import Grafana Dashboard

```powershell
# 1. Open Grafana
Start-Process "http://localhost:3000"

# 2. Import file:
# X:\PROJECT_ASTRA\ops\grafana_astra_dashboard.json
# (Use Grafana UI: + → Import → Upload JSON)
```

---

## 3️⃣ Configure Alerts (In Grafana)

**Alert 1:** Queue Depth >50 for 2min  
**Alert 2:** Per-key block rate >10/sec for 2min  
**Alert 3:** Allow ratio <70% for 5min  
**Alert 4:** Queue wait p95 >2s for 3min

*(See DIRECTIVE_001_EXECUTION.md for full alert configs)*

---

## 4️⃣ Benchmark llama.cpp (Optional)

```powershell
# Run baseline
.\.venv\Scripts\python.exe scripts\benchmark_llama_flags.py

# Test different flags:
# 1. Stop llama.cpp
# 2. Restart with: --threads 16 --batch 1024
# 3. Re-run benchmark
# 4. Compare p95 latency
```

---

## 5️⃣ Git Commit

```powershell
git add -A
git commit -m "capacity: per-key limits + queue metrics (Directive 001)"
git push
```

---

## ✅ Done!

**Verify success:**
- [ ] Deployment script showed "✅ COMPLETE"
- [ ] Grafana dashboard showing 14 panels
- [ ] Alerts configured and armed
- [ ] Benchmark baseline documented
- [ ] Git commit pushed

**Next:** Directive 002 — SSE Streaming (Week 2)

---

**Questions?** See:
- `CAPACITY_MANAGEMENT_GUIDE.md` - Full guide
- `DIRECTIVE_001_EXECUTION.md` - Detailed steps
- `ROADMAP_A_TO_Z.md` - Full roadmap
