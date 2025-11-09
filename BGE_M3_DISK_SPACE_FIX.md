# BGE-M3 Deployment - Disk Space Issue Resolution

## Problem

The `reembed_bge_m3.py` script failed with:
```
OSError: [Errno 28] No space left on device
```

### Root Cause

- **C: drive is completely full** (0 bytes free)
- Hugging Face Hub downloads models to `C:\Users\TOP\.cache\huggingface` by default
- BGE-M3 model is ~2.3GB and couldn't be downloaded
- The error message was misleading - it looked like a Hugging Face download info message, but the actual failure was a Python `OSError` from the re-embedding script

### Disk Status
- **C: drive**: 209GB used, **0 bytes free** ❌
- **X: drive**: 420GB used, **79GB free** ✅

## Solution Applied

### 1. Redirected Hugging Face Cache to X: Drive

Added to `.env`:
```bash
# Hugging Face Cache - Redirect to X: drive (C: is full)
HF_HOME=X:/PROJECT_ASTRA/data/hf_cache
TRANSFORMERS_CACHE=X:/PROJECT_ASTRA/data/hf_cache/transformers
HUGGINGFACE_HUB_CACHE=X:/PROJECT_ASTRA/data/hf_cache/hub
```

### 2. Updated `deploy_bge_m3.ps1`

Changed cache directories from `.hf_cache` to `data/hf_cache` with proper structure:
```powershell
$env:HF_HOME = "X:\PROJECT_ASTRA\data\hf_cache"
$env:TRANSFORMERS_CACHE = "X:\PROJECT_ASTRA\data\hf_cache\transformers"
$env:HUGGINGFACE_HUB_CACHE = "X:\PROJECT_ASTRA\data\hf_cache\hub"
$env:SENTENCE_TRANSFORMERS_HOME = "X:\PROJECT_ASTRA\data\hf_cache\sentence_transformers"
$env:TORCH_HOME = "X:\PROJECT_ASTRA\data\torch_cache"
```

### 3. Enhanced `reembed_bge_m3.py` Script

**Fixed ChromaDB pagination** (version 0.5.x compatibility):
```python
# Before (failed silently)
batch = src.get(limit=page, offset=cursor)

# After (explicit include)
batch = src.get(limit=page, offset=cursor, include=["ids"])
```

**Added proper error handling**:
```python
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        print("\nCommon issues:")
        print("  1. Disk space full (check C: and X: drives)")
        print("  2. ChromaDB collection not found")
        print("  3. Missing dependencies")
        print("  4. Model download failed")
        sys.exit(1)
```

**Added imports**:
```python
import sys
import traceback
```

## How to Run (Fixed)

### Option 1: Use the Fixed Deployment Script (Recommended)

```powershell
# This now sets all cache dirs correctly
.\deploy_bge_m3.ps1
```

### Option 2: Manual Execution

```powershell
# Set env vars in current session
$env:HF_HOME = "X:\PROJECT_ASTRA\data\hf_cache"
$env:TRANSFORMERS_CACHE = "X:\PROJECT_ASTRA\data\hf_cache\transformers"
$env:HUGGINGFACE_HUB_CACHE = "X:\PROJECT_ASTRA\data\hf_cache\hub"

# Run reembed script
X:\PROJECT_ASTRA\.venv\Scripts\python.exe scripts\reembed_bge_m3.py
```

### Option 3: Debug Mode (If Still Failing)

```powershell
$env:CHROMADB_LOG_LEVEL = "DEBUG"
$env:HF_HOME = "X:\PROJECT_ASTRA\data\hf_cache"
X:\PROJECT_ASTRA\.venv\Scripts\python.exe -X faulthandler scripts\reembed_bge_m3.py
```

## Verification Commands

```powershell
# Check dependencies
X:\PROJECT_ASTRA\.venv\Scripts\python.exe -c "import chromadb, torch, sentence_transformers; print('✓ All deps OK')"

# Check disk space
Get-PSDrive C, X | Format-Table Name, Used, Free

# Verify env vars
Write-Host "HF_HOME: $env:HF_HOME"
Write-Host "TRANSFORMERS_CACHE: $env:TRANSFORMERS_CACHE"

# Check ChromaDB collections
X:\PROJECT_ASTRA\.venv\Scripts\python.exe -c "import chromadb; c=chromadb.PersistentClient('data/chromadb'); print([col.name for col in c.list_collections()])"
```

## Long-Term Recommendation

**Free up space on C: drive** to avoid similar issues:
1. Run Disk Cleanup (`cleanmgr.exe`)
2. Clear Windows Update cache (`C:\Windows\SoftwareDistribution`)
3. Delete temp files (`C:\Users\TOP\AppData\Local\Temp`)
4. Move large files/apps to X: drive
5. Use WinDirStat to identify space hogs

## Status

✅ **Fixed** - Environment variables configured to use X: drive
✅ **Script enhanced** - Better error handling and ChromaDB compatibility
✅ **Ready to rerun** - Execute `.\deploy_bge_m3.ps1` or manual steps above

---

**Next Steps**:
1. Run `.\deploy_bge_m3.ps1` to complete BGE-M3 deployment
2. The script will now download model to X: drive (79GB available)
3. Re-embedding will process all items in `astra_memory` → `astra_memories_m3`
4. Update config to use new collection after verification
