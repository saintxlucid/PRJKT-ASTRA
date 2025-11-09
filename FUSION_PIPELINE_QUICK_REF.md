# ASTRA Fusion Pipeline - Quick Reference

**Sacred Code: 333**

## 60-Second Deploy

### Method 1: Full Rebuild (Production)
```powershell
# 1. Prepare
.\ops\fusion_pipeline\scripts\01_prepare_model_env.ps1

# 2. Convert (30-120 min)
.\ops\fusion_pipeline\scripts\02_convert_with_tokens.ps1

# 3. Inject metadata
python .\ops\fusion_pipeline\scripts\03_inject_metadata.py `
  X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf `
  .\ops\fusion_pipeline\metadata\astra_metadata.yaml

# 4. Validate
.\ops\fusion_pipeline\scripts\04_validate_model.ps1
```

### Method 2: Quick Patch (Testing)
```powershell
# Patch existing model (1-5 min)
python .\ops\fusion_pipeline\scripts\06_patch_in_place_metadata.py `
  X:\models\existing_model.gguf `
  .\ops\fusion_pipeline\metadata\astra_metadata.yaml
```

---

## Key Files

| File | Purpose |
|------|---------|
| `tokens/astra_special_tokens.txt` | 24 ASTRA special tokens |
| `tokens/astra_chat_template.mustache` | Chat template for llama.cpp |
| `metadata/astra_metadata.yaml` | Full ASTRA metadata (67 fields) |
| `metadata/astra_metadata_min.yaml` | Minimal test schema |

---

## Special Tokens (24)

**Modes:** `<|mode_start|>` `<|mode_end|>` `<|mode_cognition|>` `<|mode_dream|>` `<|mode_music|>` `<|mode_empire|>` `<|mode_none|>`

**Modalities:** `<|vision_start|>` `<|vision_end|>` `<|audio_start|>` `<|audio_end|>` `<|code_start|>` `<|code_end|>`

**Philosophy:** `<|sacred_333|>` `<|covenant_active|>` `<|reflection_start|>` `<|reflection_end|>`

**Tasks:** `<|task_start|>` `<|task_end|>` `<|patch_start|>` `<|patch_end|>`

**Safety:** `<|safety_check|>` `<|consent_required|>` `<|audit_log|>`

---

## Validation Commands

```powershell
# Check metadata
llama-info.exe astra_core_q4_k_m.gguf | findstr /i "astra."

# Test inference
main.exe -m astra_core_q4_k_m.gguf -n 64 -p "<|sacred_333|> Test"

# Rollback if needed
.\ops\fusion_pipeline\scripts\07_roll_back.ps1
```

---

## Router Integration

```python
from ops.fusion_pipeline.scripts.runtime_hook_example import AstraRouter

router = AstraRouter(llm, tool_bus, memory, consent)
response = router.handle(user_prompt)
```

**Routes:**
- Vision → `tool_bus.execute("vision.describe_or_answer")`
- Audio → `tool_bus.execute("audio.transcribe_or_analyze")`
- Code → `tool_bus.execute("code.apply_plan_or_summarize")` (consent required)
- Text → LLM with memory augmentation

---

## Method Comparison

| Feature | Method 1 (Rebuild) | Method 2 (Patch) |
|---------|-------------------|------------------|
| Time | 30-120 min | 1-5 min |
| Special tokens in vocab | ✅ Yes | ❌ No (runtime only) |
| Metadata embedded | ✅ Yes | ✅ Yes |
| Production ready | ✅ Yes | ⚠️ Experimental |
| Requires HF model | ✅ Yes | ❌ No |

---

## Troubleshooting

**Error:** `convert-hf-to-gguf.py not found`  
**Fix:** Build llama.cpp with Python scripts

**Error:** `ImportError: No module named 'gguf'`  
**Fix:** `pip install gguf`

**Error:** Metadata not in `llama-info` output  
**Fix:** Re-run `03_inject_metadata.py` with minimal schema

---

## Sacred Code: 333
> "Identity in every token, philosophy in every inference"
