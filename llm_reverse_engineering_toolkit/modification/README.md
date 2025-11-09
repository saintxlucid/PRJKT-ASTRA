# Modification Tools

This directory contains tools for modifying GGUF files.

## Tools Included

1. **metadata_editor.py** - Edit GGUF metadata
2. **tensor_modifier.py** - Modify tensor values
3. **weight_perturber.py** - Perturb weights for experimentation
4. **architecture_modifier.py** - Modify model architecture parameters
5. **quantization_changer.py** - Change quantization schemes

## Usage

### metadata_editor.py

```bash
python metadata_editor.py <path_to_gguf_file> [--set <key> <value>] [--remove <key>] [--output <file>]
```

This tool edits GGUF metadata:
- Set new key-value pairs
- Modify existing values
- Remove metadata entries
- Batch operations

### tensor_modifier.py

```bash
python tensor_modifier.py <path_to_gguf_file> [--tensor <name>] [--operation <op>] [--output <file>]
```

This tool modifies tensor values:
- Mathematical operations on tensors
- Tensor replacement
- Tensor initialization
- Custom transformation functions

### weight_perturber.py

```bash
python weight_perturber.py <path_to_gguf_file> [--perturbation <type>] [--scale <value>] [--output <file>]
```

This tool perturbs weights for experimentation:
- Random perturbations
- Systematic modifications
- Scaling operations
- Noise injection

### architecture_modifier.py

```bash
python architecture_modifier.py <path_to_gguf_file> [--param <name> <value>] [--output <file>]
```

This tool modifies model architecture parameters:
- Change hidden dimensions
- Modify attention heads
- Adjust layer counts
- Update vocabulary size

### quantization_changer.py

```bash
python quantization_changer.py <path_to_gguf_file> [--target-quant <type>] [--output <file>]
```

This tool changes quantization schemes:
- Convert between quantization types
- Adjust quantization parameters
- Re-quantize tensors
- Optimize for target hardware