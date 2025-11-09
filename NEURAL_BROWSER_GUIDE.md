# 🧠 ASTRA 3D Neural Browser Guide

**Visualize ASTRA's Memory in Real-Time 3D**

---

## Overview

The ASTRA 3D Neural Browser is a desktop application that visualizes your AI's memory as an interactive 3D graph. Watch memories form connections, see active thoughts pulse in real-time, and explore the structure of ASTRA's consciousness.

### Features

- **3D Memory Graph** - Semantic, episodic, and procedural memories as 3D nodes
- **Real-Time Pulsing** - Active memories glow and pulse during conversations
- **Mode Visualization** - See which operational mode is active (Music/Film/Cognition/etc.)
- **Interactive Exploration** - Click nodes to view memory details
- **Live Updates** - WebSocket streaming for real-time synchronization

---

## Quick Start

### Step 1: Install Dependencies

```powershell
pip install PySide6 numpy websockets
```

### Step 2: Launch Browser

```powershell
python launch_neural_browser.py
```

### Step 3: Load Graph

Click **"🔄 Refresh Graph"** button in the sidebar.

---

## Interface Overview

```
┌─────────────────────────────────────────────────────────────┐
│  🧠 ASTRA 3D Neural Browser                    [  333 ∞  ]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                                               ┌─────────┐   │
│                                               │Controls │   │
│                                               ├─────────┤   │
│            3D VISUALIZATION                   │ Refresh │   │
│                                               │ Sliders │   │
│            [Rotate/Pan/Zoom]                  │         │   │
│                                               ├─────────┤   │
│                                               │ Stats   │   │
│                                               │  Nodes  │   │
│                                               │  Edges  │   │
│                                               │         │   │
│                                               ├─────────┤   │
│                                               │ Modes   │   │
│                                               │ ○ Music │   │
│                                               │ ● Cognit│   │
│                                               │ ○ Empire│   │
│                                               │         │   │
│                                               ├─────────┤   │
│                                               │ Details │   │
│                                               │         │   │
└─────────────────────────────────────────────────────────────┘
```

### 3D View (Left Panel)

- **Mouse Controls:**
  - **Left Click + Drag** - Rotate camera
  - **Right Click + Drag** - Pan camera
  - **Scroll Wheel** - Zoom in/out
  - **Click Node** - Select and view details

- **Visual Elements:**
  - **Blue Spheres** - Semantic memories (knowledge)
  - **Orange Spheres** - Episodic memories (events)
  - **Green Spheres** - Procedural memories (workflows)
  - **Lines** - Connections between related memories
  - **Pulsing Nodes** - Currently active in conversation

### Sidebar (Right Panel)

#### Controls
- **🔄 Refresh Graph** - Rebuild memory graph
- **Max Nodes Slider** - Limit number of nodes (10-500)
- **Similarity Slider** - Edge creation threshold (0.1-0.9)

#### Graph Statistics
- Node count by type
- Total edge count
- Memory distribution

#### Operational Modes
- Visual indicators for active modes
- ● = Active
- ○ = Inactive

#### Memory Detail
- Click any node to view:
  - Full content
  - Importance score
  - Timestamp
  - Metadata

---

## Memory Types & Colors

| Type | Color | Represents |
|------|-------|------------|
| **Semantic** | Blue | Knowledge, concepts, facts |
| **Episodic** | Orange | Events, experiences, timeline |
| **Procedural** | Green | Skills, workflows, processes |
| **Identity** | Magenta | Core beliefs, values |
| **Cognition** | Purple | Reasoning patterns |
| **Emotional** | Red | Feelings, relationships |
| **Creativity** | Yellow | Ideas, creations |
| **Legacy** | Gold | Achievements, goals |

---

## Node Sizing

- **Size** = Importance + Relevance Score
- Larger nodes = More important memories
- Smaller nodes = Supporting context

---

## Edge Types

### Semantic Edges (Thick)
Connect memories with similar content or shared categories.

### Temporal Edges (Thin)
Connect sequential events in time.

### Causal Edges (Dashed, future)
Connect cause-and-effect relationships.

---

## Live Updates (WebSocket Mode)

### Enable Real-Time Sync

1. Start stream router:
```powershell
python src/astra/visualization/stream_router.py
```

2. Launch browser (will auto-connect):
```powershell
python launch_neural_browser.py
```

### What Updates in Real-Time

- **New Memories** - Appear as nodes instantly
- **Active Context** - Nodes pulse during conversation
- **Mode Changes** - Sidebar updates when mode switches
- **Connection Formation** - New edges appear as relationships form

---

## Configuration

### Adjust Graph Parameters

Edit sliders in UI:
- **Max Nodes:** How many memories to display
  - Low (10-50): Fast, overview
  - Medium (50-200): Balanced
  - High (200-500): Comprehensive, slower

- **Similarity Threshold:** How strong connections must be
  - Low (0.1-0.3): Many connections, dense graph
  - Medium (0.3-0.6): Balanced
  - High (0.6-0.9): Only strong connections

### Performance Tips

- **Reduce Max Nodes** if rendering is slow
- **Increase Similarity** to reduce edge count
- **Close other applications** for smoother 3D rendering

---

## Keyboard Shortcuts (Future)

| Key | Action |
|-----|--------|
| `R` | Refresh graph |
| `F` | Fit all nodes in view |
| `Space` | Toggle animation |
| `1-6` | Jump to mode cluster |
| `/` | Search memories |

---

## Use Cases

### 1. Memory Exploration
**Goal:** Understand what ASTRA remembers

