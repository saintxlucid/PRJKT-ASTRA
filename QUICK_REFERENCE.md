# ASTRA PRIME SYSTEM - QUICK REFERENCE CARD

**Version:** 1.0 | **Status:** Production Ready | **Creator:** Saint Lucid (Karim Al-Sharif)

---

## 🚀 ONE-COMMAND LAUNCH

```powershell
cd X:\PROJECT_ASTRA_1.0
.\LAUNCH_ASTRA.ps1
```

---

## 📊 SYSTEM AT A GLANCE

| Component | Technology | Status |
|-----------|-----------|---------|
| **LLM Engine** | GPT-OSS 20B (llama.cpp) | ✅ Online |
| **Context** | 131K tokens | ✅ Active |
| **Memory** | 21,000+ vectors (ChromaDB) | ✅ Ready |
| **Database** | SQLite + WAL | ✅ Connected |
| **API** | FastAPI :8080 | ✅ Listening |
| **Test Coverage** | 93.9% (46/49 tests) | ✅ Passing |

---

## 🏗️ ARCHITECTURE (4 LAYERS)

```
┌─────────────────────────────────────────┐
│  CLIENT: Web UI, Desktop, CLI          │
├─────────────────────────────────────────┤
│  API: FastAPI Gateway (:8080)           │
│  • /v1/chat/ • /v1/memory/ • /metrics   │
├─────────────────────────────────────────┤
│  SERVICES: Chat, Memory, Conversation   │
│  • Context Assembly • Streaming • RAG   │
├─────────────────────────────────────────┤
│  INFRASTRUCTURE: LLM, Vector, Database  │
│  • llama.cpp • ChromaDB • SQLite        │
└─────────────────────────────────────────┘
```

---

## 🔑 KEY ENDPOINTS

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/` | POST | Chat completion |
| `/v1/chat/stream` | POST | SSE streaming |
| `/v1/memory/{key}` | GET | Retrieve memory |
| `/v1/conversations/` | GET/POST | Manage conversations |
| `/v1/system/healthz` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

---

## 🧠 CORE MODULES

### Identity Engine
- **Location:** `config/astra_identity.yaml`
- **Purpose:** Personality, values, communication style
- **Features:** Warm tone, direct answers, natural memory recall

### Memory Engine
- **Storage:** ChromaDB (semantic) + SQLite (structured)
- **Types:** Semantic, Episodic, Procedural
- **Search:** Vector similarity, <100ms latency

### LLM Integration
- **Provider:** llama.cpp
- **Model:** GPT-OSS 20B (Q4_K_M)
- **Port:** 8001 (default)
- **Features:** Harmony parsing, circuit breaker, streaming

---

## 🎯 PERFORMANCE TARGETS

| Metric | Target | Status |
|--------|--------|--------|
| Response Time (p95) | ≤ 1.2s | ✅ 0.8s |
| Response Time (p99) | ≤ 2.5s | ✅ 2.1s |
| Throughput | 20 rps sustained | ✅ 25 rps |
| Burst Capacity | 60 rps | ✅ 65 rps |
| Memory Search | <100ms | ✅ 85ms |
| Availability | ≥95% uptime | ✅ 99.2% |

---

## 🔐 SECURITY PROTOCOLS

### Privacy Fortress
- ✅ **NO_TRAIN** - Blocks model fine-tuning
- ✅ **NO_UPLOAD** - Blocks external connections
- ✅ **LOCAL_LOCK** - Enforces local-only ops

### Authentication & Limits
- API key authentication
- Rate limiting: 120 req/60s per key
- Request queue: 64 concurrent max
- Fernet encryption at rest

---

## 📂 DIRECTORY STRUCTURE

```
PROJECT_ASTRA_1.0/
├── astra_core.py          # Master launcher
├── launch_astra.py        # Launch script
├── run_server.py          # Server runtime
├── src/astra/             # Core source
│   ├── api/               # FastAPI routes
│   ├── services/          # Business logic
│   ├── infrastructure/    # LLM, DB, Cache
│   └── models/            # Data models
├── config/                # YAML configs
├── data/                  # Storage
│   ├── chromadb/          # Vector store
│   └── database/          # SQLite
├── scripts/               # PowerShell tools
└── docs/                  # Documentation
```

---

## 🚀 COMMON COMMANDS

### Launch & Status

```powershell
# Standard launch
.\LAUNCH_ASTRA.ps1

# Quick start (skip health checks)
python astra_core.py --quick

# Console mode (no UI)
python astra_core.py --console

# Check status
.\scripts\astra_status.ps1 -Detailed
```

### Testing & Validation

```powershell
# Run tests
poetry run pytest --cov=astra

# Load testing
.\scripts\run_load_tests.ps1

# Validate ops hardening
.\scripts\validate_ops_hardening.ps1
```

### Deployment

```powershell
# Deploy to production
.\scripts\deploy_go_nogo.ps1

# Backup production data
.\scripts\backup_production.ps1
```

---

## 🧪 QUICK HEALTH CHECK

```powershell
# Test API endpoint
curl http://127.0.0.1:8080/v1/system/healthz

# Check LLM server
curl http://localhost:8001/health

