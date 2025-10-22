# Getting Started

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd astra-core
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Basic Usage

### 1. LoRA Merging

```python
from evolution.gguf.surgeon import ModelSurgeon
from evolution.gguf.manifest import AdapterManifest

# Initialize surgeon
surgeon = ModelSurgeon()

# Load manifest
manifest = AdapterManifest("adapters/manifest.json")

# Merge adapters
result = surgeon.merge_loras(
    "base.gguf",
    manifest.get_merge_order().values()
)
```

### 2. RoPE Tuning

```python
from evolution.gguf.rope import RoPEConfig

# Configure RoPE parameters
config = RoPEConfig(
    freq_base=10000,
    freq_scale=1.0,
    dimensions=128
)

# Apply tuning
result = surgeon.tune_rope(
    "model.gguf",
    config,
    "model.rope.gguf"
)
```

### 3. Schema Enforcement

```python
from evolution.gguf.grammar import SchemaValidator

# Initialize validator
validator = SchemaValidator("schema.json")

# Validate model
valid, errors = validator.validate("model.gguf")

if not valid:
    for error in errors:
        print(f"Validation error: {error}")
```

## Examples

Check out the Jupyter notebooks in the `examples/` directory:
- `01_lora_merging.ipynb`
- `02_rope_tuning.ipynb`
- `03_schema_enforcement.ipynb`

## Configuration

Edit settings in `config/`:
- `config.yaml`: General configuration
- `gates.yaml`: Validation gate thresholds
- `schemas/`: Model schemas

## Next Steps

- Read the [Architecture Overview](../architecture.md)
- Explore the [API Reference](../api/README.md)
- Check out [Advanced Usage](advanced-usage.md)