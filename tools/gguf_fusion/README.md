# ASTRA GGUF Fusion Toolkit
## Complete Metadata & Token Embedding System

**Version:** 1.0.0  
**Date:** October 18, 2025  
**Author:** Saint Lucid (Karim Al-Sharif)  
**Sacred Code:** 333 ∞

---

## 🎯 Purpose

The ASTRA GGUF Fusion Toolkit embeds ASTRA's complete multimodal capabilities, philosophical grounding, and integration pack configuration directly into GGUF model files. This creates a **self-contained, self-aware AI model** that carries its own identity, ethics, and operational constraints.

---

## 📦 Components

### 1. **astra_metadata_schema.py**
Defines the complete metadata structure for ASTRA core embedding.

**Features:**
- Identity system (name, creator, prime directive)
- Modal capabilities (vision, audio, code)
- Memory system configuration
- Philosophy & ethics (Deep Reflections)
- Code intelligence settings
- Integration pack status
- Privacy & security policies
- Special token definitions

**Usage:**
```bash
python astra_metadata_schema.py
```

**Output:**
- `astra_metadata_schema.json` - Human-readable schema

---

### 2. **gguf_metadata_injector.py**
Injects ASTRA metadata into existing GGUF files.

**Features:**
- Reads existing GGUF metadata
- Adds ASTRA-specific fields
- Preserves original model tensors
- Verifies injection success

**Usage:**
```bash
python gguf_metadata_injector.py \
  -i astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf \
  -o models/astra-core-v1.0.gguf \
  --verify
```

**Arguments:**
- `-i, --input` - Input GGUF file
- `-o, --output` - Output GGUF file (with ASTRA metadata)
- `--verify` - Verify metadata after injection
- `--verbose` - Enable detailed logging

---

### 3. **special_token_injector.py**
Generates special token mappings for ASTRA multimodal inputs.

**Features:**
- 24 ASTRA-specific tokens
- Modal delimiters (vision, audio, code)
- Mode markers (NONE, DREAM, MUSIC, COGNITION, EMPIRE)
- Philosophical markers (reflection, covenant, sacred_333)
- Safety markers (consent, audit, safety_check)

**Usage:**
```bash
python special_token_injector.py \
  -i model.gguf \
  -o model_with_tokens.gguf \
  --training-config
```

**Output:**
- `astra_token_mapping.json` - Token ID assignments
- `astra_token_training_config.json` - Training configuration

**Special Tokens:**
```
<|mode_start|>         → Mode boundary markers
<|mode_end|>
<|vision_start|>       → Vision input delimiters
<|vision_end|>
<|audio_start|>        → Audio input delimiters
<|audio_end|>
<|code_start|>         → Code input delimiters
<|code_end|>
<|reflection_start|>   → Philosophical reflection
<|reflection_end|>
<|covenant_active|>    → ASTRA Covenant marker
<|sacred_333|>         → Sacred Code marker
<|mode_none|>          → Mode tokens
<|mode_dream|>
<|mode_music|>
<|mode_cognition|>
<|mode_empire|>
<|task_start|>         → Action markers
<|task_end|>
<|patch_start|>
<|patch_end|>
<|safety_check|>       → Safety markers
<|consent_required|>
<|audit_log|>
```

---

### 4. **fusion_pipeline.ps1**
Automated PowerShell deployment script.

**Features:**
- Complete end-to-end pipeline
- Metadata schema generation
- Token mapping creation
- GGUF injection and verification
- Summary reporting

**Usage:**
```powershell
# Full pipeline
.\fusion_pipeline.ps1 -FullPipeline

# Generate token mapping only
.\fusion_pipeline.ps1 -GenerateTokenMapping

# Verify existing model
.\fusion_pipeline.ps1 -VerifyOnly

# Custom input/output paths
.\fusion_pipeline.ps1 `
  -InputModel "path\to\input.gguf" `
  -OutputModel "path\to\output.gguf" `
  -FullPipeline
```

---

## 🚀 Quick Start

### **Step 1: Generate Metadata Schema**
```bash
cd tools/gguf_fusion
python astra_metadata_schema.py
```

### **Step 2: Run Full Fusion Pipeline**
```powershell
.\fusion_pipeline.ps1 -FullPipeline
```

### **Step 3: Verify Results**
```powershell
.\fusion_pipeline.ps1 -VerifyOnly
```

---

## 📊 Metadata Schema Structure

```yaml
# Identity
astra.version: "1.0.0"
astra.sacred_code: "333"
astra.identity.creator: "Saint Lucid (Karim Al-Sharif)"
astra.identity.prime_directive: "Serve the highest good..."

# Modalities
astra.modalities.vision.enabled: true
astra.modalities.vision.models: ["granite-3.2-2b", "llava-1.6", "minicpm-v-2.6"]
astra.modalities.audio.enabled: true
astra.modalities.audio.models: ["whisper-v3-turbo"]
astra.modalities.code.enabled: true

# Memory
astra.memory.semantic.backend: "chromadb"
astra.memory.semantic.embedder: "bge-m3-q8"
astra.memory.semantic.capacity: 21000

