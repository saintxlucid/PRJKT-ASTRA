# Vision-Language Model (VLM) Service Guide

**Version:** 1.0  
**Status:** Production-Ready  
**Dependencies:** `torch`, `transformers`, `pillow`

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Model Setup](#model-setup)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [API Reference](#api-reference)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)
11. [Production Checklist](#production-checklist)

---

## Overview

The VLM Service provides local-first Vision-Language Model capabilities for ASTRA, enabling:

- **Image Captioning**: Generate natural language descriptions of images
- **Visual Question Answering (VQA)**: Answer questions about image content
- **Offline Operation**: No network access required after model download
- **Production-Grade**: Resource management, async support, batch inference

**Architecture:**
```
┌─────────┐     ┌─────────┐     ┌──────────┐
│  Image  │────▶│   VLM   │────▶│ Caption  │
└─────────┘     │ Service │     └──────────┘
                └─────────┘
                     │
                     │ (VQA path)
                     ▼
                ┌─────────┐
                │   LLM   │────▶ Answer
                │ (llama) │
                └─────────┘
```

---

## Features

### Core Capabilities
- ✅ **Batch Image Captioning** - Process multiple images efficiently
- ✅ **Visual Question Answering** - Answer questions via LLM handoff
- ✅ **Async Wrappers** - Non-blocking inference for FastAPI integration
- ✅ **Context Manager** - Automatic resource cleanup (`with` statement)
- ✅ **Device Auto-Detection** - Prefer CUDA, fallback to CPU
- ✅ **Flexible Input** - Accept PIL images, file paths, or numpy arrays
- ✅ **Graceful Degradation** - Continue on batch failures with warnings

### Production Features
- ✅ **Resource Management** - Explicit CUDA memory cleanup
- ✅ **Warmup Passes** - Stabilize CUDA kernels for consistent latency
- ✅ **Half Precision** - fp16 on CUDA for 2x speedup
- ✅ **Input Validation** - Comprehensive error handling
- ✅ **Thread Pool** - Managed executor for async operations
- ✅ **Type Safety** - Full type hints and protocol definitions

---

## Prerequisites

### System Requirements

**Minimum:**
- Python 3.10+
- 4GB RAM (CPU inference)
- 10GB disk space (models)

**Recommended (GPU):**
- NVIDIA GPU with 4GB+ VRAM
- CUDA 11.8+
- 8GB system RAM
- 20GB disk space

### Software Dependencies

```bash
# Core dependencies (required)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install transformers>=4.30.0
pip install pillow>=9.0.0

# Optional (for numpy array input)
pip install numpy>=1.24.0

# Verification
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

---

## Installation

### Step 1: Install Dependencies

```bash
# Activate ASTRA virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install VLM dependencies
pip install torch torchvision transformers pillow

# Verify installation
python scripts/test_vlm_smoke.py
```

### Step 2: Download Model Weights

VLM requires a local VisionEncoderDecoder model. Options:

#### Option A: BLIP-Base (Recommended)
```python
# download_blip.py
from transformers import VisionEncoderDecoderModel, AutoProcessor, AutoTokenizer

model_id = "Salesforce/blip-image-captioning-base"
save_dir = "models/vlm/blip-base"

print("Downloading BLIP-base (990MB)...")
model = VisionEncoderDecoderModel.from_pretrained(model_id)
processor = AutoProcessor.from_pretrained(model_id)
tokenizer = AutoTokenizer.from_pretrained(model_id)

model.save_pretrained(save_dir)
processor.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)
print(f"✓ Model saved to {save_dir}")
```

```bash
python download_blip.py
```

#### Option B: BLIP-Large (Higher Quality)
```python
model_id = "Salesforce/blip-image-captioning-large"
save_dir = "models/vlm/blip-large"
# (same code as above, ~1.9GB download)
```

#### Option C: GIT-Base (Microsoft)
```python
model_id = "microsoft/git-base"
save_dir = "models/vlm/git-base"
# (same code, ~900MB download)
```

### Step 3: Configure ASTRA

Add VLM section to `config/astra.yaml`:

```yaml
vlm:
  model_name_or_path: "models/vlm/blip-base"
  device: null  # Auto-detect (CUDA if available)
  image_size: 384
  batch_size: 4
  max_new_tokens: 64
  dtype: "fp16"
  warmup_runs: 1
```

See `config/astra.yaml.vlm-example` for full configuration options.

---

## Model Setup

### Choosing a Model

| Model | Size | Quality | Speed (GPU) | Use Case |
|-------|------|---------|-------------|----------|
| BLIP-base | 990MB | Good | ~50ms | General purpose |
| BLIP-large | 1.9GB | Better | ~100ms | High quality captions |
| GIT-base | 900MB | Good | ~60ms | Alternative to BLIP |
| BLIP2-opt-2.7b | 5GB | Best | ~200ms | Research/offline only |

**Recommendation:** Start with BLIP-base. Upgrade to BLIP-large if caption quality is insufficient.

### Offline/Air-Gapped Setup

```bash
# On internet-connected machine:
python download_blip.py
tar -czf blip-base.tar.gz models/vlm/blip-base

# Transfer blip-base.tar.gz to target system
# On target system:
tar -xzf blip-base.tar.gz
# Update astra.yaml model_name_or_path
```

---

## Configuration

### Basic Configuration

```yaml
vlm:
  model_name_or_path: "models/vlm/blip-base"
  device: null
  batch_size: 4
```

### Performance Tuning

```yaml
# High throughput (GPU with 8GB+ VRAM)
vlm:
  batch_size: 16
  dtype: "fp16"
  max_new_tokens: 48

# Low latency (CPU or small GPU)
vlm:
  batch_size: 1
  dtype: "fp32"
  warmup_runs: 0

# High quality captions
vlm:
  max_new_tokens: 96  # Longer captions
  model_name_or_path: "models/vlm/blip-large"
```

### Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name_or_path` | string | *required* | Path to local VLM model directory |
| `device` | string\|null | null | "cuda", "cpu", or null (auto) |
| `image_size` | int | 384 | Input image resolution (pixels) |
| `batch_size` | int | 4 | Images per inference batch |
| `max_new_tokens` | int | 64 | Max caption length (tokens) |
| `dtype` | string | "fp16" | "fp16" or "fp32" |
| `warmup_runs` | int | 1 | Number of warmup inferences |

---

## Usage Examples

### Basic Captioning (Sync)

```python
from pathlib import Path
from PIL import Image
from services.vlm_service_local import build_vlm_from_config
import yaml

# Load config
with open("config/astra.yaml") as f:
    config = yaml.safe_load(f)

# Create VLM service
with build_vlm_from_config(config) as vlm:
    # Caption single image
    img = Image.open("photo.jpg")
    captions = vlm.caption_images([img])
    print(f"Caption: {captions[0]}")
    
    # Caption batch
    images = [Image.open(f"photo{i}.jpg") for i in range(5)]
    captions = vlm.caption_images(images)
    for i, cap in enumerate(captions):
        print(f"Image {i}: {cap}")
```

### Visual Question Answering

```python
from services.vlm_service_local import build_vlm_from_config
from services.llm_service_local import LocalLlamaClient
from PIL import Image

# Setup
vlm = build_vlm_from_config(config)
llm = LocalLlamaClient(model_path="models/llama-3-8b.gguf")

# Ask question about image
image = Image.open("beach.jpg")
answer = vlm.answer_question(
    image=image,
    question="What is the weather like?",
    llm_client=llm
)
print(f"Answer: {answer}")

vlm.close()
```

### Async Usage (FastAPI)

```python
from fastapi import FastAPI, UploadFile
from services.vlm_service_local import build_vlm_from_config
from PIL import Image
import io

app = FastAPI()
vlm = build_vlm_from_config(config)

@app.post("/caption")
async def caption_image(file: UploadFile):
    """Caption uploaded image (non-blocking)."""
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))
    
    # Async captioning (doesn't block event loop)
    captions = await vlm.caption_images_async([image])
    
    return {"caption": captions[0]}

@app.on_event("shutdown")
async def shutdown():
    vlm.close()
```

### Flexible Input Formats

```python
# PIL Image
img = Image.open("photo.jpg")
vlm.caption_images([img])

# File path
vlm.caption_images(["photo.jpg", "photo2.jpg"])

# Numpy array
import numpy as np
arr = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
vlm.caption_images([arr])

# Mixed
vlm.caption_images([img, "photo2.jpg", arr])
```

---

## API Reference

### `VLMService`

Main service class for VLM operations.

#### `__init__(cfg: VLMConfig)`
Initialize VLM service with configuration.

**Raises:**
- `RuntimeError`: If torch/transformers/pillow not installed
- `FileNotFoundError`: If model path doesn't exist

#### `caption_images(images: list[Any]) -> list[str]`
Generate captions for images (synchronous).

**Parameters:**
- `images`: List of PIL.Image, file paths (str), or numpy arrays

**Returns:**
- List of caption strings

**Raises:**
- `TypeError`: Unsupported image format
- `FileNotFoundError`: Image path doesn't exist
- `RuntimeError`: Image preparation failed

#### `caption_images_async(images: list[Any]) -> list[str]`
Async version of `caption_images()`.

**Parameters:**
- Same as `caption_images()`

**Returns:**
- Awaitable that resolves to list of captions

#### `answer_question(image: Any, question: str, llm_client: LLMClientProtocol | None) -> str`
Answer question about image using caption + LLM.

**Parameters:**
- `image`: PIL.Image, file path, or numpy array
- `question`: User's question string
- `llm_client`: Optional LLM client with `chat(prompt, system)` method

**Returns:**
- Answer string

**Note:** If `llm_client` is None, returns caption with fallback message.

#### `answer_question_async(image, question, llm_client) -> str`
Async version of `answer_question()`.

#### `close()`
Free CUDA memory and cleanup resources.

**Note:** Called automatically when using context manager.

#### `__enter__() / __exit__(...)`
Context manager support for automatic cleanup.

```python
with VLMService(cfg) as vlm:
    # Use vlm
    pass
# Automatically calls vlm.close()
```

### `build_vlm_from_config(conf: dict) -> VLMService`
Factory function to create VLM service from config dict.

**Parameters:**
- `conf`: Dictionary with "vlm" section (from astra.yaml)

**Returns:**
- Initialized `VLMService` instance

**Raises:**
- `ValueError`: If `vlm.model_name_or_path` missing in config

---

## Performance Tuning

### GPU Optimization

```yaml
vlm:
  device: "cuda"
  dtype: "fp16"          # 2x faster than fp32
  batch_size: 16         # Maximize GPU utilization
  warmup_runs: 2         # Stabilize CUDA kernels
```

**Expected Performance (BLIP-base, RTX 3090):**
- Single image: ~50ms
- Batch of 16: ~400ms (25ms/image)
- Throughput: ~40 images/second

### CPU Optimization

```yaml
vlm:
  device: "cpu"
  dtype: "fp32"          # fp16 not supported on CPU
  batch_size: 1          # CPU batching less beneficial
  warmup_runs: 0         # Skip warmup
```

**Expected Performance (BLIP-base, 12-core CPU):**
- Single image: ~2s
- Throughput: ~0.5 images/second

### Memory Management

```python
# Process large image collection
import gc

batch_size = 100
for i in range(0, len(all_images), batch_size):
    batch = all_images[i:i + batch_size]
    captions = vlm.caption_images(batch)
    process_captions(captions)
    
    # Free memory every N batches
    if i % 500 == 0:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
```

### Latency vs Throughput

**Low Latency (real-time inference):**
```yaml
batch_size: 1
max_new_tokens: 32
warmup_runs: 3
```

**High Throughput (batch processing):**
```yaml
batch_size: 32
max_new_tokens: 64
warmup_runs: 1
```

---

## Troubleshooting

### Issue: "RuntimeError: VLM dependencies missing"

**Cause:** torch, transformers, or pillow not installed.

**Solution:**
```bash
pip install torch torchvision transformers pillow
```

### Issue: "FileNotFoundError: VLM model path not found"

**Cause:** Model directory doesn't exist or wrong path in config.

**Solution:**
```bash
# Verify model path
ls -la models/vlm/blip-base

# Re-download if missing
python download_blip.py

# Check astra.yaml path
grep model_name_or_path config/astra.yaml
```

### Issue: CUDA Out of Memory

**Cause:** Batch size too large for GPU VRAM.

**Solution:**
```yaml
# Reduce batch size
vlm:
  batch_size: 2  # Or 1 for very limited VRAM

# Or use CPU
vlm:
  device: "cpu"
```

### Issue: Slow CPU Inference

**Cause:** CPU inference is inherently slower.

**Solutions:**
1. Use smaller batch size (CPU batching less efficient)
2. Use BLIP-base instead of BLIP-large
3. Reduce `max_new_tokens` to 32-48
4. Consider GPU upgrade if frequent usage

### Issue: Poor Caption Quality

**Cause:** Model limitations or low-quality input images.

**Solutions:**
1. Upgrade to BLIP-large:
   ```yaml
   model_name_or_path: "models/vlm/blip-large"
   ```

2. Increase caption length:
   ```yaml
   max_new_tokens: 96
   ```

3. Ensure input images are:
   - Well-lit (not too dark)
   - In-focus (not blurry)
   - Sufficient resolution (≥224px)

### Issue: VQA Returns Caption Only

**Cause:** LLM client not provided or incompatible.

**Solution:**
```python
# Ensure LLM client has chat() method
llm = LocalLlamaClient(model_path="models/llama.gguf")

# Verify client works
resp = llm.chat("Test prompt", system="You are helpful")
assert "text" in resp

# Pass to VLM
answer = vlm.answer_question(img, question, llm_client=llm)
```

---

## Production Checklist

### Pre-Deployment

- [ ] VLM dependencies installed (`pip install torch transformers pillow`)
- [ ] Model weights downloaded and verified (hash check)
- [ ] Model path in `astra.yaml` is correct and accessible
- [ ] CUDA available (if using GPU): `torch.cuda.is_available() == True`
- [ ] Smoke tests pass: `python scripts/test_vlm_smoke.py`
- [ ] Unit tests pass: `pytest tests/week3/test_vlm_service.py`
- [ ] Validation script passes: `.\scripts\validate_hardening.ps1 -IncludeVLM`

### Configuration Tuning

- [ ] `batch_size` tuned for target hardware (GPU: 8-16, CPU: 1-2)
- [ ] `dtype` set to "fp16" for GPU, "fp32" for CPU
- [ ] `device` set explicitly or null (auto-detect tested)
- [ ] `max_new_tokens` balanced for quality vs speed (32-96)
- [ ] `warmup_runs` configured (1-3 for production)

### Monitoring

- [ ] Log VLM initialization (device, model, dtype)
- [ ] Track inference latency (p50, p95, p99)
- [ ] Monitor VRAM usage (if GPU)
- [ ] Alert on repeated inference failures
- [ ] Measure caption quality (manual spot checks)

### Operational

- [ ] Model files backed up (restore procedure documented)
- [ ] Model path is read-only (prevent accidental modification)
- [ ] Graceful degradation plan (fallback if VLM unavailable)
- [ ] Resource cleanup tested (memory leaks checked)
- [ ] Async endpoints tested under load (no event loop blocking)

### Documentation

- [ ] VLM setup instructions shared with team
- [ ] Model download procedure documented
- [ ] Configuration tuning guide available
- [ ] Troubleshooting runbook created
- [ ] API usage examples provided

---

## Additional Resources

- **HuggingFace BLIP:** https://huggingface.co/Salesforce/blip-image-captioning-base
- **Transformers Docs:** https://huggingface.co/docs/transformers/
- **PyTorch CUDA Setup:** https://pytorch.org/get-started/locally/
- **ASTRA VLM Tests:** `tests/week3/test_vlm_service.py`
- **VLM Smoke Tests:** `scripts/test_vlm_smoke.py`

---

**Questions or Issues?**  
See `TROUBLESHOOTING.md` or check existing unit tests for usage examples.
