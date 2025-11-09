# Extraction Tools

This directory contains tools for extracting components from GGUF files.

## Tools Included

1. **tensor_extractor.py** - Extract tensor data from GGUF files
2. **vocab_extractor.py** - Extract vocabulary and tokenizer data
3. **model_decomposer.py** - Decompose model into component parts
4. **weight_exporter.py** - Export weights in various formats
5. **architecture_exporter.py** - Export model architecture specifications

## Usage

### tensor_extractor.py

```bash
python tensor_extractor.py <path_to_gguf_file> [--tensor <name>] [--output-dir <dir>] [--format numpy|bin]
```

This tool extracts tensor data from GGUF files:
- Extract specific tensors by name
- Extract all tensors
- Save in NumPy or binary format
- Preserve tensor metadata

### vocab_extractor.py

```bash
python vocab_extractor.py <path_to_gguf_file> [--output-file <file>] [--format json|txt]
```

This tool extracts vocabulary and tokenizer information:
- Token list
- Token scores
- Token types
- Special token IDs
- Merge rules (for BPE)

### model_decomposer.py

```bash
python model_decomposer.py <path_to_gguf_file> [--output-dir <dir>] [--separate-components]
```

This tool decomposes a model into its components:
- Separate attention layers
- Separate feed-forward layers
- Separate embedding layers
- Component metadata preservation

### weight_exporter.py

```bash
python weight_exporter.py <path_to_gguf_file> [--format pytorch|numpy|safetensors] [--output-dir <dir>]
```

This tool exports weights in various formats:
- PyTorch format
- NumPy arrays
- Safetensors format
- Metadata preservation

### architecture_exporter.py

```bash
python architecture_exporter.py <path_to_gguf_file> [--output-file <file>] [--format json|yaml]
```

This tool exports model architecture specifications:
- Layer configurations
- Dimension specifications
- Model hyperparameters
- Architecture-specific details