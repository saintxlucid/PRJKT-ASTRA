# Parsing & Vector Sliding

This guide covers ASTRA's layout-aware PDF parsing and vector sliding techniques.

## PDF Parsing

### Layout-Aware Chunking

ASTRA uses intelligent PDF parsing that preserves:
- Page numbers
- Bounding boxes
- Heading hierarchy
- Visual layout

### Chunk Parameters

- Token length: 512-800 tokens
- Stride overlap: 25-30%
- Preserved metadata:
  - Page number
  - Bounding box coordinates
  - Section headings
  - Layout context

### Usage

```python
from astra.parse.pdf import parse_pdf

chunks = parse_pdf(
    path="document.pdf",
    chunk_size=700,
    stride_ratio=0.25
)
```

## Vector Sliding

### Overview

Vector sliding merges semantically similar adjacent chunks during retrieval to:
- Reduce information fragmentation
- Preserve context
- Improve answer coherence

### Algorithm

1. Initial Retrieval:
   - Get top-k chunks
   - Include adjacent chunks

2. Similarity Check:
   - Calculate vector similarity
   - Identify merge candidates

3. Chunk Merging:
   - Merge similar adjacent chunks
   - Preserve metadata
   - Update relevance scores

### Configuration

```yaml
vector_sliding:
  enabled: true
  similarity_threshold: 0.85
  max_merge_size: 1500
  context_window: 2
```

## Integration Points

### Parse Module

```python
# Chunk extraction
chunks = parse_pdf(doc_path)

# Access metadata
for chunk in chunks:
    print(f"Page: {chunk.page}")
    print(f"Bbox: {chunk.bbox}")
    print(f"Heading: {chunk.heading}")
```

### Retrieval Flow

```python
# During retrieval
results = retriever.retrieve(
    query="example query",
    k=5,
    slide_vectors=True
)
```

## Tuning Guidelines

### Chunk Parameters

1. Size (512-800 tokens):
   - Smaller: More precise, may fragment
   - Larger: More context, may dilute

2. Stride (25-30%):
   - Lower: More chunks, better coverage
   - Higher: Fewer chunks, may miss content

### Vector Sliding

1. Similarity Threshold:
   - Lower: More merges, potential noise
   - Higher: Fewer merges, may miss connections

2. Max Merge Size:
   - Balance readability
   - Consider model context limits
   - Monitor performance impact

## Performance Impact

### Resource Usage

- Memory: O(n) for n chunks
- CPU: Linear with chunk count
- GPU: Batch embeddings for efficiency

### Optimization

1. Caching:
   - Cache parsed chunks
   - Store vector similarities
   - Reuse merge decisions

2. Batch Processing:
   - Group parsing operations
   - Parallel embeddings
   - Efficient vector operations

## Monitoring

### Key Metrics

1. Parsing:
   - Chunks per document
   - Token distribution
   - Metadata coverage

2. Vector Sliding:
   - Merge frequency
   - Similarity distributions
   - Performance impact

### Telemetry

Monitor in `data/logs/telemetry.jsonl`:
- Parsing duration
- Chunk statistics
- Merge operations
- Vector calculations