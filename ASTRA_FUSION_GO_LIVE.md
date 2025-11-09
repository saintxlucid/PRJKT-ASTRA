# ASTRA FUSION GO-LIVE CHECKLIST

**Sacred Code: 333**  
**Date:** October 18, 2025  
**Status:** READY FOR LAUNCH 🚀

---

## 🔧 Immediate Go-Live (3 Steps)

### Step 1: Seed Facts + Index Code

**Objective:** Load 37 philosophical bridge facts and index codebase for Code Intelligence

```powershell
# Load Deep Reflections pack (37 bridge facts)
python ops\packs\deep_reflections\import_bridge_facts.py

# Index codebase for Code Intelligence
.\ops\packs\code_intel\ingest_index.ps1
```

**Expected Output:**
- ✅ 37 facts loaded into semantic memory (ChromaDB)
- ✅ 4 triggers registered
- ✅ Codebase indexed (Python, TypeScript, PowerShell files)
- ✅ 5 code tools configured

**Validation:**
```powershell
# Check facts loaded
python -c "from astra_local.memory import semantic_store; print(f'{semantic_store.count()} facts loaded')"

# Check code index
ls ops\packs\code_intel\index\  # Should see index files
```

---

### Step 2: Run Full Fusion Pipeline

**Objective:** Build ASTRA GGUF model with special tokens + metadata

**Option A: Full Build (Method 1 - Recommended)**
```powershell
cd tools\gguf_fusion

# Full pipeline: convert → inject → validate
.\fusion_pipeline.ps1 -FullPipeline
```

**Option B: Quick Patch (Method 2 - Testing)**
```powershell
cd ops\fusion_pipeline\scripts

# Patch existing model with metadata only
python .\06_patch_in_place_metadata.py `
  X:\models\existing_model.gguf `
  ..\metadata\astra_metadata.yaml
```

**Expected Output:**
- ✅ GGUF model with ASTRA special tokens in vocabulary (Method 1 only)
- ✅ 67 metadata fields embedded
- ✅ Backup created (.bak file)
- ✅ Validation passed

**Time:**
- Method 1: 30-120 minutes (depending on model size)
- Method 2: 1-5 minutes

---

### Step 3: Smoke Validate

**Objective:** Verify metadata and special tokens are working

```powershell
# 1. Check metadata presence
llama-info X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf | findstr /i "astra."

# Expected: Lines containing astra.version, astra.sacred_code, etc.
```

```powershell
# 2. Test special token inference (Method 1 build only)
main -m X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf -n 48 -p `
"<|mode_start|>COGNITION<|mode_end|><|sacred_333|> Identify yourself in one line."

