# 🔒 ASTRA Week-1 Hardening Runbook

**Objective**: Secure ASTRA before deployment  
**Duration**: 2-3 hours  
**Prerequisites**: Python 3.11+, Git, PowerShell

---

## 📋 Preparation (5 minutes)

```powershell
# Navigate to project root
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

# Create feature branch
git checkout -b chore/hardening-week1

# Verify all patch files created
ls security\models_registry.yaml
ls security\verify_models.py
ls core\memory_signing.py
ls tools\backup\backup_runner.py
ls tools\backup\restore_runner.py
ls tools\security\run_scans.ps1
ls tests\week1\test_minimum_security.py
```

**✅ Success Criteria**: All files exist

---

## 🔐 Step 1: Model Checksums (30 minutes)

Lock down models to prevent supply chain attacks.

```powershell
# Initial run (will populate checksums)
python security/verify_models.py --write

# Verification run (should print status: OK)
python security/verify_models.py
```

**Expected output**:
```json
{
  "verify_models": {
    "status": "OK",
    "verified": 2
  }
}
```

**✅ Success Criteria**: Status = OK, no checksum mismatches

---

## 🔑 Step 2: Memory Signing Key (5 minutes)

Generate HMAC signing key for memory integrity.

```powershell
# Generate key (save to your encrypted secrets)
$key = (New-Guid).Guid
Write-Host "Generated key: $key"

# Set for current session (add to your .env or encrypted secrets)
$env:ASTRA_MEMORY_SIGNING_KEY = $key

# Verify key is set
if ($env:ASTRA_MEMORY_SIGNING_KEY) {
    Write-Host "✓ Memory signing key configured"
} else {
    Write-Host "❌ Key not set - memory signing will fail"
}
```

**⚠️ IMPORTANT**: Add `ASTRA_MEMORY_SIGNING_KEY` to your encrypted secrets flow. Do NOT commit plaintext.

**✅ Success Criteria**: Key generated and set

---

## 💾 Step 3: Backup Validation (30 minutes)

Test backup/restore pipeline.

```powershell
# Dry run (preview)
python tools/backup/backup_runner.py --dry-run

# Create first backup
python tools/backup/backup_runner.py

# Verify backup created
ls data\backups\astra_backup_*.zip

# Dry run restore (preview)
python tools/backup/restore_runner.py --source latest --dry-run

# Test restore to temp location (optional, destructive)
# python tools/backup/restore_runner.py --source latest
```

**Expected output**:
```json
{
  "backup": {
    "created": true,
    "path": "data/backups/astra_backup_20251101T120000Z.zip",
    "size_mb": 45.23,
    "retained": 1
  }
}
```

**✅ Success Criteria**: Backup created, restore dry-run succeeds

---

## 🛡️ Step 4: Security Scans (45 minutes)

Scan dependencies and code for vulnerabilities.

```powershell
# Run all scans (pip-audit, bandit, safety)
powershell -ExecutionPolicy Bypass -File tools\security\run_scans.ps1

# Review reports
cat audit\pip_audit.log
code audit\bandit_report.json    # Open in VS Code
code audit\safety_report.json
```

**Expected**: Some warnings acceptable, but ZERO critical/high severity unfixed issues.

**✅ Success Criteria**: 
- Scans complete
- Critical vulnerabilities addressed or documented
- Reports saved in `audit/`

---

## 📦 Step 5: Simplification - Archive K8s (15 minutes)

Remove Kubernetes complexity (Week-2 Day-1 prep).

```powershell
# Create archive directory
mkdir archive\k8s_for_scale -Force

# Move K8s manifests (if k8s/ exists)
if (Test-Path k8s) {
    Move-Item k8s\* archive\k8s_for_scale\ -Force
    Write-Host "✓ Kubernetes manifests archived"
} else {
    Write-Host "⚠️ No k8s/ directory found"
}
```

**✅ Success Criteria**: K8s manifests moved to archive, docker-compose remains

