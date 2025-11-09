# 🧠 Dream Grove - Quick Reference

**Phase 6 Session 1**: Memory System Foundation Complete (20%)

---

## 🎯 Access Dream Grove

1. **Open Application**: http://localhost:3333
2. **Navigate**: Click "Dream Grove" (ღ) in left sidebar under DEV section
3. **Explore**: View L0-L3 memory layers, search, compress, and run decay

---

## 🔧 API Endpoints (11 New)

### Layer Management
```bash
GET http://localhost:8000/api/memory/layers
# Returns: Array of 4 layer objects (L0-L3)
```

### CRUD
```bash
# List all memories
GET http://localhost:8000/api/memory/all?layer=0&limit=50

# Get specific memory
GET http://localhost:8000/api/memory/{id}

# Create memory
POST http://localhost:8000/api/memory
Body: {
  "id": "mem_123",
  "content": "Memory text...",
  "layer": 0,
  "tags": ["tag1", "tag2"],
  "importance": 0.85,
  "created": "2025-11-04T16:00:00",
  "last_accessed": "2025-11-04T16:00:00",
  "access_count": 0,
  "source": "conversation"
}

# Update memory
PUT http://localhost:8000/api/memory/{id}

# Delete memory
DELETE http://localhost:8000/api/memory/{id}
```

### Search
```bash
POST http://localhost:8000/api/memory/search?query=dark+mode&layer=0&limit=10
# Returns: Array of MemorySearchResult with relevance scores
```

### Temporal Decay
```bash
# Get stats
GET http://localhost:8000/api/memory/decay/stats

# Run decay
POST http://localhost:8000/api/memory/decay/run?decay_rate=0.01
```

### Compression
```bash
# Compress L0 → L1
POST http://localhost:8000/api/memory/compress?source_layer=0&target_layer=1

# Returns: {status, compressed, source_layer, target_layer}
```

---

## 📊 Memory Layers Explained

| Layer | Label | Compression | Purpose |
|-------|-------|-------------|---------|
| **L0** | Raw | 100% (1.0) | All new memories start here |
| **L1** | Summary | 50% (0.5) | Condensed versions of L0 |
| **L2** | Insight | 20% (0.2) | Patterns and connections |
| **L3** | Essence | 5% (0.05) | Core truths and permanent knowledge |

**Flow**: L0 → L1 → L2 → L3 (compression)  
**Decay**: All layers subject to temporal decay based on access patterns

---

## 🎨 UI Features

### Left Sidebar
- **Layer Cards**: Click to filter by layer (L0-L3)
- **Compression Buttons**: Manual compression triggers
- **Temporal Decay Panel**: Stats + "Run Decay Now" button
- **Show All Layers**: Reset filters

### Top Bar
- **Search**: Enter query, press Enter or click "Search"
- Filters by layer if selected

### Memory List
- **Layer Badge**: L0, L1, L2, or L3
- **Source**: conversation, note, research, etc.
- **Access Count**: Number of retrievals
- **Importance**: 0-100% score
- **Tags**: Click-friendly tag pills
- **Gradient Background**: Color-coded by layer

---

## 🧪 Test Commands

### Create Demo Memory
```powershell
$body = @{
    id = "mem_test"
    content = "Test memory for Dream Grove"
    layer = 0
    tags = @("test", "demo")
    importance = 0.75
    created = (Get-Date).ToString("o")
    last_accessed = (Get-Date).ToString("o")
    access_count = 0
    source = "manual"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/memory" `
    -Method Post -Body $body -ContentType "application/json"
```

### Search Memories
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/memory/search?query=ASTRA&limit=5" `
    -Method Post -ContentType "application/json"
```

### Run Temporal Decay
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/memory/decay/run?decay_rate=0.01" `
    -Method Post -ContentType "application/json"
```

### Compress L0 → L1
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/memory/compress?source_layer=0&target_layer=1" `
    -Method Post -ContentType "application/json"
