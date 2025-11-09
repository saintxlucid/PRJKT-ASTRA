# Utility Tools

This directory contains utility scripts and helper functions.

## Tools Included

1. **gguf_validator.py** - Validate GGUF file integrity
2. **format_converter.py** - Convert between GGUF versions
3. **model_comparator.py** - Compare two GGUF models
4. **performance_analyzer.py** - Analyze model performance characteristics
5. **memory_calculator.py** - Calculate memory requirements

## Usage

### gguf_validator.py

```bash
python gguf_validator.py <path_to_gguf_file> [--strict] [--verbose]
```

This tool validates GGUF file integrity:
- File format validation
- Header integrity check
- Metadata consistency verification
- Tensor data validation

### format_converter.py

```bash
python format_converter.py <input_file> <output_file> [--target-version <version>]
```

This tool converts between GGUF versions:
- Version compatibility conversion
- Endianness conversion
- Metadata format updates
- Backward compatibility support

### model_comparator.py

```bash
python model_comparator.py <model1.gguf> <model2.gguf> [--detailed] [--output <file>]
```

This tool compares two GGUF models:
- Architecture differences
- Weight value comparisons
- Metadata discrepancies
- Performance characteristic analysis

### performance_analyzer.py

```bash
python performance_analyzer.py <path_to_gguf_file> [--hardware <type>] [--output <file>]
```

This tool analyzes model performance characteristics:
- Computational complexity estimation
- Memory bandwidth requirements
- Hardware compatibility analysis
- Performance bottleneck identification

### memory_calculator.py

```bash
python memory_calculator.py <path_to_gguf_file> [--context-length <tokens>] [--batch-size <size>]
```

This tool calculates memory requirements:
- Model size calculation
- Context memory estimation
- Batch processing requirements
- Hardware recommendation