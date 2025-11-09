# Visualization Tools

This directory contains tools for visualizing GGUF model internals.

## Tools Included

1. **architecture_visualizer.py** - Visualize model architecture
2. **weight_visualizer.py** - Visualize weight distributions
3. **attention_visualizer.py** - Visualize attention patterns
4. **tensor_flow_visualizer.py** - Visualize tensor data flow
5. **vocab_heatmap.py** - Visualize vocabulary relationships

## Usage

### architecture_visualizer.py

```bash
python architecture_visualizer.py <path_to_gguf_file> [--output <file>] [--format png|svg|pdf]
```

This tool visualizes model architecture:
- Layer connectivity diagrams
- Parameter count visualization
- Model structure charts
- Component relationship graphs

### weight_visualizer.py

```bash
python weight_visualizer.py <path_to_gguf_file> [--tensor <name>] [--output <file>]
```

This tool visualizes weight distributions:
- Histograms of weight values
- Statistical distribution charts
- Layer-wise comparisons
- Quantization effect visualization

### attention_visualizer.py

```bash
python attention_visualizer.py <path_to_gguf_file> [--layer <num>] [--output <file>]
```

This tool visualizes attention patterns:
- Attention head matrices
- Sequence attention patterns
- Head similarity analysis
- Attention flow diagrams

### tensor_flow_visualizer.py

```bash
python tensor_flow_visualizer.py <path_to_gguf_file> [--output <file>]
```

This tool visualizes tensor data flow:
- Data flow through layers
- Tensor size changes
- Computational graph visualization
- Memory usage patterns

### vocab_heatmap.py

```bash
python vocab_heatmap.py <path_to_gguf_file> [--output <file>]
```

This tool visualizes vocabulary relationships:
- Token similarity heatmaps
- Vocabulary clustering
- Special token relationships
- Embedding space visualization