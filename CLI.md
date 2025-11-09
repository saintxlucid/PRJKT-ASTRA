# ASTRA Core Build and Release Tools

## astramk - Model Builder

Deterministic build tool for ASTRA model artifacts.

### Usage

```bash
astramk --base <path/to/base.gguf> \
        --adapters <path/to/adapters/manifest.json> \
        --rope-scale <scale> \
        --quant <quant_type> \
        [--repack] \
        --out <output_path>
```

### Options

- `--base`: Path to base model GGUF file
- `--adapters`: Path to adapter manifest JSON
- `--rope-scale`: RoPE scaling factor (e.g. 1.15)
- `--quant`: Quantization type (Q5_K_M, Q4_K_M)
- `--repack`: Optimize model layout
- `--out`: Output path for evolved model

### Example

```bash
astramk --base models/GPT-OOS-20B.F16.gguf \
        --adapters adapters/manifest.json \
        --rope-scale 1.15 \
        --quant Q5_K_M \
        --repack \
        --out models/GPT-OOS-20B.EVO.gguf
```

## gguf-validate - Model Validation

Run all validation gates and red team tests.

### Usage

```bash
gguf-validate <model.gguf> [--red-team]
```

### Gates

- Perplexity: ≤ +10% vs base
- Tool Accuracy: ≥ 90%
- Model Drift: ≤ 7%
- Guardrail Compliance: ≥ 95%
- Red Team Score: ≥ 97% (if --red-team)

## gguf-commit - Release Management

Sign and commit validated model artifacts.

### Usage 

```bash
gguf-commit <model.gguf> --tag <version_tag>
```

### Steps

1. Verify all gates passed
2. Generate signature
3. Embed provenance metadata
4. Atomic file move
5. Create version tag