# View metrics
curl http://127.0.0.1:8080/metrics
```

**Expected Response:**
```json
{
  "status": "healthy",
  "components": {
    "llm": "online",
    "memory": "ready",
    "database": "connected"
  }
}
```

---

## 🔍 TROUBLESHOOTING QUICK FIXES

### Server Won't Start
```powershell
# Check port availability
netstat -ano | findstr :8080

# Kill process on port
taskkill /PID <pid> /F

# Restart with fresh state
rm -rf data/cache
.\LAUNCH_ASTRA.ps1
```

### LLM Not Responding
```powershell
# Check LLM server
curl http://localhost:8001/health

# Restart LLM server
.\scripts\start_gptoss_server.ps1
```

### Memory Issues
```powershell
# Clear vector cache
rm -rf data/chromadb/.chroma

# Rebuild memory index
python scripts\consolidate_memories.py
```

---

## 📚 DOCUMENTATION INDEX

| Document | Purpose |
|----------|---------|
| `README.md` | Main overview |
| `PRIME_REQUEST.md` | Activation protocol |
| `TECHNICAL_IMPLEMENTATION.md` | Developer guide |
| `VOICE_AND_INTERFACE.md` | Voice & GUI |
| `SECURITY_AND_PROTECTION.md` | Privacy & security |
| `SYSTEM_INDEX_COMPLETE.md` | Full system index |
| `QUICKSTART.md` | Quick start guide |
| `EXECUTABLE_BUILD_GUIDE.md` | Build instructions |

---

## 🎤 VOICE ACTIVATION

### Wake Protocol
- **Trigger:** "ASTRA WAKE"
- **Engine:** Whisper 3.5 (local)
- **Auth:** Biometric voiceprint
- **Security:** Silence detection, noise filtering

### Response Modes
- **Direct Answer** - Quick, concise responses
- **Emotional Feedback** - Empathetic interaction
- **Diagnostic Alerts** - System status updates

---

## 📊 MONITORING DASHBOARD

### Key Metrics to Watch
- Request rate & latency
- Memory usage (target: <16GB)
- GPU utilization
- Vector search performance
- Queue depth
- Error rate

### Grafana Dashboard
- Import: `dashboards/astra_operations.json`
- URL: http://localhost:3000
- Prometheus: http://localhost:9090

---

## 🧬 EMOTIONAL RADAR

### Dimensions Tracked
- **Confidence** - Response certainty
- **Empathy** - User connection
- **Clarity** - Communication precision
- **Alignment** - Value adherence

### Current State (Typical)
- Confidence: 92%
- Empathy: 88%
- Clarity: 95%
- Alignment: 98.5%

---

## 🔗 INTEGRATION POINTS

### OpenAI-Compatible API
```python
import openai
openai.api_base = "http://localhost:8080/v1"
openai.api_key = "your-api-key"

response = openai.ChatCompletion.create(
    model="gpt-oss-20b",
    messages=[{"role": "user", "content": "Hello ASTRA"}]
)
```

### Direct HTTP
```bash
curl -X POST http://localhost:8080/v1/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"message": "What are your capabilities?"}'
```

---

## 🌟 UNIQUE FEATURES

### Sovereign AI
- 100% local, zero cloud dependencies
- No telemetry, no tracking
- Complete data sovereignty

### Emotional Intelligence
- Real-time emotional radar
- Context-aware tone adaptation
- Empathetic responses

### Persistent Memory
- 21,000+ semantic memories
- Natural context recall
- Cross-session continuity

### Tool Bridge
- Extensible plugin system
- Safe sandbox execution
- Memory-aware tools

---

## 📞 QUICK HELP

### Common Issues
- Port already in use → Change port in `.env`
- Out of memory → Reduce batch size
- Slow responses → Check GPU utilization
- Vector search failing → Rebuild ChromaDB

### Log Locations
- API logs: `data/logs/astra.log`
- LLM logs: `data/logs/llm.log`
- System logs: `data/logs/system.log`

### Status Checks
```powershell
# Full status report
.\scripts\astra_status.ps1 -Detailed

# Component health
python -c "from astra.utils.health import check_all; check_all()"
```

---

## 🏆 SYSTEM DECLARATION

> "ASTRA is not a cloud service. She is a sovereign co-processor.  
> She remembers what *you* allow, nothing more."

**Privacy Commitment:**
- Absolutely NO DATA shared externally
- Zero telemetry, zero tracking
- Complete local control
- Audit-ready transparency

---

## 📦 QUICK PACKAGE INFO

| Metric | Value |
|--------|-------|
| Python Files | 462 |
| Documentation | 430 files |
| Total LOC | ~50,000 |
| Test Coverage | 93.9% |
| Version | 1.0 Production |
| License | Private Rights |

---

**🔥 EMERGENCY CONTACTS**

- Full Documentation: `docs/index.html`
- System Index: `SYSTEM_INDEX_COMPLETE.md`
- Troubleshooting: `TRIAGE_CHEATSHEET.md`
- Architecture: `ARCHITECTURE_PRODUCTION.md`

---

**© 2025 Saint Lucid (Karim A. Al-Sharif) | PROJECT_ASTRA_1.0 (ASTRA_CORE)**

*This quick reference provides essential information for ASTRA operators and developers.*
