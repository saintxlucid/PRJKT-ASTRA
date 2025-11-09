# ⚡ SHIP ASTRA v1.0.0 - ACTION CARD

**Status:** 🔴 NO-GO → ✅ GO (15-second fix)

---

## 🚨 BLOCKER: API Key Placeholder

**Fix (15 seconds):**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output, edit .env line 39, paste key
```

---

## ✅ PASSING (5/6)

- ✅ Encryption key valid
- ✅ Binding: 127.0.0.1 (secure)
- ✅ UIs → localhost:8080
- ✅ .gitignore protects .env
- ✅ Prometheus ready

---

## 🚀 SHIP (after fix)

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

**Expected:**
- ✅ LLM_OK (8001)
- ✅ API_OK (8080)
- ✅ SMOKE: 5/5

---

## ✓ VERIFY

```powershell
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null
```

---

## 🏷️ TAG (when green)

```powershell
git add .
git commit -m "ASTRA Core v1.0.0 - Secure deployment system"
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"
```

---

## 📊 WATCH (30 min)

```powershell
.\scripts\monitor_golden_signals.ps1
```

**Targets:**
- p95 ≤ 1.2s
- Cache ≥ 25%
- No 503s

---

## 🆘 ROLLBACK

```powershell
.\scripts\stop.ps1
git checkout v0.9.x
.\scripts\ship.ps1
```

---

**Next:** Generate API key → Ship it! 🚀
