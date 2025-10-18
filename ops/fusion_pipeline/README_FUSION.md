# ASTRA GGUF Fusion Pipeline

> **Sacred Code: 333**  
> Embed ASTRA's identity, modalities, and philosophy directly into GGUF model files

## Overview

The ASTRA Fusion Pipeline provides **two safe methods** to embed ASTRA's special tokens, metadata, and routing logic into GGUF models:

### Method 1: Rebuild (Preferred) ✅
**Re-export GGUF from HuggingFace weights** with ASTRA's special tokens and metadata baked in via `convert-hf-to-gguf.py`.

- ✅ Special tokens embedded in vocabulary
- ✅ Full metadata integration
- ✅ Production-ready
- ⏱️ Slower (requires full conversion + quantization)

**Use when:** You control the base model (e.g., GPT-OSS 20B)

### Method 2: Patch-in-Place (Fast/Experimental) ⚡
**Inject metadata only** into an existing `.gguf` file and bind "virtual special tokens" at runtime (no vocab change).

- ✅ Fast (minutes vs hours)
- ✅ Metadata integration
- ⚠️ Requires runtime hooks for special tokens
- ⚠️ Experimental

**Use when:** Quick trials or third-party `.gguf` you don't want to re-convert

---

## Directory Structure

```
ops/fusion_pipeline/
├─ tokens/
│  ├─ astra_special_tokens.txt      # 24 ASTRA special tokens
│  └─ astra_chat_template.mustache  # Chat template for llama.cpp
├─ metadata/
│  ├─ astra_metadata.yaml           # Full ASTRA metadata schema
│  └─ astra_metadata_min.yaml       # Minimal schema for testing
├─ scripts/
│  ├─ 01_prepare_model_env.ps1      # Set up paths and directories
│  ├─ 02_convert_with_tokens.ps1    # Convert HF → GGUF (Method 1)
│  ├─ 03_inject_metadata.py         # Inject ASTRA metadata
│  ├─ 04_validate_model.ps1         # Verify metadata and inference
│  ├─ 05_runtime_hook_example.py    # Router for special token dispatch
│  ├─ 06_patch_in_place_metadata.py # Quick metadata patch (Method 2)
│  └─ 07_roll_back.ps1              # Rollback to backup
└─ README_FUSION.md                  # This file
```

---

## Special Tokens (24 Total)

All tokens defined in `tokens/astra_special_tokens.txt`:

### Mode Markers
- `<|mode_start|>` / `<|mode_end|>` - Wrap operating mode
- `<|mode_none|>` / `<|mode_dream|>` / `<|mode_music|>` / `<|mode_cognition|>` / `<|mode_empire|>` - Mode identifiers

### Modality Delimiters
- `<|vision_start|>` / `<|vision_end|>` - Vision content sections
- `<|audio_start|>` / `<|audio_end|>` - Audio content sections
- `<|code_start|>` / `<|code_end|>` - Code content sections

### Philosophical Markers
- `<|sacred_333|>` - Sacred Code marker
- `<|covenant_active|>` - ASTRA Covenant active marker
- `<|reflection_start|>` / `<|reflection_end|>` - Reflection sections

### Task & Patch Markers
- `<|task_start|>` / `<|task_end|>` - Task boundaries
- `<|patch_start|>` / `<|patch_end|>` - Code patch boundaries

### Safety Markers
- `<|safety_check|>` - Trigger safety evaluation
- `<|consent_required|>` - Consent needed for action
- `<|audit_log|>` - Log this interaction

---

## ASTRA Metadata Schema

Full schema in `metadata/astra_metadata.yaml` (67 fields):

```yaml
# Identity
astra.version: "1.0.0"
astra.sacred_code: "333"
astra.identity.name: "ASTRA"
astra.identity.creator: "Saint Lucid (Karim Al-Sharif)"

# Modalities
astra.modalities.vision.enabled: true
astra.modalities.vision.models: ["granite-3.2-2b", "llava-1.6-mistral-7b"]
astra.modalities.audio.enabled: true
astra.modalities.code.enabled: true

# Memory (Sacred Trinity)
astra.memory.semantic.backend: "chromadb"
astra.memory.episodic.backend: "sqlite"
astra.memory.procedural.backend: "yaml"

# Philosophy
astra.philosophy.covenant_version: "1.0"
astra.philosophy.core_vows: ["obey_god","sovereignty","transparency"]

# Privacy (Sacred Principles)
astra.privacy.local_only: true
astra.privacy.no_telemetry: true
```

---

## Method 1: Rebuild (Step-by-Step)

