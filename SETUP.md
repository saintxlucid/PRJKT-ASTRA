# Project Setup Guide

## Introduction
This guide covers setting up and configuring the ASTRA core components including model surgery, schema validation, and RoPE tuning capabilities.

## Installation
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration
- Copy `config.example.yaml` to `config/config.yaml`
- Update settings as needed
- Configure validation gates in `config/gates.yaml`

## Usage

### Model Surgery
```python
from evolution.gguf.surgeon import ModelSurgeon

surgeon = ModelSurgeon()
result = surgeon.merge_loras("base.gguf", adapters)
```

### Schema Validation
```python 
from evolution.gguf.grammar import SchemaValidator

validator = SchemaValidator("schema.json")
valid, errors = validator.validate("model.gguf")
```

### RoPE Tuning
```python
from evolution.gguf.rope import RoPEConfig

config = RoPEConfig(freq_base=10000)
result = surgeon.tune_rope("model.gguf", config)
```

## Development
- Run tests: `pytest tests/`
- Generate docs: `make docs`
- Format code: `black .`

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Documentation
Full documentation is in `docs/` directory.