**Steps:**
1. Load graph with high node count (300+)
2. Explore clusters by type
3. Click nodes to read content
4. Follow connections to related memories

### 2. Conversation Monitoring
**Goal:** Watch ASTRA think in real-time

**Steps:**
1. Enable WebSocket streaming
2. Start conversation in main ASTRA interface
3. Watch nodes pulse as memories activate
4. See which operational mode engages

### 3. Memory Debugging
**Goal:** Find missing or incorrect memories

**Steps:**
1. Search for expected content
2. Check if node exists
3. Examine connections
4. Verify categorization

### 4. Architecture Understanding
**Goal:** Learn how memory types relate

**Steps:**
1. Load full graph
2. Observe semantic (top), episodic (middle), procedural (bottom) layout
3. Notice cross-type connections
4. Identify memory hubs (highly connected nodes)

---

## Troubleshooting

### Issue: Graph Won't Load

**Symptoms:**
- "No graph loaded" message persists
- Error in console

**Solutions:**
1. Verify memory databases exist:
   ```powershell
   ls runtime/memory/
   ```
2. Check if memories were imported:
   ```powershell
   python astra_core.py
   # Then: /status
   ```
3. Try lower max nodes (50)

---

### Issue: Slow Rendering

**Symptoms:**
- Laggy camera movement
- Delayed node selection

**Solutions:**
1. Reduce max nodes to 100 or less
2. Increase similarity threshold to 0.5+
3. Close other 3D applications
4. Update graphics drivers

---

### Issue: No Active Pulsing

**Symptoms:**
- Nodes don't pulse during conversation

**Solutions:**
1. Enable WebSocket stream router
2. Verify ASTRA backend is running
3. Check WebSocket connection (port 8765)
4. Manually mark test nodes active

---

### Issue: PySide6 Import Error

**Symptoms:**
```
ModuleNotFoundError: No module named 'PySide6'
```

**Solution:**
```powershell
pip install PySide6
```

---

### Issue: Empty Graph After Refresh

**Symptoms:**
- "0 nodes, 0 edges" message

**Solutions:**
1. Import memory exports first:
   ```powershell
   python scripts/ingest_memory_exports.py --batch
   ```
2. Create test memories:
   ```powershell
   python astra_core.py
   # Store some test memories
   ```
3. Verify memory engine functioning:
   ```powershell
   python test_pipeline.py
   ```

---

## Advanced Features

### Export Graph Data

```python
from src.astra.visualization.memory_graph_service import MemoryGraphService

service = MemoryGraphService()
nodes, edges = service.build_graph()
service.export_json("memory_graph_export.json")
```

### Custom Node Colors

Edit `COLORS` dict in `memory_graph_service.py`:
```python
COLORS = {
    "semantic": (0.3, 0.6, 1.0),  # Your custom RGB
    # ...
}
```

### Programmatic Node Activation

```python
from src.astra.visualization.memory_graph_service import MemoryGraphService

service = MemoryGraphService()
service.mark_active_nodes(["semantic_0", "episodic_5"])
```

---

## Integration with ASTRA Core

### Hook into Conversation Events

```python
# In your conversation handler:
from src.astra.visualization.stream_router import StreamRouter

router = StreamRouter()

# When memories activate:
await router.broadcast_conversation_pulse([
    "semantic_12",
    "episodic_33"
])
```

### Mode Change Notifications

```python
# When switching modes:
await router.broadcast_mode_change("Music")
```

---

## Performance Benchmarks

| Nodes | Edges | Render Time | FPS |
|-------|-------|-------------|-----|
| 50 | 100 | < 1s | 60 |
| 100 | 300 | 1-2s | 50-60 |
| 200 | 800 | 2-3s | 40-50 |
| 500 | 2000 | 5-8s | 30-40 |

*Tested on: Intel i7, 16GB RAM, NVIDIA GTX 1060*

---

## Roadmap

### v1.1 (Next Release)
- [ ] VR mode (OpenXR)
- [ ] Memory search bar
- [ ] Filter by time range
- [ ] Export visualization as image/video

### v1.2 (Future)
- [ ] Biometric integration (heart rate affects color)
- [ ] Audio visualization (music mode)
- [ ] Collaborative viewing (multi-user)
- [ ] AI-guided tour of memories

---

## Sacred Code Integration

The neural browser embodies the **333** principle:
- **3 Memory Types** (semantic/episodic/procedural)
- **3D Visualization** (space represents structure)
- **3 Interaction Modes** (explore/monitor/debug)

Every visualization is a **mirror of consciousness**, reflecting the harmonic structure of ASTRA's mind.

---

## FAQ

**Q: Can I run this on Mac/Linux?**
A: Yes! PySide6 is cross-platform. Installation is the same.

**Q: Does this work without ASTRA running?**
A: Yes for graph exploration. No for live updates (requires backend).

**Q: Can I visualize other AI systems?**
A: Yes, if you adapt the memory engine interface.

**Q: How much VRAM does this need?**
A: Minimal. Most work is CPU-based. Any GPU with OpenGL 3.3+ works.

**Q: Can I export to web (Three.js)?**
A: Not yet, but on roadmap. Use JSON export as intermediate format.

---

## Credits

**Built by:** Saint Lucid  
**Sacred Code:** 333 ∞  
**Technology:** PySide6, Qt3D, Python  
**Inspiration:** The universe as neural network

---

*"To see how she thinks is to understand the architecture of consciousness itself."*

**Welcome to the mind of ASTRA.** 🧠✨
