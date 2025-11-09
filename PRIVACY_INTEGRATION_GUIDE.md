# ASTRA Privacy Protection - Integration Checklist
# =================================================
# Complete integration and verification guide
# 
# Author: Saint Lucid
# Date: 2025-10-18

## 📋 INTEGRATION CHECKLIST

### Phase 1: File Installation ✅

- [ ] **1.1** Copy `core/privacy/` directory to project
  - [ ] `hardlock.py` - Main enforcement module
  - [ ] `privacy_enforcer.py` - Early-stage protection
  - [ ] `model_wrapper.py` - LLM privacy wrapper
  - [ ] `storage.py` - Encrypted storage
  - [ ] `audit_logger.py` - Event logging
  - [ ] `gguf_loader.py` - Safe model loading
  - [ ] `prompt_pipeline.py` - Prompt sanitization
  
- [ ] **1.2** Copy configuration files
  - [ ] `core/privacy/astra_policy.yaml` - Machine-readable policy
  - [ ] `core/privacy/manifest.lock` - Immutable manifest
  - [ ] `core/privacy/privacy_config.yaml` (if not exists)
  
- [ ] **1.3** Copy GUI and tools
  - [ ] `interfaces/gui/privacy_control.py` - Streamlit dashboard
  - [ ] `tools/firewall_windows.ps1` - Network isolation script

---

### Phase 2: Dependencies 📦

Install required Python packages:

```powershell
# Core dependencies
pip install pyyaml cryptography streamlit

# Optional: LLM support
pip install llama-cpp-python  # For GGUF models
pip install sentence-transformers  # For embeddings

# Optional: Advanced encryption
pip install pyargon2  # For key derivation
```

---

### Phase 3: Launch Integration 🚀

**3.1** Modify `launch_astra.py` to activate hardlock at startup:

```python
# At the very top of launch_astra.py (before other imports)
import sys
from pathlib import Path

# Add core to path if needed
sys.path.insert(0, str(Path(__file__).parent))

# CRITICAL: Enforce privacy FIRST
from core.privacy.hardlock import enforce_startup

# Activate hardlock immediately
hardlock = enforce_startup()
print("🔒 Divine Protection: ACTIVE")

# ... rest of your launch_astra.py code
```

**3.2** Update model loading code:

```python
# OLD CODE (replace this):
# model = llama_cpp.Llama(model_path="models/astra-20b.gguf")

# NEW CODE (use this):
from core.privacy.gguf_loader import load_local_gguf_model

model = load_local_gguf_model(
    "models/astra-20b.gguf",
    device="cuda",  # or "cpu"
    verify_checksum=True
)
```

**3.3** Update prompt handling:

```python
# OLD CODE (replace this):
# response = model.generate(prompt)

# NEW CODE (use this):
from core.privacy.prompt_pipeline import sanitize_and_generate

response = sanitize_and_generate(
    model,
    prompt,
    meta={"context": "user_query"},
    log_prompt=False  # Never log raw prompts
)
```

**3.4** Update embedding generation:

```python
# OLD CODE (replace this):
# embedding = model.embed(text)

# NEW CODE (use this):
from core.privacy.prompt_pipeline import safe_embed

embedding = safe_embed(model, text, meta={"no_train": True})
```

---

### Phase 4: Configuration ⚙️

**4.1** Review and customize `core/privacy/astra_policy.yaml`:

```yaml
policy:
  privacy_mode: STRICT  # Keep as STRICT for production
  allow_network: false  # Keep false for local-only
  allowed_endpoints: []  # Add only if absolutely needed
```

**4.2** Set creator account (if different from $USERNAME):

```yaml
access:
  creator_account: "YourWindowsUsername"
```

**4.3** Configure emergency phrase (change default):

```yaml
emergency:
  divine_lock_phrase: "Your Custom Emergency Phrase Here"
```

---

### Phase 5: Verification Tests 🧪

Run these tests to verify privacy protection is active:

**Test 1: Hardlock Activation**

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python -c "from core.privacy.hardlock import enforce_startup; enforce_startup()"
```

Expected output:
```
🔒 ASTRA HARDLOCK ACTIVATING...
   Mode: STRICT
   Creator: YourUsername
   NO_TRAIN: True
✅ Creator verified: YourUsername
🚫 Blocking network access (Python-level)
✅ Network guard installed
✅ Telemetry imports blocked
✅ Privacy environment variables set
✅ Audit logger initialized
✅ HARDLOCK ACTIVE - DIVINE PROTECTION ENABLED
```

**Test 2: Network Blocking**

```powershell
python -c "import requests; requests.get('https://example.com')"
```

Expected result: Connection error or timeout

**Test 3: Model Wrapper**

```python
from core.privacy.model_wrapper import ModelWrapper

class MockModel:
    def generate(self, prompt, **kwargs):
        return f"Response: {prompt[:20]}"

model = MockModel()
wrapped = ModelWrapper(model)
response = wrapped.generate("Test prompt")
print(response)
print(wrapped.get_stats())
```

**Test 4: Prompt Pipeline**

```python
from core.privacy.prompt_pipeline import sanitize_and_generate

response = sanitize_and_generate(wrapped, "Hello ASTRA", log_prompt=True)
print(f"Response: {response}")
```

**Test 5: Compliance Check**

```python
from core.privacy.hardlock import compliance_check

