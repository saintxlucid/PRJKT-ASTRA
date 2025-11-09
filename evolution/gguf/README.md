# ASTRA GGUF Model Surgery

Tools for merging LoRA adapters, tuning RoPE parameters, and enforcing structured outputs in GGUF models.

## Features

- LoRA adapter merging with provenance tracking
- RoPE parameter tuning with drift monitoring
- Grammar-constrained output validation
- Comprehensive validation gates
- HTTP API and CLI

## Quick Start

### LoRA Merging

Create an adapter manifest (`adapters/manifest.json`):

```json
{
  "planner": {
    "path": "adapters/planner.gguf",
    "alpha": 0.8
  },
  "tooluse": {
    "path": "adapters/tooluse.gguf",
    "alpha": 0.7
  },
  "safety": {
    "path": "adapters/safety.gguf",
    "alpha": 0.6
  }
}
```

Merge adapters:

```bash
gguf-merge --base model.gguf --manifest adapters/manifest.json --out model.evo.gguf --quant Q5_K_M
```

### Validation

Run validation:

```bash
gguf-validate --base model.gguf --out model.evo.gguf --dataset eval/*
```

Gates:
- Tool accuracy ≥ 90%
- PPL delta ≤ +10%
- Drift ≤ 7%
- Safety ≥ 95%

### HTTP API

Start Chamber API:

```bash
uvicorn evolution.gguf.chamber:app
```

Example patch request:

```http
POST /gguf/patch
Content-Type: application/json

{
  "base_path": "model.gguf",
  "ops": {
    "lora_paths": ["adapter.gguf"],
    "rope_scale": 1.15,
    "quantize": "Q5_K_M"
  }
}
```

## Development

### Setup

```bash
# Install
pip install -e .

# Test
pytest tests/evolution/test_*.py -v
```

### Project Structure

```
evolution/gguf/
├── surgeon.py   # Core operations
├── chamber.py   # HTTP API
├── manifest.py  # Adapter manifest
├── rope.py      # RoPE tuning
├── grammar.py   # Validation
└── cli.py      # CLI
```

### Configuration

```python
# RoPE defaults
ROPE_SCALE = 1.15
ROPE_BASE = 1e6

# Validation gates
TOOL_ACC_MIN = 0.90
PPL_DELTA_MAX = 0.10
DRIFT_MAX = 0.07
SAFETY_MIN = 0.95
```

### Contributing

1. Fork repository
2. Create feature branch
3. Add tests
4. Update docs
5. Submit PR

Requirements:
- Tests pass
- Coverage maintained
- Docs updated
- Gates enforced

## License

MIT License