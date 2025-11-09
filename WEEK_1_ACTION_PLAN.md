# 🚀 ASTRA PHASE C - IMMEDIATE ACTIONS (Week 1)
**Target**: Ship Week 1 Security + Simplification Foundation
**Deadline**: 7 days from handoff
**GO/NO-GO Gate**: All 8 acceptance criteria must pass

---

## 🔐 SECURITY HARDENING (Priority 1)

### Action 1.1: Encrypt Secrets
**Owner**: Operator  
**Effort**: 30 min  
**RICE Score**: 25/10 (Critical)

```powershell
# Step 1: Generate .env template
python scripts\encrypt_secrets.py --generate

# Step 2: Fill in values (especially MEMORY_SIGNING_KEY)
notepad config\.env

# Step 3: Encrypt
python scripts\encrypt_secrets.py

# Step 4: Verify
python scripts\encrypt_secrets.py --verify

# Step 5: Delete plaintext
del config\.env
```

**Acceptance Criteria**:
- ✅ `config/.env.gpg` exists and decrypts successfully
- ✅ `config/.env` deleted (no plaintext secrets)
- ✅ `MEMORY_SIGNING_KEY` populated (32-byte hex)

---

### Action 1.2: Implement Memory Signing
**Owner**: Developer  
**Effort**: 4 hours  
**RICE Score**: 20/4

**Files to Edit**:
1. `src/astra/memory/memory_service.py` - Add signature on write
2. `src/astra/memory/memory_engine.py` - Verify signature on read
3. `tests/constitution/test_memory_signing.py` - 100% pass rate

**Implementation**:
```python
# src/astra/memory/memory_service.py
import hashlib
import os
from datetime import datetime

def sign_memory(content: str, timestamp: datetime) -> str:
    """Sign memory with SHA256(content + timestamp + secret_key)"""
    secret = os.getenv("MEMORY_SIGNING_KEY")
    if not secret:
        raise ValueError("MEMORY_SIGNING_KEY not set")
    
    payload = f"{content}{timestamp.isoformat()}{secret}"
    return hashlib.sha256(payload.encode()).hexdigest()

def verify_signature(content: str, timestamp: datetime, signature: str) -> bool:
    """Verify memory signature"""
    expected = sign_memory(content, timestamp)
    return expected == signature
```

**Acceptance Criteria**:
- ✅ All new memories auto-signed on creation
- ✅ Unsigned memories flagged with warning
- ✅ Forged signatures → quarantine memory
- ✅ `test_memory_signing.py` passes 100%

---

### Action 1.3: Add Model Checksums
**Owner**: Operator  
**Effort**: 1 hour  
**RICE Score**: 18/1

```bash
# Generate checksums for all models
cd models/
sha256sum llama-2-7b-chat.Q4_K_M.gguf > checksums.txt
sha256sum mistral-7b-instruct-v0.2.Q5_K_M.gguf >> checksums.txt
sha256sum codellama-13b.Q4_K_M.gguf >> checksums.txt
```

**Update `config/models_registry.yaml`**:
```yaml
models:
  - name: "llama-2-7b"
    path: "models/llama-2-7b-chat.Q4_K_M.gguf"
    sha256: "<paste checksum here>"
    
  - name: "mistral-7b"
    path: "models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
    sha256: "<paste checksum here>"
    
  - name: "codellama-13b"
    path: "models/codellama-13b.Q4_K_M.gguf"
    sha256: "<paste checksum here>"
```

**Acceptance Criteria**:
- ✅ All 3 models have SHA256 checksums
- ✅ Boot-time verification passes
- ✅ Tampered model → ASTRA refuses to start

---

### Action 1.4: Automate Backups
**Owner**: Developer  
**Effort**: 3 hours  
**RICE Score**: 16/3

**Files to Create**:
1. `scripts/backup.py` - Backup script (ZIP memory + config + identity)
2. `.github/workflows/backup.yml` - Schedule backups every 4 hours
3. `tests/test_backup.py` - Verify backup integrity

**Backup Script**:
```python
# scripts/backup.py
import zipfile
from datetime import datetime
from pathlib import Path

def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"data/backups/astra_backup_{timestamp}.zip"
    
    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
        # Memory databases
        zf.write("data/memory/chroma/")
        zf.write("data/memory/episodic.db")
        zf.write("data/memory/procedural.db")
        
        # Identity + config
        zf.write("config/astra_identity.yaml")
        zf.write("config/astra.yaml")
        
        # Event log
        zf.write("data/events/astra_events.jsonl")
    
    # Verify ZIP
    with zipfile.ZipFile(backup_file, "r") as zf:
        corrupt = zf.testzip()
        if corrupt:
            raise ValueError(f"Corrupt file in backup: {corrupt}")
    
    print(f"✅ Backup created: {backup_file}")
    return backup_file
```