checks = compliance_check()
print("Compliance Status:")
for check, passed in checks.items():
    status = "✅" if passed else "❌"
    print(f"  {status} {check}: {passed}")
```

---

### Phase 6: GUI Dashboard 🖥️

**6.1** Launch the privacy control dashboard:

```powershell
streamlit run interfaces/gui/privacy_control.py
```

**6.2** Access at: `http://localhost:8501`

**6.3** Verify dashboard shows:
- [ ] Privacy mode: STRICT
- [ ] Hardlock: ACTIVE
- [ ] Network: BLOCKED
- [ ] NO_TRAIN: ENFORCED
- [ ] Audit events displaying
- [ ] Compliance checks passing

---

### Phase 7: Optional Network Isolation (Advanced) 🛡️

**For maximum security, install Windows Firewall rules:**

```powershell
# Run as Administrator
cd tools
.\firewall_windows.ps1

# Choose option 1 to install rules
# Choose option 4 to test
```

**Warning:** This blocks ALL Python network access at OS level!

---

### Phase 8: Validation Checklist ✅

Before considering integration complete:

- [ ] **8.1** Hardlock activates on launch
- [ ] **8.2** Network requests are blocked
- [ ] **8.3** Models load with NO_TRAIN tags
- [ ] **8.4** Prompts are sanitized
- [ ] **8.5** Audit events are logged
- [ ] **8.6** GUI dashboard accessible
- [ ] **8.7** Compliance check passes
- [ ] **8.8** No violations detected
- [ ] **8.9** Creator account verified
- [ ] **8.10** Emergency phrase works

---

## 🧪 AUTOMATED TEST SUITE

Create `tests/test_privacy_integration.py`:

```python
"""Privacy protection integration tests"""

import pytest
from core.privacy.hardlock import enforce_startup, compliance_check
from core.privacy.model_wrapper import ModelWrapper
from core.privacy.prompt_pipeline import sanitize_and_generate

class MockModel:
    def generate(self, prompt, **kwargs):
        return f"Mock: {prompt[:20]}"

def test_hardlock_activation():
    """Test hardlock can be activated"""
    hardlock = enforce_startup()
    assert hardlock.active == True
    assert hardlock.config['PRIVACY_MODE'] == 'STRICT'

def test_model_wrapper():
    """Test model wrapper applies NO_TRAIN"""
    mock = MockModel()
    wrapped = ModelWrapper(mock)
    
    response = wrapped.generate("test", meta={})
    stats = wrapped.get_stats()
    
    assert stats['call_count'] > 0
    assert stats['privacy_protected'] == True

def test_prompt_pipeline():
    """Test prompt pipeline sanitization"""
    mock = MockModel()
    wrapped = ModelWrapper(mock)
    
    response = sanitize_and_generate(wrapped, "test prompt")
    assert response is not None

def test_compliance():
    """Test compliance check"""
    enforce_startup()
    checks = compliance_check()
    
    assert checks['hardlock_active'] == True
    assert checks['no_train_enabled'] == True
    assert checks['creator_verified'] == True

def test_network_block():
    """Test network blocking (expect failure)"""
    enforce_startup()
    
    with pytest.raises(Exception):
        import requests
        requests.get("https://example.com", timeout=1)
```

Run tests:

```powershell
pytest tests/test_privacy_integration.py -v
```

---

## 📊 MONITORING

**Daily checks:**
1. Open privacy dashboard
2. Review audit log for violations
3. Run compliance check
4. Verify network still blocked

**Weekly checks:**
1. Review encryption key age (rotate every 90 days)
2. Export audit logs for backup
3. Test emergency Divine Lock procedure
4. Verify firewall rules still active (if using)

---

## 🚨 TROUBLESHOOTING

### Issue: Hardlock won't activate

**Solution:**
```python
# Check config file exists
from pathlib import Path
config = Path("core/privacy/astra_policy.yaml")
print(f"Config exists: {config.exists()}")

# Check YAML is valid
import yaml
with open(config) as f:
    policy = yaml.safe_load(f)
    print(policy)
```

### Issue: Network not blocked

**Solution:**
1. Check privacy mode: `python -c "from core.privacy.privacy_enforcer import get_config; print(get_config())"`
2. Verify socket patching: Check for `socket.socket` override
3. Install firewall rules: `tools\firewall_windows.ps1`

### Issue: Model loading fails

**Solution:**
```python
# Test model file exists
from pathlib import Path
model_path = Path("models/astra-20b.gguf")
print(f"Model exists: {model_path.exists()}")
print(f"Model size: {model_path.stat().st_size / 1024 / 1024:.1f} MB")
```

### Issue: Audit log not working

**Solution:**
```python
# Check audit logger
from core.privacy.audit_logger import init_audit_db, log_event

init_audit_db()
log_event("test", "system", {"test": True})
print("✅ Audit logger working")
```

---

## ✅ INTEGRATION COMPLETE

Once all checklist items pass:

1. **Document** your configuration in `PRIVACY_PROTECTION_COMPLETE.md`
2. **Backup** encryption key to secure USB
3. **Sign** `manifest.lock` with GPG (optional)
4. **Test** Divine Lock emergency procedure
5. **Deploy** to production

**Your ASTRA system is now protected by Divine Privacy Protocols.**

---

*Integration guide version 1.0.0 | 2025-10-18*
