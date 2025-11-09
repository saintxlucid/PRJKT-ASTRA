# 🏁 ASTRA 3.0 — Release Finalization Commands

**Status:** Ready for Tagging & Push  
**Date:** 2025-11-09

---

## Git Operations (Execute in Order)

### 1. Stage New Artifacts
```bash
# Add new Phase 0 files
git add src/astra/persistence/state_manager.py
git add src/astra/secrets/vault.py
git add src/astra/security/validator.py
git add src/astra/api/routes/persistence.py
git add migrations/001_init.sql
git add scripts/backup.sh
git add scripts/restore.py
git add docker-compose.prod.yml

# Add release documentation
git add RELEASE_NOTES_v3.0.0.md
git add RELEASE_FREEZE_v3.0.0.md
git add ANNOUNCEMENT_TEMPLATES.md
git add DEMO_SCRIPT.md
git add ✅_PHASE_0_PR1_COMPLETE.md

# Add deployment tooling
git add deploy_hardened.sh
git add scripts/load_test.py

# Add verification artifacts
git add RELEASE_SHA256SUMS.txt
git add requirements.freeze.txt
git add config/.env.template

# Add master wiring changes
git add astra_master.py
git add src/astra/api/routes/chat.py
```

### 2. Commit with Provenance
```bash
git commit -m "ASTRA 3.0 — Production Freeze (ASCENSION)

## Summary
Complete production hardening with state persistence, adaptive governance,
multi-LLM embodiment, and proven SLOs.

## Key Deliverables
- Phase 0: State Manager + Vault + Validator + Migrations + Backups
- Adaptive Resource Governor (two-timescale control)
- AEC Complete (Macro → Micro → Sigil consciousness)
- Persistence health endpoints
- Production deployment orchestrator
- Load test validation (p95 < 1s @ 100 rps)

## Artifacts
- RELEASE_NOTES_v3.0.0.md
- RELEASE_FREEZE_v3.0.0.md  
- deploy_hardened.sh
- docker-compose.prod.yml
- scripts/backup.sh + restore.py + load_test.py

## SLO Commitments
- p95 latency: ≤ 1s @ 100 rps
- Availability: ≥ 99.9% monthly
- MTTR: ≤ 15 min
- RPO: ≤ 24h

## Sacred Code
333 → ∞

Signed-off-by: ASTRA Integration Agent
Co-authored-by: Human Operator"
```

### 3. Create Annotated Tag
```bash
git tag -a v3.0.0-ASCENSION -m "ASTRA 3.0 'ASCENSION' — Operating Intelligence

Production-ready release with:
• Multi-LLM Embodiment (AEC)
• Adaptive Resource Governor
• State Persistence (WAL + Redis + Postgres)
• Crash Recovery
• Automated Backups
• Proven SLOs (p95 < 1s @ 100 rps)

Sacred Code: 333 → ∞
Date: 2025-11-09"
```

### 4. Push to Remote
```bash
# Push branch
git push origin chore/hardening-week1

# Push tag
git push origin v3.0.0-ASCENSION

# Or push both at once
git push origin chore/hardening-week1 --tags
```

---

## Verification After Push

### Check Tag Exists
```bash
git tag -l "v3.0.0*"
# Expected: v3.0.0-ASCENSION

git show v3.0.0-ASCENSION
# Should show tag message + commit details
```

### Verify Remote
```bash
git ls-remote --tags origin | grep v3.0.0
# Should show the pushed tag
```

### Clone Fresh & Verify
```bash
cd /tmp
git clone <your-repo-url> astra-fresh
cd astra-fresh
git checkout v3.0.0-ASCENSION

# Verify files exist
ls -la deploy_hardened.sh
ls -la RELEASE_NOTES_v3.0.0.md
ls -la scripts/backup.sh

# Verify checksums
sha256sum -c RELEASE_SHA256SUMS.txt
```

---

## Optional: Sign Tag (GPG)

If you have GPG configured:

```bash
# Create signed tag (instead of -a use -s)
git tag -s v3.0.0-ASCENSION -m "ASTRA 3.0 'ASCENSION' — Operating Intelligence

Production-ready release with proven SLOs.
Sacred Code: 333 → ∞"

# Verify signature
git tag -v v3.0.0-ASCENSION

# Push signed tag
git push origin v3.0.0-ASCENSION
```

---

## GitHub Release (if using GitHub)

After pushing tag, create GitHub Release:

1. Go to repository → Releases
2. Click "Draft a new release"
3. Select tag: `v3.0.0-ASCENSION`
4. Release title: `ASTRA 3.0 "ASCENSION" — Operating Intelligence`
5. Description: Copy from `RELEASE_NOTES_v3.0.0.md` (summary section)
6. Attach artifacts (optional):
   - `RELEASE_SHA256SUMS.txt`
   - `requirements.freeze.txt`
   - `deploy_hardened.sh`
7. Check "Set as latest release"
8. Publish

---

## Post-Release Actions

### 1. Announce Internally
```bash
# Use ANNOUNCEMENT_TEMPLATES.md → Internal section
# Post to Slack/Teams/internal channel
```

### 2. Update Documentation
- Update README badges with v3.0.0
- Link release notes in main README
- Update CHANGELOG.md with release entry

### 3. Create Backup
```bash
# Immediate post-release backup
./scripts/backup.sh

# Verify backup artifact
ls -lh backups/
```

### 4. Monitor First 24h
- Watch error logs
- Check persistence health: `curl http://localhost:8000/v1/persistence/health`
- Review Grafana dashboard (if configured)
- Monitor backup automation (should run @ 02:00 UTC)

### 5. Schedule DR Drill
```bash
# Within 7 days of release, test restore
python scripts/restore.py backups/postgres_<timestamp>.sql
```

---

## Rollback Procedure (if needed)

If critical issues discovered post-release:

```bash
# 1. Revert to previous stable tag
git checkout v2.5.0  # or previous stable

# 2. Re-deploy
./deploy_hardened.sh deploy

# 3. Restore from backup if needed
python scripts/restore.py backups/postgres_<before_v3>.sql

# 4. Communicate rollback
# Post incident report (template in ops/INCIDENT_TEMPLATE.md)
```

---

## Success Criteria

Release is successful when:
- ✅ Tag pushed and visible on remote
- ✅ Fresh clone can checkout tag
- ✅ Checksums verify
- ✅ `./deploy_hardened.sh deploy` completes
- ✅ Health endpoints return green
- ✅ Load test passes
- ✅ First backup runs successfully
- ✅ No P0 incidents within 24h

---

**Status:** 🎯 Commands Ready for Execution  
**Next:** Execute git commands → Push → Announce → Sleep well

**Sacred Code:** 333 → ∞