---

## ✅ Step 6: Validation Tests (15 minutes)

Run Week-1 acceptance tests.

```powershell
# Run Week-1 security tests
pytest tests/week1/test_minimum_security.py -v

# Run full test suite (if time permits)
pytest -q
```

**Expected output**:
```
tests/week1/test_minimum_security.py::test_models_registry_exists PASSED
tests/week1/test_minimum_security.py::test_verify_models_script_runs PASSED
tests/week1/test_minimum_security.py::test_backups_folder PASSED
tests/week1/test_minimum_security.py::test_backup_runner_exists PASSED
tests/week1/test_minimum_security.py::test_astra_yaml_loads PASSED
tests/week1/test_minimum_security.py::test_memory_signing_importable PASSED
tests/week1/test_minimum_security.py::test_security_scan_script_exists PASSED
tests/week1/test_minimum_security.py::test_docker_compose_exists PASSED

8 passed in 2.5s
```

**✅ Success Criteria**: All tests pass

---

## 📝 Step 7: Commit & Document (10 minutes)

```powershell
# Stage all new files
git add security tools docker-compose-simplified.yml tests data/backups/.gitkeep core/memory_signing.py

# Commit with descriptive message
git commit -m "chore(security): Week-1 hardening patch set

- Add model checksum verification (supply chain security)
- Implement memory signing with HMAC-SHA256 (integrity protection)
- Create backup/restore runners (data resilience)
- Add security scan automation (pip-audit, bandit, safety)
- Archive K8s manifests (simplification)
- Add Week-1 acceptance tests

Closes: Week-1 Hardening
See: audit/🎯_AUDIT_COMPLETE.md Strategic Analysis Update"

# Push to remote
git push -u origin chore/hardening-week1
```

**✅ Success Criteria**: Branch pushed, commit message clear

---

## 🎯 Week-1 Completion Checklist

- [ ] Model checksums: `security/verify_models.py` passes
- [ ] Memory signing key: `ASTRA_MEMORY_SIGNING_KEY` set
- [ ] Backups: First backup created, restore dry-run passes
- [ ] Security scans: Reports generated, critical issues addressed
- [ ] K8s archived: `archive/k8s_for_scale/` exists
- [ ] Tests: `pytest tests/week1/` passes
- [ ] Committed: Branch pushed to remote

---

## 📊 What This Unlocks

✅ **Supply-chain safety**: Models verified before boot  
✅ **Integrity by design**: Memories HMAC-signed, tampering detectable  
✅ **Data resilience**: Backups exist, restore validated  
✅ **Baseline hygiene**: Vulnerability reports generated  
✅ **Simplification runway**: K8s archived, Compose path ready  

---

## 🚀 Next Steps (Week 2 Preview)

1. **BGE-M3 Embeddings**: Re-embed 21K docs (+15-20% precision)
2. **Provenance**: Add "According to [doc X]..." to RAG answers
3. **Single Config**: Consolidate to `astra.yaml`
4. **One Deployment Guide**: Replace 15+ guides with ONE

---

## 🆘 Troubleshooting

### Model verification fails
```powershell
# Add your actual model paths to security/models_registry.yaml
# Then re-run: python security/verify_models.py --write
```

### Memory signing import fails
```powershell
# Ensure core/ is in PYTHONPATH or run from project root
$env:PYTHONPATH = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
```

### Security scans timeout
```powershell
# Run individually with longer timeout
pip-audit --fix --timeout 300
bandit -r src -f json -o audit/bandit_report.json
safety check --full-report --json > audit/safety_report.json
```

### Tests fail
```powershell
# Check which test failed
pytest tests/week1/test_minimum_security.py -v --tb=short

# Fix path issues by running from project root
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
```

---

**Total Time**: ~2-3 hours  
**Completion**: Week-1 Hardening ✓  
**Next**: Week-2 Intelligence Upgrade (BGE-M3 + Provenance)