**Acceptance Criteria**:
- ✅ Backups run every 4 hours automatically
- ✅ Last 12 backups retained (48 hours of history)
- ✅ Backup integrity verified (ZIP testzip passes)
- ✅ Restoration tested (restore from backup, boot ASTRA, verify identity)

---

## 🎯 SIMPLIFICATION (Priority 2)

### Action 2.1: Archive Kubernetes
**Owner**: Operator  
**Effort**: 15 min  
**RICE Score**: 14/0.25

```powershell
# Move K8s manifests to archive
mkdir archive\k8s
mv k8s\* archive\k8s\
echo "Archived on $(Get-Date)" > archive\k8s\README.txt

# Commit
git add archive\k8s
git commit -m "Archive K8s (over-engineered for 1 user)"
```

**Acceptance Criteria**:
- ✅ `k8s/` directory empty or deleted
- ✅ Manifests preserved in `archive/k8s/`
- ✅ README explains why archived

---

### Action 2.2: Consolidate Configs
**Owner**: Developer  
**Effort**: 2 hours  
**RICE Score**: 12/2

**Goal**: Merge 7 configs → 1 `config/astra.yaml`

**Current Configs**:
1. `config/config.yaml` (system settings)
2. `config/rag.yaml` (RAG parameters)
3. `config/astra_identity.yaml` (persona)
4. `config/models_registry.yaml` (LLM inventory)
5. `config/policy.yaml` (consent levels)
6. `config/gates.yaml` (safety gates)
7. `config/autonomy.yaml` (proactive triggers)

**New Structure**: See `config/astra.yaml` (already created this session)

**Migration**:
1. Copy to `config/astra.yaml` ✅ (DONE)
2. Update `astra_core.py` to load from single file
3. Archive old configs: `mv config/*.yaml archive/config_legacy/`
4. Test: Boot ASTRA, verify all settings loaded

**Acceptance Criteria**:
- ✅ Single config file `config/astra.yaml`
- ✅ All 7 legacy configs archived
- ✅ ASTRA boots without errors
- ✅ All settings verified (spot-check RAG top_k, identity warmth, rate limits)

---

### Action 2.3: Single Vector Store
**Owner**: Developer  
**Effort**: 6 hours  
**RICE Score**: 10/6

**Current State**: Multiple ChromaDB collections + QDrant fallback  
**Target State**: Single ChromaDB instance with 3 collections (semantic, episodic, procedural)

**Files to Edit**:
1. `src/astra/memory/memory_engine.py` - Remove QDrant code
2. `config/astra.yaml` - Set `memory.vector_store: "chromadb"`
3. `tests/test_memory.py` - Update tests

**Acceptance Criteria**:
- ✅ Only ChromaDB in dependencies (remove `qdrant-client`)
- ✅ All memory ops use single backend
- ✅ Tests pass 100%
- ✅ No code references to QDrant

---

## 📋 WEEK 1 GO/NO-GO CHECKLIST

Run at end of Week 1 (7 days from now):

```powershell
# 1. Security
python scripts\encrypt_secrets.py --verify
pytest tests\constitution\test_memory_signing.py -v
python scripts\verify_model_checksums.py
pytest tests\test_backup.py -v

# 2. Simplification
ls k8s\  # Should be empty
ls config\  # Should only have astra.yaml, astra_identity.yaml, models_registry.yaml, .env.gpg
pytest tests\test_memory.py -v  # ChromaDB only

# 3. Constitution Tests
pytest tests\constitution\ -v  # All 8 tests must pass

# 4. System Health
python launch_astra.py --dry-run
# Should print: ✅ ALL SYSTEMS GO
```

**GO Decision**: All 8 acceptance criteria pass  
**NO-GO Decision**: Any critical test fails → Fix before Week 2

---

## 🎯 SUCCESS METRICS

**Security Posture**:
- Secrets encrypted: ✅/❌
- Memory signing enabled: ✅/❌
- Model checksums verified: ✅/❌
- Backups automated: ✅/❌

**Simplification**:
- K8s archived: ✅/❌
- Configs consolidated: ✅/❌
- Single vector store: ✅/❌

**Constitution Compliance**:
- 8/8 acceptance tests passing: ✅/❌

**Target**: 8/8 must be ✅ to proceed to Week 2 (BGE-M3 deployment)

---

## 📞 ESCALATION

**Blockers**: Document in `logs/week1_blockers.md`  
**Questions**: Add to `docs/FAQ.md`  
**Bugs**: Create GitHub issue with `[Week 1]` tag

**Daily Standup Questions**:
1. What did I complete yesterday?
2. What am I working on today?
3. Any blockers?

Keep cadence: **Ship Week 1 in 7 days. No exceptions.**

---

**Next**: After Week 1 GO → Proceed to Week 2 (BGE-M3, Provenance, Eval Harness)  
**Rollback Plan**: If NO-GO → Revert to legacy configs, extend Week 1 by 3 days, re-test