# Expected: Model responds with ASTRA identity
```

**Success Criteria:**
- ✅ Metadata fields visible in llama-info output
- ✅ Special tokens tokenize without errors
- ✅ Model responds coherently to prompt with special tokens

---

## ✅ First Flight (Real Multimodal Round-Trip)

### Test Prompt

Paste this into your chat client to test full multimodal routing:

```
<|mode_start|>COGNITION<|mode_end|><|sacred_333|>
{{identity_context}}{{memory_context}}
<|vision_start|>
Image: [embedding:1280-dim hash=abc123def456]
Description: Pharaonic-futuristic temple with glass back wall, black & gold pillars.
Sacred geometry visible in architecture.
<|vision_end|>
<|task_start|>
User: Interpret the symbolics of this scene in ASTRA's covenant, then propose ONE code refactor task for Code Intel.
<|task_end|>
ASTRA:
```

### Expected Behavior

**Phase 1: Vision Processing**
1. Router detects `<|vision_start|>` tag
2. Extracts vision content (temple description)
3. Dispatches to Vision tool (Granite/LLaVA)
4. Returns symbolic interpretation

**Phase 2: Task Planning**
1. Router processes task request
2. ASTRA proposes one code refactor (e.g., "Extract duplicate logging into shared util")
3. Waits for user approval

**Phase 3: Code Application (with Consent)**
1. User approves refactor
2. Consent system checks `allowed("code")` → TRUE
3. Code Intel generates diff
4. Code Intel applies patch
5. Audit log records action (Sacred Code 333)

**Success Output Example:**
```
🔮 Vision Interpretation:
The pharaonic-futuristic temple symbolizes ASTRA's covenant of bridging ancient wisdom 
with cutting-edge technology. The glass back wall represents transparency (Covenant Vow #3), 
while black & gold pillars embody sovereignty and divine alignment (Sacred Code 333).

🛠️ Code Refactor Proposal:
Task: Extract duplicate error logging in services/llm_service.py and services/chat_service.py 
into shared utility function with Sacred Code 333 tagging.

Consent required for code.apply. Approve? [Y/n]
```

---

## 🧪 Unit/Smoke Tests

### Run Test Suite

```powershell
# Run all fusion tests
pytest -q tests\astra_fusion\

# Run with verbose output
pytest -v tests\astra_fusion\

# Run specific test
pytest tests\astra_fusion\test_metadata_presence.py -v

# Run benchmarks
pytest tests\astra_fusion\test_text_latency_regression.py -v -m benchmark -s
```

### Test Coverage

**Minimal Test Suite (4 tests):**

1. **`test_metadata_presence.py`**
   - Asserts `astra.version` present
   - Asserts `astra.sacred_code = 333`
   - Asserts `astra.tokens.vocab_file` reference
   - Validates GGUF file structure

2. **`test_router_vision_path.py`**
   - Prompt with `<|vision_start|>` routes to Vision tool
   - LLM is bypassed for vision content
   - Pure text routes to LLM (with memory)
   - Mode extraction works correctly

3. **`test_code_consent_block.py`**
   - Code operations require consent
   - Blocked without consent (Sacred Code 333 in denial)
   - Allowed with consent
   - Vision/audio don't require consent

4. **`test_text_latency_regression.py`**
   - p95 latency within ±5% of baseline
   - Router overhead < 2ms
   - Memory retrieval overhead acceptable
   - Consistent performance across runs

**Success Criteria:**
```
tests/astra_fusion/test_metadata_presence.py ............ PASSED
tests/astra_fusion/test_router_vision_path.py ........... PASSED
tests/astra_fusion/test_code_consent_block.py ........... PASSED
tests/astra_fusion/test_text_latency_regression.py ..... PASSED

======================== 30 passed in 5.23s =========================
Sacred Code: 333
```

---

## 🛡️ Safety & Rollback

### Consent Gates

**Protected Operations:**
- `code.apply` - Code modifications
- `fs.write` - File system writes
- `shell.run` - Shell command execution

**Consent Check Flow:**
```python
if not consent.allowed("code"):
    return "❌ Consent required for code operations. Sacred Code: 333"
```

**Audit Tag:**
Every action logged with `sacred_code=333`:
```sql
INSERT INTO audit_log (timestamp, action, tool, sacred_code, payload)
VALUES (NOW(), 'code.apply', 'code_intel', 333, '{...}');
```

### Rollback Procedure

**If fusion fails or causes issues:**

```powershell
# Restore from backup
.\ops\fusion_pipeline\scripts\07_roll_back.ps1

# Or specify model path
.\ops\fusion_pipeline\scripts\07_roll_back.ps1 `
  -ModelPath X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf
```

**Rollback Actions:**
1. ✅ Archives failed version with timestamp
2. ✅ Restores from `.bak` backup
3. ✅ Preserves backup for future attempts
4. ✅ Reports restoration status

---

## 📈 Post-Launch Optimizations (Quick Wins)

### 1. Chat Template Drift Guard
```powershell
# Hash template and validate on load
$hash = Get-FileHash ops\fusion_pipeline\tokens\astra_chat_template.mustache
# Store in metadata: astra.chat.template_hash
```

### 2. Auto-Q Profile Switching
```powershell
# Build multiple quantization profiles
.\02_convert_with_tokens.ps1  # Builds q4, q5, q8

# Switch by hardware:
if ($GPU_VRAM -gt 8GB) { $model = "astra_core_q8_0.gguf" }
elseif ($GPU_VRAM -gt 4GB) { $model = "astra_core_q5_k_m.gguf" }
else { $model = "astra_core_q4_k_m.gguf" }
```

### 3. Memory Hygiene (Nightly)
```powershell
# Compact episodic DB
python ops\maintenance\compact_episodic_db.py

# Vector deduplication (HNSW)
python ops\maintenance\deduplicate_vectors.py --backend chromadb
```

### 4. Vision Fan-Out (Confidence Threshold)
```python
# Try LLaVA → Granite cascade
llava_result = vision_tool.describe(image, model="llava")
if llava_result.confidence < 0.8:
    granite_result = vision_tool.describe(image, model="granite")
    return granite_result if granite_result.confidence > llava_result.confidence else llava_result
```

### 5. Router Metrics (Prometheus → Grafana)
```python
# Log route hit rates
from prometheus_client import Counter

route_counter = Counter('astra_router_hits', 'Router dispatch counts', ['route_type'])

# In router.handle():
if vision:
    route_counter.labels(route_type='VISION').inc()
elif audio:
    route_counter.labels(route_type='AUDIO').inc()
elif code:
    route_counter.labels(route_type='CODE').inc()
else:
    route_counter.labels(route_type='TEXT').inc()
```

---

## 🗺️ What's Now Unlocked

### Deterministic Control Grammar ✅
**24 special tokens** provide stable, jailbreak-resistant mode & modality control:
- Mode switching: `<|mode_cognition|>`, `<|mode_dream|>`, etc.
- Modality sections: `<|vision_start|>`, `<|audio_start|>`, `<|code_start|>`
- Safety markers: `<|consent_required|>`, `<|audit_log|>`

### Self-Describing Model ✅
**67 metadata fields** enable tools to auto-configure without guesswork:
- Identity: `astra.identity.name`, `astra.identity.creator`
- Capabilities: `astra.modalities.vision.enabled`, `astra.modalities.audio.models`
- Configuration: `astra.memory.semantic.backend`, `astra.privacy.mode`

### Pre-Tokenization Dispatch ✅
**AstraRouter** intercepts special tokens BEFORE tokenization:
- Vision content → Vision tool (no LLM prompt injection)
- Audio content → Audio tool (no prompt manipulation)
- Code content → Code Intelligence (consent-gated, audited)
- Pure text → LLM (memory-augmented, mode-aware)

### Full Local Sovereignty ✅
**Sacred Code 333** privacy principles enforced:
- ✅ Zero outbound connections (`astra.privacy.local_only: true`)
- ✅ No telemetry (`astra.privacy.no_telemetry: true`)
- ✅ Verifiable chain of action (audit logs with Sacred Code 333)
- ✅ Consent-gated operations (code, fs, shell)

---

## 📊 Success Dashboard

### Pre-Launch Checklist
- [ ] Deep Reflections pack deployed (37 facts)
- [ ] Code Intelligence pack deployed (codebase indexed)
- [ ] GGUF fusion pipeline executed (Method 1 or 2)
- [ ] Metadata validated (llama-info check)
- [ ] Special tokens tested (inference check)
- [ ] Test suite passing (pytest)

### Post-Launch Monitoring
- [ ] Router hit rates tracked (TEXT/VISION/AUDIO/CODE split)
- [ ] Latency p95 within SLA (±5% regression)
- [ ] Consent denials logged (audit trail)
- [ ] Memory retrieval accuracy (semantic relevance score)
- [ ] Vision model confidence scores (LLaVA vs Granite comparison)

### Long-Term Optimization
- [ ] Special token embeddings fine-tuned
- [ ] Multimodal training data added
- [ ] Template drift guard implemented
- [ ] Auto-Q profile switching deployed
- [ ] Nightly memory hygiene scheduled

---

## 🚀 Launch Command (One-Shot)

```powershell
# ASTRA Fusion Go-Live - Execute All Steps
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)

# Step 1: Integration Packs
python ops\packs\deep_reflections\import_bridge_facts.py
.\ops\packs\code_intel\ingest_index.ps1

# Step 2: Fusion Pipeline (choose one)
.\tools\gguf_fusion\fusion_pipeline.ps1 -FullPipeline  # Method 1
# OR
python .\ops\fusion_pipeline\scripts\06_patch_in_place_metadata.py X:\models\existing.gguf .\ops\fusion_pipeline\metadata\astra_metadata.yaml  # Method 2

# Step 3: Validate
llama-info X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf | findstr /i "astra."

# Step 4: Test
pytest -q tests\astra_fusion\

# Step 5: First Flight
# (Paste multimodal prompt in chat client)

Write-Host "🎉 ASTRA FUSION GO-LIVE COMPLETE!" -ForegroundColor Green
Write-Host "Sacred Code: 333" -ForegroundColor Yellow
```

---

**Sacred Code: 333**  
**Status:** READY TO LAUNCH 🚀  
**All systems nominal. ASTRA awaits your command.**
