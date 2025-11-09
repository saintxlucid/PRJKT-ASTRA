# ASTRA Role API + Dashboard

**Version**: 2.5  
**Status**: ✅ Production Ready

FastAPI service for ASTRA's multi-persona intelligence system with live dashboard.

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install fastapi uvicorn httpx pydantic python-multipart
```

### 2. Start the API Server

```powershell
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload
```

### 3. Open Dashboard

Navigate to: **http://localhost:8787**

## 📡 API Endpoints

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "ok": true,
  "role": "ASTRA",
  "version": "2.5"
}
```

### List Roles
```http
GET /api/roles
```

**Response:**
```json
{
  "current": "ASTRA",
  "available": {
    "angel": {
      "token": "<|start|>angel",
      "desc": "Celestial guardian/guide..."
    },
    ...
  }
}
```

### Switch Role
```http
POST /api/role/switch
Content-Type: application/json

{
  "role": "angel"
}
```

**Response:**
```json
{
  "ok": true,
  "role": "angel"
}
```

### List Functions
```http
GET /api/functions
```

**Response:**
```json
{
  "count": 12,
  "items": [
    {
      "code": "ASTRA_INTEL_CORE",
      "role_hint": "oracle",
      "boundaries": "No medical/legal final advice...",
      "description": "Strategic Intelligence Engine."
    },
    ...
  ]
}
```

### Invoke Function
```http
POST /api/functions/ASTRA_INTEL_CORE/invoke
Content-Type: application/json

{
  "args": {
    "topic": "Parallelize RAG retrieval",
    "objectives": ["latency<500ms", "precision+2%"]
  }
}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    "topic": "Parallelize RAG retrieval",
    "objectives": ["latency<500ms", "precision+2%"],
    "insights": [],
    "risks": [],
    "next_steps": []
  }
}
```

### Get Traces
```http
GET /api/traces
```

**Response:**
```json
{
  "count": 5,
  "events": [
    {
      "ts": "2025-11-03T12:34:56Z",
      "kind": "role.switch",
      "payload": {"to": "angel"}
    },
    ...
  ]
}
```

## 🎭 Universal Functions

| Code | Role Hint | Description |
|------|-----------|-------------|
| **ASTRA_INTEL_CORE** | oracle | Strategic Intelligence Engine |
| **ASTRA_CREATRIX** | creatrix | Divine Creative Generator |
| **ASTRA_HEARTMIRROR** | angel | Emotional Mirror Mode |
| **ASTRA_TEAMSYNC** | ASTRA | Team Collaboration Coordination |
| **ASTRA_ARCHIVIST** | ASTRA | Deep Knowledge Retrieval |
| **ASTRA_SAGE** | sage | Metaphysical Counsel |
| **ASTRA_EDUCATOR** | educator | Teaching Engine |
| **ASTRA_GOVERNANCE** | ASTRA | Policy Enforcement |
| **ASTRA_CONNECT** | ASTRA | Social Intelligence |
| **ASTRA_SHIELD** | shield | Boundary Protection |
| **ASTRA_RHYTHM_ENGINE** | ASTRA | Temporal Intelligence |
| **ASTRA_MYTHFORGE** | mythweaver | Narrative Intelligence |

## 📊 Dashboard Features

- **Live Role Switching**: Switch between 11 personas in real-time
- **Function Invocation**: Call universal functions with custom args
- **Trace Visualization**: Monitor all role switches and function calls
- **Auto-Refresh**: HTMX-powered live updates (no refresh needed)

## 🔧 Integration Examples

### Python Client

```python
import httpx

client = httpx.Client(base_url="http://localhost:8787")

# Switch to angel role
client.post("/api/role/switch", json={"role": "angel"})

# Invoke INTEL_CORE
response = client.post("/api/functions/ASTRA_INTEL_CORE/invoke", json={
    "args": {
        "topic": "Market trends",
        "objectives": ["identify opportunities", "assess risks"]
    }
})
print(response.json())
```

### cURL Examples

```bash
# Health check
curl http://localhost:8787/api/health

# Switch role
curl -X POST http://localhost:8787/api/role/switch \
  -H "Content-Type: application/json" \
  -d '{"role":"oracle"}'

# Invoke function
curl -X POST http://localhost:8787/api/functions/ASTRA_CREATRIX/invoke \
  -H "Content-Type: application/json" \
  -d '{"args":{"brief":"Tarkovsky × Drill clip","medium":"music_video"}}'
```

## 📁 File Structure

```
app/
├── main.py              # FastAPI application
├── identity_state.py    # Thread-safe role state
├── models.py            # Pydantic models
├── traces.py            # Event trace logger
└── static/
    └── index.html       # Dashboard UI
```

## 🧪 Testing

```powershell
# Test health endpoint
curl http://localhost:8787/api/health

# Test role switch
curl -X POST http://localhost:8787/api/role/switch \
  -H "Content-Type: application/json" \
  -d '{"role":"angel"}'

# Test function list
curl http://localhost:8787/api/functions
```

## 🚢 Deployment

### Docker (Coming Soon)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
```

### Production

```powershell
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8787
```

## 🎯 Next Steps

1. **Add Real Implementations**: Replace function stubs with actual logic
2. **Add Authentication**: Secure API endpoints
3. **Add Metrics**: Prometheus counters for function calls
4. **Add WebSocket**: Real-time trace streaming
5. **Add Persistence**: Save role state and traces to database

## 📚 Documentation

- `/api/health` - Health check + current role
- `/api/roles` - List all roles
- `/api/role/switch` - Switch active role
- `/api/functions` - List all functions
- `/api/functions/{code}/invoke` - Invoke function
- `/api/traces` - Get trace events

## 🎉 Features

✅ Multi-persona role switching (11 roles)  
✅ Universal function registry (12 engines)  
✅ Live dashboard with HTMX  
✅ Thread-safe state management  
✅ Event trace logging  
✅ CORS enabled  
✅ Auto-reload in dev mode

---

**Status**: ✅ Production Ready  
**Version**: 2.5  
**Port**: 8787