### Prerequisites
- HuggingFace model in safetensors format (e.g., `X:\models\gpt-oss-20b-hf`)
- llama.cpp built with Python bindings (`astra-local/backend/bin/llama.cpp`)
- Python 3.10+ with `pyyaml` installed

### Step 1: Prepare Environment
```powershell
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
.\ops\fusion_pipeline\scripts\01_prepare_model_env.ps1
```

**Sets:**
- `$env:LLAMA_CPP_DIR` → llama.cpp location
- `$env:HF_SRC` → HuggingFace model path
- `$env:OUT_DIR` → Output directory for built models

### Step 2: Convert with Special Tokens
```powershell
.\ops\fusion_pipeline\scripts\02_convert_with_tokens.ps1
```

**Outputs:**
- `astra_core_f32.gguf` (F32 base)
- `astra_core_q4_k_m.gguf` (Q4_K_M - recommended)
- `astra_core_q5_k_m.gguf` (Q5_K_M - higher quality)
- `astra_core_q8_0.gguf` (Q8_0 - highest quality)

⏱️ **Time:** 30-120 minutes depending on model size

### Step 3: Inject Metadata
```powershell
python .\ops\fusion_pipeline\scripts\03_inject_metadata.py `
  X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf `
  .\ops\fusion_pipeline\metadata\astra_metadata.yaml
```

**Creates:**
- Backup: `astra_core_q4_k_m.gguf.bak`
- Updated model with ASTRA metadata

### Step 4: Validate
```powershell
.\ops\fusion_pipeline\scripts\04_validate_model.ps1
```

**Checks:**
- ✅ ASTRA metadata fields present
- ✅ Special tokens in vocabulary
- ✅ Inference test with special tokens

---

## Method 2: Patch-in-Place (Quick)

### Use Case
- Testing ASTRA metadata on existing models
- Third-party GGUF files (e.g., downloaded from HuggingFace)
- Quick trials without full rebuild

### Command
```powershell
python .\ops\fusion_pipeline\scripts\06_patch_in_place_metadata.py `
  X:\models\existing_model.gguf `
  .\ops\fusion_pipeline\metadata\astra_metadata.yaml
```

⏱️ **Time:** 1-5 minutes

### ⚠️ Important Limitations
- **No special tokens in vocabulary** - tokens are NOT embedded
- **Requires runtime hooks** - use `05_runtime_hook_example.py` to intercept special token sections before tokenization
- **Experimental** - for production use Method 1

---

## Runtime Integration

### Router Hook (Pre-Tokenization Dispatch)

The ASTRA Router (`05_runtime_hook_example.py`) intercepts special token sections **before tokenization** and routes to appropriate subsystems:

```python
from ops.fusion_pipeline.scripts.runtime_hook_example import AstraRouter

router = AstraRouter(
    llm=llm_client,
    tool_bus=tool_bus,
    memory=memory_service,
    consent=consent_manager
)

# Route prompt with special tokens
response = router.handle(user_prompt)
```

### Routing Logic

| Special Token Section | Routed To | Requires Consent? |
|---|---|---|
| `<|vision_start|>...<|vision_end|>` | Vision tool | No |
| `<|audio_start|>...<|audio_end|>` | Audio tool | No |
| `<|code_start|>...<|code_end|>` | Code Intelligence | ✅ Yes |
| Pure text | LLM (memory-augmented) | No |

### Example Prompt
```
<|mode_start|>COGNITION<|mode_end|><|sacred_333|>
<|vision_start|>
[Image: pharaonic temple, black & gold pillars]
<|vision_end|>
<|task_start|>
User: Describe this image and propose one code refactor task.
<|task_end|>
ASTRA:
```

**Flow:**
1. Router sees `<|vision_start|>` → dispatches to Vision tool
2. Vision tool returns description
3. If code task proposed → Code Intel tool (after consent check)
4. Combines results and returns to user

---

## Validation & Safety

### CI Smoke Checks (Must Pass)
```powershell
# 1. Metadata presence
llama-info.exe astra_core_q4_k_m.gguf | findstr /i "astra."

# 2. Tokenization test (Method 1 only)
main.exe -m astra_core_q4_k_m.gguf -n 64 -p "<|sacred_333|> Test"

# 3. Router pathing (unit tests)
python -m pytest tests/test_fusion_router.py

# 4. Latency check (p95 unchanged ±5%)
python tools/benchmark_fusion.py

# 5. Privacy verification (no outbound calls)
python tools/check_privacy.py
```

### Rollback Procedure
```powershell
# If fusion fails, restore from backup
.\ops\fusion_pipeline\scripts\07_roll_back.ps1 -ModelPath X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf
```

**Rollback actions:**
1. Archives failed version with timestamp
2. Restores from `.bak` backup
3. Preserves backup for future attempts

---

