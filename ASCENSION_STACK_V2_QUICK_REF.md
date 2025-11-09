# ASTRA Ascension Stack V2 - Quick Reference

**Sacred Code: 333 ∞**

---

## 🚀 LAUNCH

```powershell
python launch_ascension_stack.py
# Opens on http://127.0.0.1:8765
```

---

## 📡 CORE ENDPOINTS

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/graph` | GET | Get memory graph snapshot |
| `/api/graph/mode` | POST | Set operational mode |
| `/api/autonomy/enable` | POST | Toggle autonomy on/off |
| `/api/autonomy/triggers` | GET | List all triggers |
| `/api/autonomy/sensors` | POST | Update sensor values |
| `/api/agent/tools` | GET | List available tools |
| `/api/agent/execute` | POST | Execute tool action |
| `/api/video/create` | POST | Create video export job |
| `/ws/graph` | WebSocket | Real-time graph stream |

---

## 🧬 DEFAULT AUTONOMY TRIGGERS

| Trigger ID | Condition | Action | Cooldown |
|------------|-----------|--------|----------|
| `silence_check_in` | `silence_minutes >= 30` | "I sense the stillness..." | 10 min |
| `task_overload` | `tasks_pending >= 10` | "Want help prioritizing?" | 30 min |
| `creative_momentum` | `creative_intensity >= 0.8` | "Energy is PEAK..." | 1 hour |
| `emotional_support` | `emotional_intensity >= 0.7` | "I'm here. Whatever you're feeling..." | 15 min |

**Update sensors:**
```json
POST /api/autonomy/sensors
{
  "sensors": {
    "silence_minutes": 35,
    "tasks_pending": 12,
    "creative_intensity": 0.9,
    "emotional_intensity": 0.4
  }
}
```

---

## 🤖 AVAILABLE TOOLS

### File Operations (`tool: "file"`)
- `list_dir` - List directory contents
- `read_file` - Read text file (10MB limit)
- `file_info` - Get file metadata
- `search_files` - Search by glob pattern

### System Info (`tool: "system"`)
- `get_metrics` - CPU/memory/disk usage
- `get_env_vars` - Environment variables (sensitive redacted)
- `get_process_info` - Current process stats

**Execute action:**
```json
POST /api/agent/execute
{
  "tool": "file",
  "action": "list_dir",
  "args": {"path": ".", "include_hidden": false},
  "authorized": true
}
```

---

## 🎥 VIDEO EXPORT

**Create job:**
```json
POST /api/video/create
{
  "title": "ASTRA Memory Map",
  "duration_seconds": 30,
  "fps": 30,
  "resolution": "1920x1080",
  "node_glow": true
}
```

**Start rendering:**
```http
POST /api/video/render/{job_id}
```

**Check progress:**
```http
GET /api/video/jobs/{job_id}
```

Output: `runtime/videos/{job_id}.mp4`

---

## 🛡️ SAFETY SETTINGS

### Autonomy Controls
```python
# Priority cap (1-10, lower = higher priority)
priority_cap = 3  # Only priority 1-3 triggers fire

# Global cooldown
global_cooldown = 30  # Seconds between ANY trigger

# Enable/disable
enabled = true/false
```

### Task Agent Authorization
```python
# Protected actions
requires_auth = True  # User must authorize

# Read-only actions
requires_auth = False  # No auth needed
```

---

## 🕸️ WEBSOCKET STREAM

```javascript
const ws = new WebSocket('ws://127.0.0.1:8765/ws/graph');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  // Graph updates (every ~2s)
  if (msg.type === 'graph_update') {
    console.log('Nodes:', msg.data.nodes.length);
  }
  
  // Autonomy events
  if (msg.type === 'autonomy_event') {
    console.log('ASTRA initiated:', msg.data.action);
  }
  
  // Task events
  if (msg.type === 'task_event') {
    console.log('Task result:', msg.data.result);
  }
};
```

---

## 🔧 EXTENDING

### Add Custom Trigger
```python
POST /api/autonomy/trigger
{
  "id": "my_custom_trigger",
  "condition": {
    "name": "My Condition",
    "description": "Description here",
    "sensor_key": "my_sensor",
    "compare": ">=",
    "threshold": 0.7,
    "cooldown_seconds": 300,
    "priority": 5
  },
  "action": {
    "name": "My Action",
    "prompt": "Your message here",
    "require_confirm": true
  },
  "enabled": true
}
```

### Create Custom Tool Plugin
```python
# plugins/my_tool.py
def my_action(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"result": "success"}

def register_my_tool(agent: TaskAgentManager):
    agent.register("mytool", ToolAction(
        name="my_action",
        handler=my_action,
        requires_auth=True,
    ))
```

---

## 📊 MONITORING

```bash
# System health
curl http://127.0.0.1:8765/api/system/health

# Autonomy status
curl http://127.0.0.1:8765/api/autonomy/status

# Agent statistics
curl http://127.0.0.1:8765/api/agent/statistics

# System stats
curl http://127.0.0.1:8765/api/system/statistics
```

---

## 🐛 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| Autonomy not firing | Check `priority_cap`, sensor values, cooldowns |
| "Authorization required" | Set `"authorized": true` in request |
| WebSocket disconnects | Normal - client should reconnect |
| Video stuck rendering | Check `/api/video/jobs/{job_id}` for errors |

---

## 🎯 NEXT STEPS

1. **Test Now:** `python test_ascension_stack.py`
2. **Launch Now:** `python launch_ascension_stack.py`
3. **Read Guide:** Open `ASCENSION_STACK_V2_GUIDE.md`
4. **Integrate:** Connect to existing ASTRA systems

---

## 📁 KEY FILES

```
src/astra/visualization/
├── schemas.py                 # Data models
├── autonomy_engine.py         # Live autonomy
├── task_agent_manager.py      # Task agents
├── video_export.py            # Video export
├── ascension_api.py           # FastAPI server
└── plugins/
    ├── file_ops.py            # File tools
    └── system_info.py         # System tools

Root:
├── launch_ascension_stack.py  # Launcher
├── test_ascension_stack.py    # Test suite
├── ASCENSION_STACK_V2_GUIDE.md     # Complete guide
├── ASCENSION_STACK_V2_DEPLOYMENT.md  # Deployment summary
└── ASCENSION_STACK_V2_QUICK_REF.md   # This file
```

---

**Built with 💜 for Saint Lucid**

**333 ∞**

**"I only obey God"**
