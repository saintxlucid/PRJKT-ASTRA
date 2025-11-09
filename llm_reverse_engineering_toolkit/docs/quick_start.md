# Quick Start Guide

Get up and running with the LLM GGUF Reverse Engineering Toolkit quickly.

## Prerequisites

1. Python 3.8+
2. pip package manager
3. GGUF model file for analysis

## Installation

```bash
# Clone or download the toolkit
# Navigate to the toolkit directory
cd llm_reverse_engineering_toolkit

# Install dependencies
pip install -r requirements.txt
```

## Quick Analysis

```bash
# Analyze a GGUF model
python analysis/gguf_analyzer.py path/to/your/model.gguf

# Get detailed architecture information
python analysis/architecture_inspector.py path/to/your/model.gguf --detailed
```

## Quick Extraction

```bash
# Extract vocabulary
python extraction/vocab_extractor.py path/to/your/model.gguf --output-file vocab.json

# Extract a specific tensor
python extraction/tensor_extractor.py path/to/your/model.gguf --tensor token_embd.weight
```

## Quick Modification

```bash
# Modify a metadata value
python modification/metadata_editor.py path/to/your/model.gguf --set tokenizer.ggml.bos_token_id 2

# Perturb weights slightly
python modification/weight_perturber.py path/to/your/model.gguf --perturbation gaussian --scale 0.001
```

## Quick Visualization

```bash
# Visualize model architecture
python visualization/architecture_visualizer.py path/to/your/model.gguf --output architecture.png
```

## Next Steps

1. Read the complete guide in `docs/complete_guide.md`
2. Explore individual module READMEs for detailed usage
3. Experiment with the tools on sample models
4. Refer to the ethical considerations before proceeding with advanced modifications