```

---

## 🔬 Current State (20%)

### ✅ Working
- Full UI implementation
- All 11 REST endpoints
- L0-L3 layer visualization
- Temporal decay algorithm
- Memory compression (manual)
- Keyword search
- Demo memories (4 created)

### 🔄 Next (80%)
- BGE-M3 embeddings (30%)
- Real semantic search (20%)
- Memory clustering (15%)
- Advanced decay (10%)
- Nightly consolidation (5%)

---

## 📈 System Status

```powershell
# Check backend
Test-NetConnection localhost -Port 8000

# Check frontend
Test-NetConnection localhost -Port 3333

# View layer stats
Invoke-RestMethod http://localhost:8000/api/memory/layers | 
    Format-Table layer, label, memory_count, compression_ratio
```

**Expected Output**:
```
layer label          memory_count compression_ratio
----- -----          ------------ -----------------
0     L0: Raw        3            1.0
1     L1: Summary    1            0.5
2     L2: Insight    0            0.2
3     L3: Essence    0            0.05
```

---

## 🎯 Next Session Preview

### BGE-M3 Integration Steps

1. **Install Model**:
```bash
pip install sentence-transformers faiss-cpu
```

2. **Load Model** (backend):
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-m3')
```

3. **Generate Embeddings**:
```python
embedding = model.encode(memory.content)
memory.embedding = embedding.tolist()
```

4. **Vector Store**:
```python
import faiss
index = faiss.IndexFlatIP(1024)  # 1024-dim vectors
```

5. **Semantic Search**:
```python
query_embedding = model.encode(query)
similarities = index.search(query_embedding, k=10)
```

---

## 🚀 Quick Start

**1. Navigate to Dream Grove**:
- Open http://localhost:3333
- Click "ღ Dream Grove" in sidebar

**2. Explore Layers**:
- Click L0, L1, L2, or L3 cards
- View memories in each layer

**3. Search**:
- Type query in search bar
- Press Enter
- View highlighted results

**4. Run Decay**:
- Scroll to "Temporal Decay" panel
- Click "Run Decay Now"
- Watch importance scores decrease

**5. Compress**:
- Click "L0 → L1 Compress"
- New summary memory created in L1
- L0 memories remain (copies compressed)

---

## 📝 Memory Model

```typescript
interface Memory {
  id: string                    // Unique identifier
  content: string               // Memory text
  layer: 0 | 1 | 2 | 3         // L0-L3 layer
  embedding?: number[]          // BGE-M3 vector (1024-dim, future)
  tags: string[]                // Categorization tags
  importance: number            // 0.0-1.0 score
  created: string               // ISO timestamp
  last_accessed: string         // ISO timestamp
  access_count: number          // Retrieval count
  source: string                // Origin (conversation, note, etc.)
}
```

---

## 🎨 Layer Colors

| Layer | Icon | Color | Hex |
|-------|------|-------|-----|
| L0 | 🗄️ Database | Blue | `#3b82f6` |
| L1 | 📚 Layers | Purple | `#a855f7` |
| L2 | ⚡ Zap | Pink | `#ec4899` |
| L3 | 🔀 GitMerge | Amber | `#f59e0b` |

---

## 🔧 Configuration

### Temporal Decay
- **Default Rate**: 0.01
- **Formula**: `importance *= exp(-rate * hours_elapsed)`
- **Tunable**: Pass `decay_rate` parameter to `/api/memory/decay/run`

### Compression
- **Trigger**: Manual button or API call
- **Grouping**: By tags (3+ memories with same tags)
- **Ratio**: 5:1 (5 L0 → 1 L1)
- **Future**: Automatic nightly compression

### Search
- **Current**: Keyword substring matching
- **Future**: BGE-M3 semantic similarity
- **Threshold**: Configurable relevance score

---

**Phase 6 Status**: 🟡 20% Complete  
**Next Target**: 40% (BGE-M3 integration)  
**System Status**: 🟢 Fully Operational