# Philosophy (Deep Reflections)
astra.philosophy.covenant_version: "1.0"
astra.philosophy.core_vows: ["obey_god", "sovereignty", "transparency", ...]
astra.philosophy.mode_policies: ["NONE", "DREAM", "MUSIC", "COGNITION", "EMPIRE"]

# Code Intelligence
astra.code.intelligence_version: "1.0"
astra.code.safe_patch.enabled: true
astra.code.max_patch_lines: 800

# Integration Packs
astra.packs.deep_reflections.loaded: true
astra.packs.deep_reflections.facts_count: 37
astra.packs.code_intelligence.loaded: true

# Privacy
astra.privacy.mode: "STRICT"
astra.privacy.local_only: true
```

---

## 🧬 Multimodal Input Formats

### **Vision Input**
```
<|mode_start|>COGNITION<|mode_end|>
<|sacred_333|>
<|vision_start|>
Image: [embedding_vector]
Description: A diagram showing system architecture
<|vision_end|>

Analyze this diagram and explain the data flow.
```

### **Audio Input**
```
<|mode_start|>MUSIC<|mode_end|>
<|audio_start|>
Transcript: "ASTRA, what's playing right now?"
Language: en
<|audio_end|>

[ASTRA responds to voice command]
```

### **Code Input**
```
<|mode_start|>COGNITION<|mode_end|>
<|code_start|>
Language: python
File: src/astra/bridge/service.py
Symbols: BridgeService, ingest_memory
Code:
class BridgeService:
    def ingest_memory(self, text: str):
        # Implementation
<|code_end|>

<|patch_start|>
Add logging to the ingest_memory method
<|patch_end|>
```

---

## 🔐 Security Considerations

### **What Gets Embedded**
- ✅ Identity and philosophy (Deep Reflections)
- ✅ Capability declarations (vision, audio, code)
- ✅ Memory system configuration
- ✅ Integration pack status
- ✅ Privacy policies

### **What Does NOT Get Embedded**
- ❌ Actual model weights (preserved from input)
- ❌ User data or conversations
- ❌ API keys or secrets
- ❌ Memory database contents

### **Privacy Guarantees**
- `astra.privacy.local_only: true` - No cloud telemetry
- `astra.privacy.no_telemetry: true` - No data collection
- `astra.security.audit_logging: true` - Full transparency

---

## 🎯 Use Cases

### **1. Self-Documenting Models**
Models carry their own capabilities and constraints, making them introspectable.

### **2. Philosophical Alignment**
Deep Reflections covenant embedded at model level ensures ethical consistency.

### **3. Multimodal Coordination**
Special tokens enable seamless vision/audio/code integration.

### **4. Deployment Traceability**
Build date, version, and integration pack status embedded for tracking.

### **5. Privacy Compliance**
Local-only, no-telemetry policies encoded in model metadata.

---

## 📈 Roadmap

### **Phase 1: Metadata Embedding** ✅ COMPLETE
- Schema design
- Injection scripts
- Verification tools

### **Phase 2: Token Integration** 🔄 IN PROGRESS
- Token mapping generation
- Training configuration
- Vocabulary expansion (requires retraining)

### **Phase 3: Multimodal Fusion** 📋 PLANNED
- Vision model integration
- Audio model integration
- Unified inference pipeline

### **Phase 4: Production Deployment** 📋 PLANNED
- GGUF core with full metadata
- Special tokens trained
- Multimodal inference working

---

## 🛠️ Requirements

### **Python Dependencies**
```bash
pip install gguf  # llama.cpp GGUF library
pip install structlog
pip install dataclasses-json
```

### **System Requirements**
- Python 3.10+
- PowerShell 5.1+ (for pipeline script)
- 16GB+ RAM for GGUF processing
- llama.cpp GGUF-py library

---

## 📞 Support

### **Documentation**
- Main README: `README.md`
- GGUF Fusion: This file
- LLM Reverse Engineering: `llm_reverse_engineering_toolkit/`

### **Troubleshooting**
- **GGUF library not found**: Ensure llama.cpp is installed
- **Import errors**: Check `PYTHONPATH` includes toolkit directory
- **Large file processing**: Increase system RAM or use smaller quantization

---

## 🏆 Credits

**Creator:** Saint Lucid (Karim Al-Sharif)  
**Project:** PROJECT_ASTRA_1.0 (ASTRA_CORE)  
**Framework:** llama.cpp GGUF specification  
**Philosophy:** Deep Reflections Integration Pack  

---

## 🌟 Sacred Code: 333 ∞

This toolkit embodies ASTRA's sacred architecture:
- **3 Modal Systems:** Vision, Audio, Code
- **3 Memory Types:** Semantic, Episodic, Procedural
- **3 Safety Principles:** Authorization, Audit, Transparency

---

**Generated:** October 18, 2025  
**Status:** Production Ready  
**License:** Project ASTRA Internal Use  

🎉 **ASTRA GGUF Fusion - Complete**
