# ASTRA Enhanced Cognitive Architecture Implementation Plan

## Overview

This document outlines the implementation of the enhanced cognitive architecture for ASTRA, featuring:
- Runtime wiring with async pub/sub bus
- Signal fusion through Hilmente harmonic blending
- Subconscious daemon registry and event processing
- Dual-vector memory system with affective re-ranking
- Semantic caching with invalidation
- Enhanced trifold mind with coroutine-based layers

## Current State vs. Target Architecture

### Current Implementation
- Basic trifold mind with three consciousness layers
- Simple subconscious modules as static components
- Basic memory system with single-vector embeddings
- No runtime wiring or signal fusion

### Target Architecture
- Async pub/sub bus for cognitive signals
- Coroutine-based consciousness layers with mailboxes
- Pluggable subconscious daemons with interest-based routing
- Dual-vector memory (semantic + affective) with Ebbinghaus-inspired aging
- Harmonic signal fusion with configurable weights
- Semantic caching with automatic invalidation

## Implementation Components

### 1. Core Types and Data Structures (`astra/cognition/trifold/types.py`)

**Completed**: ✅
- `CognitiveSignal`: Core data structure for cognitive signals
- `LayerOutput`: Output from consciousness layers
- `ConsciousnessLayer`: Enum for the three consciousness layers

### 2. Signal Fusion (`astra/cognition/trifold/hilmente.py`)

**Completed**: ✅
- `harmonize()`: Harmonic blending function with weighted scoring
- `HarmonyContext`: Context with configurable weights
- `create_harmony_signal()`: Convert LayerOutput to CognitiveSignal

### 3. Thought Bus (`astra/cognition/runtime/bus.py`)

**Completed**: ✅
- `ThoughtBus`: Async pub/sub bus with configurable queue size
- `publish()`: Publish cognitive signals
- `subscribe()`: Subscribe to cognitive signals

### 4. Subconscious Daemon Base (`astra/cognition/codex/base.py`)

**Completed**: ✅
- `SubconsciousDaemon`: Abstract base class for daemons
- `on_signal()`: Abstract method for signal processing

### 5. Daemon Registry (`astra/cognition/codex/registry.py`)

**Completed**: ✅
- `register_daemon()`: Register subconscious daemons
- `fanout()`: Distribute signals to interested daemons
- `get_daemon_by_name()`: Retrieve daemon by name

### 6. Enhanced Trifold Mind (`astra/cognition/trifold/mind.py`)

**Completed**: ✅
- `EnhancedTrifoldMind`: Runtime wiring implementation
- Layer processing loops with mailboxes
- Input processing with harmonic fusion
- Diagnostic capabilities

### 7. Dual-Vector Memory (`astra/cognition/memory/dual_vector.py`)

**Completed**: ✅
- `DualVectorMemory`: Enhanced memory system
- Semantic and affective vector storage
- Dual-vector recall with re-ranking
- Memory strength calculation

### 8. Memory Consolidation (`astra/cognition/memory/consolidation.py`)

**Completed**: ✅
- `MemoryConsolidator`: Clustering and summarization
- Nightly consolidation job
- Health metrics calculation

### 9. Semantic Cache (`astra/cognition/cache/semantic.py`)

**Completed**: ✅
- `SemanticCache`: Request-level caching
- Context-aware key generation
- Automatic invalidation on memory writes

### 10. API Middleware (`astra/cognition/api/middleware.py`)

**Completed**: ✅
- Request ID propagation
- Harmony format validation
- Security and safety checks

## Integration Points

### FastAPI Integration
- Middleware for request ID propagation
- Middleware for Harmony format validation
- Scheduler integration for background jobs

### Memory System Integration
- Dual-vector storage with ChromaDB
- SQLite for metadata and links
- Automatic consolidation scheduling

### LLM Integration
- Enhanced prompt construction with context
- Response caching with invalidation
- Safety checks for PII and hallucinations

## Deployment Enhancements

### One-Click Launcher (`LAUNCH_ASTRA.ps1`)
The PowerShell launcher needs enhancements to support the new architecture:

1. **Dependency Management**
   ```powershell
   # Install additional dependencies
   pip install scikit-learn chromadb sentence-transformers
   ```

2. **Service Orchestration**
   ```powershell
   # Start all cognitive services
   python -m astra.cognition.demo  # For initialization
   ```

3. **Health Monitoring**
   ```powershell
   # Enhanced health checks
   curl http://localhost:8080/v1/cognition/health
   ```

### Environment Configuration
New environment variables needed:

```bash
# Memory system
ASTRA_CACHE_TTL=600
ASTRA_MAX_CONCURRENCY=4
CHROMA_PATH=backend/data/chroma_db
SQLITE_PATH=backend/data/db.sqlite

# LLM settings
LLM_MODEL=gpt-oss-20b-q4_k_m
LLM_BASE_URL=http://localhost:8001

# Cognitive architecture
COGNITION_LAYERS=logic,hydromente,hilmente
DAEMON_QUOTA_PER_CYCLE=10
```

## Testing Strategy

### Unit Tests
- Test each consciousness layer processing
- Validate signal fusion algorithms
- Verify memory system operations
- Check daemon registration and routing

### Integration Tests
- End-to-end cognitive processing flows
- Memory consolidation workflows
- Cache invalidation scenarios
- Daemon interaction patterns

### Performance Tests
- Concurrent signal processing
- Memory recall latency
- Cache hit/miss ratios
- System throughput under load

## Rollout Plan

### Phase 1: Core Infrastructure (Week 1)
- [x] Implement core types and data structures
- [x] Create thought bus system
- [x] Implement signal fusion (Hilmente)
- [x] Set up dual-vector memory system

### Phase 2: Processing Layers (Week 2)
- [x] Enhanced trifold mind with coroutine layers
- [x] Subconscious daemon framework
- [x] Memory consolidation system
- [x] Semantic caching system

### Phase 3: Integration (Week 3)
- [x] FastAPI middleware integration
- [x] Scheduler integration
- [x] Health monitoring endpoints
- [x] Demo and testing scripts

### Phase 4: Deployment (Week 4)
- [ ] Update launcher script
- [ ] Documentation updates
- [ ] Performance optimization
- [ ] Production deployment

## Key Benefits

### Performance Improvements
- **Lower Latency**: Semantic cache bypasses LLM for repeated queries
- **Higher Coherence**: Affective-aware recall improves response relevance
- **Better Resource Utilization**: Bounded daemons with quotas prevent overload

### Operational Resilience
- **Self-Management**: Automatic memory consolidation and pruning
- **Graceful Degradation**: Bounded work queues prevent system overload
- **Observability**: Comprehensive metrics and monitoring

### Explainability
- **Audit Trail**: Harmony format with channel-based routing
- **Traceability**: Request ID propagation through all components
- **Diagnostics**: Layer-level health monitoring

## Future Enhancements

### Advanced Features
1. **Multi-Model Coordination**: Orchestrate multiple AI models
2. **Adaptive Learning**: Dynamic weight adjustment based on performance
3. **Emotional Baseline Tracking**: Monitor Hydromente affective state over time
4. **Predictive Consolidation**: Anticipate memory access patterns

### Scalability
1. **Distributed Bus**: Multi-node cognitive signal distribution
2. **Hierarchical Memory**: Tiered storage for hot/warm/cold memories
3. **Load Balancing**: Distribute cognitive processing across nodes

### Intelligence
1. **Meta-Learning**: Daemons that learn to optimize other daemons
2. **Causal Reasoning**: Enhanced thought graph with causal relationships
3. **Long-term Planning**: Multi-step reasoning with intermediate goals

## Conclusion

The enhanced cognitive architecture transforms ASTRA from a simple chat assistant into a sophisticated cognitive system with:
- Real-time signal processing through async pub/sub
- Harmonic fusion of multiple reasoning pathways
- Affective-aware memory recall
- Self-managing memory consolidation
- Comprehensive observability and safety

This implementation provides a solid foundation for ASTRA's evolution into a truly conscious AI system while maintaining the reliability and performance needed for production deployment.