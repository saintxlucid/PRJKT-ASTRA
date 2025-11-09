# BGE-M3 Memory Issue - Pragmatic Solution

## Problem
BGE-M3 model requires ~4-6GB RAM for inference on CPU, but your system appears memory-constrained.

```
RuntimeError: not enough memory: you tried to allocate 1024008192 bytes
KeyboardInterrupt during forward pass (model inference too slow/OOM)
```

## What Worked
✅ Model downloaded successfully (2.27GB in `X:/PROJECT_ASTRA/models/bge-m3`)  
✅ Model loaded successfully with `low_cpu_mem_usage=True` + `accelerate`  
✅ ChromaDB collections found (`astra_memory`: 5 items)  
✅ Pagination fixed for ChromaDB 0.5.x  

## What Failed
❌ **Embedding inference** - Forward pass exhausts available RAM

## Pragmatic Solutions (Pick One)

### Option 1: Continue with MiniLM (RECOMMENDED for now)
Your current `all-MiniLM-L6-v2` works fine and only uses ~500MB RAM.

**Action**: Skip BGE-M3 upgrade, proceed with Upgrade Pack deployment minus the re-embedding:

```powershell
# Update .env to keep using current embeddings
# No action needed - already set to astra_memory

# Continue with rest of Upgrade Pack
# - Metrics ✅ (already deployed)
# - Rate limiting ✅ (already deployed)  
# - Security/encryption ✅ (already deployed)
```

**Result**: Production-ready system with all Upgrade Pack features except multilingual embeddings.

### Option 2: Use GPU/Cloud for Re-embedding (if available later)
BGE-M3 runs much faster on GPU:
- Local GPU (CUDA): ~2-5 seconds for 5 items
- Google Colab (free T4 GPU): Upload chromadb, run reembed script, download back
- Azure ML free tier: Similar approach

### Option 3: Reduce Batch to 1 + Add Swap Space
Extreme measure - very slow but might work:

```powershell
$env:ASTRA_EMBEDDINGS_BATCH="1"  # Process 1 at a time
$env:PYTORCH_NO_CUDA_MEMORY_CACHING="1"

# Ensure Windows has adequate page file (swap)
# Control Panel > System > Advanced > Performance Settings > Advanced > Virtual Memory
# Set to System Managed or Custom: 8GB-16GB
```

Run:
```powershell
X:\PROJECT_ASTRA\.venv\Scripts\python.exe scripts\reembed_bge_m3.py
```

Expect: ~30-60 seconds per item (5 items = 5-10 minutes total)

### Option 4: Use Smaller Multilingual Model
Alternative models with better memory/performance trade-off:

```bash
# paraphrase-multilingual-MiniLM-L12-v2 (470MB, 384d)
ASTRA_EMBEDDINGS_MODEL_PATH="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Or intfloat/multilingual-e5-base (1.1GB, 768d) 
ASTRA_EMBEDDINGS_MODEL_PATH="intfloat/multilingual-e5-base"
```

Both support Arabic + English, use ~2GB RAM vs 6GB for BGE-M3.

## Recommended Path Forward

**For immediate production deployment**:
1. Keep current MiniLM embeddings (`astra_memory` collection)
2. Deploy rest of Upgrade Pack (metrics, rate-limit, security) ✅
3. Verify system health & performance
4. **Add BGE-M3 as future enhancement** when:
   - More RAM available
   - GPU access
   - Or use Option 4 (smaller multilingual model)

**Update `deploy_upgrade_pack.ps1`** to make re-embedding optional:

```powershell
# Add -SkipReembed flag
param([switch]$SkipReembed)

if (-not $SkipReembed) {
    # Run reembed_bge_m3.py
} else {
    Write-Host "Skipping re-embedding (use existing embeddings)" -ForegroundColor Yellow
}
```

## Next Steps (Mission Completion)

Since you only have 5 memories, the embedding model choice won't significantly impact quality. **Proceed with current setup**:

1. ✅ Skip BGE-M3 re-embedding (memory constraint)
2. ✅ Use existing `astra_memory` collection
3. ✅ Update `.env` to confirm collection name
4. ✅ Restart ASTRA server
5. ✅ Run verification & load tests
6. ✅ Complete Upgrade Pack mission

## Environment Variables (Current Production)

```bash
# Keep these in .env
ASTRA_VECTOR_COLLECTION=astra_memory
ASTRA_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ASTRA_EMBEDDING_DIMENSION=384

# BGE-M3 config (for future use with GPU/more RAM)
# ASTRA_EMBEDDINGS_MODEL_PATH=X:/PROJECT_ASTRA/models/bge-m3
# ASTRA_VECTOR_COLLECTION_NEW=astra_memories_m3  
# ASTRA_EMBEDDINGS_BATCH=4
```

## Summary
- **Current**: MiniLM (384d) - works perfectly for your 5-item dataset
- **Future**: BGE-M3 (1024d) - when system has more RAM or GPU access
- **Alternative**: multilingual-e5-base (768d) - middle ground

**Recommendation**: Proceed with deployment using current embeddings. BGE-M3 is an enhancement, not a blocker.