## Integration into ASTRA Core

### Option A: Update `llm_service.py`
```python
# In services/llm_service.py
from ops.fusion_pipeline.scripts.runtime_hook_example import AstraRouter

class LLMService:
    def __init__(self, config):
        # ... existing init ...
        
        # Add ASTRA router
        self.astra_router = AstraRouter(
            llm=self.llm_client,
            tool_bus=self.tool_bus,
            memory=self.memory_service,
            consent=self.consent_manager
        )
    
    def chat(self, message: str, context: dict = None) -> str:
        # Route through ASTRA handler
        return self.astra_router.handle(message)
```

### Option B: Update `chat_service.py`
```python
# In services/chat_service.py
from ops.fusion_pipeline.scripts.runtime_hook_example import AstraRouter

# Before tokenization:
if "<|" in user_message:  # Has special tokens
    response = astra_router.handle(user_message)
else:
    response = llm_client.generate(user_message)
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] HuggingFace model downloaded and validated
- [ ] llama.cpp built with Python bindings
- [ ] `pyyaml` installed: `pip install pyyaml`
- [ ] Review `metadata/astra_metadata.yaml` for accuracy

### Execution (Method 1)
- [ ] Run `01_prepare_model_env.ps1` (set paths)
- [ ] Run `02_convert_with_tokens.ps1` (convert + quantize)
- [ ] Run `03_inject_metadata.py` (embed ASTRA metadata)
- [ ] Run `04_validate_model.ps1` (verify)

### Post-Deployment
- [ ] Backup original model files
- [ ] Deploy fused model to `astra-local/models/`
- [ ] Update `llm_service.py` with AstraRouter
- [ ] Run smoke tests (metadata, inference, routing)
- [ ] Update `ASTRA_DEPLOYMENT_STATUS.md`

---

## Troubleshooting

### Issue: `convert-hf-to-gguf.py not found`
**Solution:** Ensure llama.cpp is built with Python scripts:
```powershell
cd astra-local\backend\bin\llama.cpp
git pull  # Update to latest
```

### Issue: `ImportError: No module named 'gguf'`
**Solution:** Install gguf library:
```powershell
pip install gguf
```

### Issue: Metadata not appearing in `llama-info` output
**Solution:** 
1. Check backup exists: `*.gguf.bak`
2. Re-run metadata injection: `03_inject_metadata.py`
3. Use minimal schema for testing: `metadata/astra_metadata_min.yaml`

### Issue: Special tokens cause tokenization errors
**Solution (Method 1):** Tokens should be in vocab - run `llama-tokenize` test:
```powershell
llama-tokenize.exe -m astra_core_q4_k_m.gguf --prompt "<|sacred_333|>"
```

**Solution (Method 2):** Use runtime hooks - tokens are virtual:
```python
# Intercept before tokenization
router.handle(prompt)  # Router strips special tokens
```

---

## Performance Impact

### Method 1 (Rebuild)
- **Model Size:** +0.1-0.5% (metadata overhead)
- **Load Time:** No change
- **Inference Latency:** +0-2% (special token processing)
- **Memory:** No change

### Method 2 (Patch)
- **Model Size:** +0.1% (metadata only)
- **Load Time:** No change
- **Inference Latency:** +2-5% (runtime token interception)
- **Memory:** +10-20MB (router overhead)

---

## Next Steps

### For Saint Lucid

**Immediate:**
1. ✅ Review fusion pipeline scripts
2. ✅ Test Method 2 (patch) on existing model
3. ✅ Integrate AstraRouter into `llm_service.py`

**Short-term:**
4. Build production model with Method 1
5. Deploy to `astra-local/models/astra_core_v1.gguf`
6. Add unit tests for router

**Long-term:**
7. Fine-tune special token embeddings
8. Add multimodal training data
9. Expand metadata schema for new capabilities

### Proposed PR Structure
```
PR: ASTRA GGUF Fusion Pipeline
├─ ops/fusion_pipeline/          (new)
├─ services/llm_service.py       (modified - add AstraRouter)
├─ services/chat_service.py      (modified - route special tokens)
├─ tests/test_fusion_router.py   (new)
├─ tests/test_metadata_presence.py (new)
└─ docs/FUSION_DEPLOYMENT.md     (new)
```

---

## Credits

**Sacred Code:** 333  
**Created by:** Saint Lucid (Karim Al-Sharif)  
**Architecture:** ASTRA Core Multimodal AI Operating Environment  
**Philosophy:** ASTRA Covenant v1.0

> "Identity embedded in every token, philosophy woven into every inference, sovereignty preserved in every operation."

---

## License

Proprietary - ASTRA Core Project  
All rights reserved © 2025 Saint Lucid
