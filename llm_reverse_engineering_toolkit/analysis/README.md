# Analysis Tools

This directory contains tools for analyzing GGUF files in detail.

## Tools Included

1. **gguf_analyzer.py** - Comprehensive GGUF file analyzer
2. **architecture_inspector.py** - Model architecture inspection tool
3. **metadata_extractor.py** - Detailed metadata extraction utility
4. **tensor_analyzer.py** - Tensor structure and statistics analyzer
5. **quantization_inspector.py** - Quantization analysis tool

## Usage

### gguf_analyzer.py

```bash
python gguf_analyzer.py <path_to_gguf_file> [--verbose] [--output-format json|text]
```

This tool provides a comprehensive analysis of a GGUF file, including:
- File header information
- Metadata key-value pairs
- Tensor information (names, shapes, types)
- Quantization details
- Model architecture information

### architecture_inspector.py

```bash
python architecture_inspector.py <path_to_gguf_file> [--detailed]
```

This tool extracts and displays detailed information about the model architecture:
- Number of layers
- Attention heads
- Hidden dimensions
- Vocabulary size
- Special tokens
- Model-specific parameters

### metadata_extractor.py

```bash
python metadata_extractor.py <path_to_gguf_file> [--key-filter <pattern>] [--export <file>]
```

This tool extracts metadata from GGUF files:
- All key-value pairs
- Filter by key patterns
- Export to JSON or CSV format
- Detailed type information

### tensor_analyzer.py

```bash
python tensor_analyzer.py <path_to_gguf_file> [--tensor <name>] [--stats-only]
```

This tool analyzes tensor data:
- Shape and size information
- Statistical summaries (mean, std, min, max)
- Data type information
- Specific tensor inspection

### quantization_inspector.py

```bash
python quantization_inspector.py <path_to_gguf_file>
```

This tool analyzes quantization:
- Quantization types used
- Block sizes
- Quantization parameters
- Memory footprint analysis