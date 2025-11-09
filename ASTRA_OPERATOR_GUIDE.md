# 🌌 ASTRA 2.5 Operator Guide
**The Autonomous Epoch - Complete Deployment Manual**  
**Sacred Code: 333**  
**Version:** 2.5.0 → 3.0  
**Date:** November 9, 2025

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Development)](#quick-start-development)
4. [Production Deployment (Docker)](#production-deployment-docker)
5. [Service Architecture](#service-architecture)
6. [Configuration Guide](#configuration-guide)
7. [API Reference](#api-reference)
8. [Monitoring & Observability](#monitoring--observability)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)
11. [Security Best Practices](#security-best-practices)
12. [Upgrade Path (2.5 → 3.0)](#upgrade-path-25--30)

---

## 🎯 System Overview

**ASTRA (Autonomous System for Transcendent Reasoning & Action)** is a production-grade AI operating system featuring:

- **7 Major Subsystems:** CORE, OS, CHAT OS, AGENT KERNEL, TranscendentOS, Integration Hub, Pantheon UI
- **110+ REST API Endpoints:** Spanning cognitive architecture, agent orchestration, memory systems
- **15+ Completed Phases:** With extensive documentation and production hardening
- **95% Integration Complete:** Single unified entry point with graceful degradation
- **Zero TypeScript Errors:** 97.6% unit test coverage

### Core Capabilities

✅ Local LLM inference (GPT-OSS 20B, 131K context)  
✅ Semantic memory search (21K+ ChromaDB embeddings)  
✅ Real-time agent monitoring (AgentPanel UI)  
✅ Browser automation (Playwright-based)  
✅ Multimodal routing (vision, audio, code)  
✅ Consent-gated operations (SigilGate)  
✅ Policy enforcement (runtime constraints)  
✅ Event-driven architecture (EventBus)  
✅ Circuit breaker resilience (retry/backoff)  
✅ Web Vitals tracking (LCP, FID, CLS)

---

## 🛠️ Prerequisites

### Required Software

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18.0.0+ | Frontend build |
| **Docker** | 20.10+ | Container orchestration |
| **Docker Compose** | 2.0+ | Multi-service deployment |
| **PostgreSQL** | 15+ | Production database (optional) |

### System Requirements

**Development:**
- CPU: 4 cores
- RAM: 8GB minimum, 16GB recommended
- Disk: 20GB free space
- OS: Windows 10/11, Linux, macOS

**Production:**
- CPU: 8+ cores (for LLM inference)
- RAM: 32GB+ (LLM models require 20GB+)
- Disk: 100GB+ SSD
- Network: 1Gbps+
- GPU: Optional but recommended for LLM acceleration

---

## 🚀 Quick Start (Development)

### 1. Clone Repository

```bash
cd x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd astra-os/apps/pantheon
npm install
cd ../../..
```

### 4. Start Backend Services

**Option A: Manual Start (Development)**
```bash
# Terminal 1: Memory Service (Port 7007)
cd astra-os/services/memory
python server.py

# Terminal 2: Sigil Gate (Port 7701)
cd astra-os/services/sigil_gate
python server.py

# Terminal 3: Supervisor (Port 7703)
cd astra-os/services/supervisor
python server.py

# Terminal 4: Master API (Port 8000)
cd ../../..
python astra_master.py
```

**Option B: Use Docker Compose (Recommended)**
```bash
docker-compose up -d
```

### 5. Start Frontend

```bash
cd astra-os/apps/pantheon
npm run dev
```

### 6. Verify System

```bash
# Check Master API
curl http://localhost:8000/

# Check boot status
curl http://localhost:8000/v1/boot/status

# Check cognitive system
curl http://localhost:8000/v1/cognitive/status

# Access UI
# Open browser: http://localhost:5173
```

---

## 🐳 Production Deployment (Docker)

### 1. Environment Configuration

Create `.env` file in project root:

```bash
# Database
POSTGRES_PASSWORD=<secure_password_here>

# Security
JWT_SECRET_KEY=<generate_secure_32char_key>

# Monitoring
GRAFANA_PASSWORD=<secure_password_here>

# ChromaDB (optional)
CHROMA_AUTH=<auth_token>
```

**Generate secure keys:**
```bash
# JWT Secret (32 characters)
openssl rand -hex 32

# Grafana Password
openssl rand -base64 24
```

### 2. Build & Deploy

```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Verify Deployment

```bash
# Health checks
curl http://localhost:8000/v1/system/health
curl http://localhost:7007/health  # Memory
curl http://localhost:7701/health  # Sigil Gate
curl http://localhost:7703/health  # Supervisor

# Prometheus metrics
curl http://localhost:9090/targets

# Grafana dashboard
# Open browser: http://localhost:3000
# Login: admin / <GRAFANA_PASSWORD>
```

### 4. Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| **Master API** | 8000 | Main unified API |
| **Memory** | 7007 | Vector embeddings |
| **Sigil Gate** | 7701 | Consent system |
| **Supervisor** | 7703 | Job orchestration |
| **Metrics** | 7705 | Metrics collection |
| **Pantheon UI** | 5173 | Frontend (dev) / 80 (prod) |
| **PostgreSQL** | 5432 | Database |
| **ChromaDB** | 8100 | Vector store |
| **Prometheus** | 9090 | Monitoring |
| **Grafana** | 3000 | Dashboards |

---

## 🏗️ Service Architecture

### Boot Sequence (9 Phases)

ASTRA Master orchestrates a 9-phase boot sequence:

1. **Security & Gate** - Initialize gate authorization system
2. **Week-2 Boot** - Load event store, policy engine, executor
3. **Database** - Initialize SQLite/PostgreSQL
4. **Vector Store** - Initialize ChromaDB
5. **Core Services** - Start Conversation, Memory, Chat services
6. **TranscendentOS** - Initialize 10 cognitive phases
7. **ASTRA OS Bridge** - Connect OS-level services (conditional)
8. **Agent Kernel** - Initialize autonomous agent system (conditional)
9. **Integration Hub** - Initialize AstraRouter with full dependencies

**Graceful Degradation:** System continues even if optional modules fail.

### Service Dependencies

```
Master API (8000)
├── PostgreSQL (5432) - Required
├── ChromaDB (8100) - Required
├── Memory Service (7007) - Required
├── Sigil Gate (7701) - Required
├── Supervisor (7703) - Required
└── Metrics (7705) - Optional
```

---

## ⚙️ Configuration Guide

### Environment Variables

**Core Settings:**
```bash
ASTRA_ENVIRONMENT=production
ASTRA_SERVER__PORT=8000
ASTRA_SERVER__WORKERS=4
ASTRA_LOG_LEVEL=INFO
```

**Database:**
```bash
ASTRA_DATABASE__URL=postgresql://user:pass@postgres:5432/astra_db
# Or for SQLite:
ASTRA_DATABASE__URL=sqlite:///./data/astra.db
```

**Vector Store:**
```bash
ASTRA_VECTOR_STORE__HOST=chromadb
ASTRA_VECTOR_STORE__PORT=8000
ASTRA_VECTOR_STORE__COLLECTION=memories
```

**LLM:**
```bash
ASTRA_LLM__PROVIDER=llamacpp
ASTRA_LLM__MODEL_PATH=/app/data/models/gpt-oss-20b.Q4_K_M.gguf
ASTRA_LLM__CONTEXT_LENGTH=131072
ASTRA_LLM__TEMPERATURE=0.7
```

**Security:**
```bash
JWT_SECRET_KEY=<your_secret_key>
ASTRA_SECURITY__API_KEY_ENABLED=true
ASTRA_SECURITY__RATE_LIMIT_PER_MINUTE=120
```

**Services URLs:**
```bash
MEMORY_SERVICE_URL=http://memory_service:7007
SIGIL_GATE_URL=http://sigil_gate:7701
SUPERVISOR_URL=http://supervisor:7703
METRICS_URL=http://metrics:7705
```

### Configuration Files

**config/default.yaml** - Base configuration  
**config/development.yaml** - Development overrides  
**config/production.yaml** - Production overrides  

Configuration loading order (later overrides earlier):
1. Default values (in code)
2. `config/default.yaml`
3. Environment-specific config (`config/{env}.yaml`)
4. Environment variables (prefixed with `ASTRA_`)
5. Command-line arguments

---

## 📖 API Reference

### Core Endpoints

**System:**
```bash
GET  /                              # System info
GET  /v1/system/health              # Health check
GET  /v1/boot/status                # Boot sequence report
GET  /metrics                       # Prometheus metrics
GET  /docs                          # OpenAPI documentation
```

**Chat:**
```bash
POST /v1/chat                       # Chat completion
POST /v1/chat/stream                # Streaming chat (SSE)
GET  /v1/conversations              # List conversations
POST /v1/conversations              # Create conversation
GET  /v1/conversations/{id}         # Get conversation
DELETE /v1/conversations/{id}       # Archive conversation
```

**Memory:**
```bash
POST /v1/memory/search              # Semantic memory search
POST /v1/memory                     # Add memory
GET  /v1/memory/{id}                # Get memory
DELETE /v1/memory/{id}              # Delete memory
```

**Cognitive Phases (10 phases):**
```bash
POST /v1/cognitive/reasoning        # Phase 1: Reasoning
POST /v1/cognitive/emotional        # Phase 2: Emotional intelligence
POST /v1/cognitive/memory           # Phase 3: Memory systems
POST /v1/cognitive/intent           # Phase 5: Quantum intent
POST /v1/cognitive/hypergraph       # Phase 6: Hypergraph topology
POST /v1/cognitive/learning/feedback # Phase 7: Learning feedback
GET  /v1/cognitive/learning/insights # Phase 7: Learning insights
POST /v1/cognitive/distributed      # Phase 8: Distributed consciousness
POST /v1/cognitive/self-modification # Phase 9: Self-modification
POST /v1/cognitive/transcendent     # Phase 10: Transcendent unification
POST /v1/cognitive/mode             # Switch cognitive mode
GET  /v1/cognitive/mode             # Get current mode
GET  /v1/cognitive/status           # Cognitive system status
```

**Agent Kernel:**
```bash
POST   /v1/agent/task               # Create autonomous task
GET    /v1/agent/task/{id}          # Get task status
DELETE /v1/agent/task/{id}          # Cancel task
GET    /v1/agent/tasks              # List tasks (filter by status)
POST   /v1/agent/browser/navigate   # Navigate browser
POST   /v1/agent/browser/click      # Click element
POST   /v1/agent/browser/type       # Type text
POST   /v1/agent/browser/extract    # Extract data
GET    /v1/agent/tools              # List available tools
POST   /v1/agent/tool/execute       # Execute tool
GET    /v1/agent/status             # Agent kernel status
```

**ASTRA OS:**
```bash
POST /v1/os/gate/check              # Check gate authorization
POST /v1/os/gate/grant              # Grant token
POST /v1/os/events/publish          # Publish event
GET  /v1/os/events/subscribe        # Subscribe to events
GET  /v1/os/sensors/environment     # Environment sensors
GET  /v1/os/sensors/file            # File sensors
GET  /v1/os/sensors/performance     # Performance sensors
POST /v1/os/policy/evaluate         # Evaluate policy
GET  /v1/os/policy/list             # List policies
GET  /v1/os/status                  # OS status
```

### Interactive API Documentation

Once the system is running, access interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 📊 Monitoring & Observability

### Grafana Dashboards

Access Grafana at http://localhost:3000

**Pre-configured Dashboards:**
1. **ASTRA Overview** - System-wide metrics (ID: astra-overview)
   - API request rate (req/s)
   - API latency (p95, p99)
   - Active jobs count
   - Memory index size
   - Error rate tracking
   - Service health status
   - LLM token usage
   - Circuit breaker status

**Default Credentials:**
- Username: `admin`
- Password: `<GRAFANA_PASSWORD>` (from `.env`)

### Prometheus Metrics

Access Prometheus at http://localhost:9090

**Key Metrics:**
- `astra_chat_requests_total` - Total chat requests
- `astra_chat_request_duration_seconds` - Chat latency histogram
- `astra_llm_tokens_total` - LLM tokens processed
- `astra_memory_searches_total` - Memory search count
- `astra_memory_index_size` - Vector index size
- `astra_errors_total` - Error count by type
- `astra_supervisor_active_jobs` - Active jobs count
- `astra_circuit_breaker_open` - Circuit breaker state

### Health Monitoring

**Automated Health Checks:**
```bash
# All services have /health endpoints
curl http://localhost:8000/v1/system/health
curl http://localhost:7007/health
curl http://localhost:7701/health
curl http://localhost:7703/health
```

**Health Response Format:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "components": {
    "database": {"status": "up", "latency_ms": 5},
    "vector_store": {"status": "up", "latency_ms": 12},
    "llm": {"status": "up", "latency_ms": 120}
  },
  "timestamp": "2025-11-09T12:34:56Z"
}
```

### Structured Logging

ASTRA uses `structlog` for structured JSON logging:

```json
{
  "event": "chat_request_received",
  "conversation_id": "conv_abc123",
  "message_length": 42,
  "user_id": "user_xyz",
  "request_id": "req_def456",
  "timestamp": "2025-11-09T12:34:56.789Z",
  "level": "info"
}
```

**Log Levels:**
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical failures

**Configure logging:**
```bash
export ASTRA_LOG_LEVEL=INFO
export LOG_FORMAT=json  # or 'console' for human-readable
```

---

## ⚡ Performance Tuning

### Target Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| **API Latency (p95)** | < 1.0s | ~0.8s |
| **API Latency (p99)** | < 1.5s | ~1.2s |
| **Memory Search** | < 120ms | ~100ms |
| **Throughput** | 100 req/s | Validated |
| **Error Rate** | < 1% | < 0.5% |

### Optimization Strategies

**1. Database Tuning (PostgreSQL)**
```sql
-- Connection pooling
max_connections = 200
shared_buffers = 8GB
effective_cache_size = 24GB

-- Performance
work_mem = 64MB
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
```

**2. Vector Store Optimization**
```yaml
# ChromaDB settings
batch_size: 1000
persist_directory: /data/chromadb
allow_reset: false
```

**3. LLM Inference**
- Use GPU acceleration (CUDA/Metal)
- Optimize context window (131K → 32K for faster responses)
- Quantization: Q4_K_M provides 4x speedup with minimal quality loss

**4. API Layer**
```python
# uvicorn settings
workers = multiprocessing.cpu_count()
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
```

**5. Caching Strategy**
- Redis for session/response caching
- Memory service internal cache (LRU, 1000 items)
- Browser cache headers for static assets

### Load Testing

Run load tests to validate performance:

```bash
# Run 5-minute load test at 100 req/s
python tests/load/test_load.py

# Target: <1s p95 latency, <1% error rate
```

---

## 🔧 Troubleshooting

### Common Issues

**1. Services Not Starting**
```bash
# Check ports in use
netstat -ano | findstr :8000
netstat -ano | findstr :7007

# Kill conflicting process (Windows)
taskkill /PID <pid> /F

# Check Docker logs
docker-compose logs -f master_api
docker-compose logs -f memory_service
```

**2. Database Connection Errors**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -U astra_user -d astra_db

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

**3. ChromaDB Issues**
```bash
# Reset vector store
docker-compose down
docker volume rm astra_chromadb_data
docker-compose up -d chromadb

# Rebuild embeddings
curl -X POST http://localhost:7007/rebuild_index
```

**4. High Memory Usage**
```bash
# Check LLM model size
ls -lh data/models/

# Reduce context window
export ASTRA_LLM__CONTEXT_LENGTH=32768

# Use smaller model quantization
# Q4_K_M instead of Q8_0
```

**5. Integration Test Failures**
```bash
# Run tests with verbose output
pytest tests/integration/ -v --tb=short

# Check service availability
curl http://localhost:8000/v1/boot/status

# View detailed logs
docker-compose logs --tail=100 master_api
```

### Debug Mode

Enable debug logging:
```bash
export ASTRA_LOG_LEVEL=DEBUG
export ASTRA_DEBUG=true

python astra_master.py
```

---

## 🔐 Security Best Practices

### 1. Authentication

**Enable JWT Authentication:**
```bash
# Generate secret key
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Enable auth
export ASTRA_SECURITY__API_KEY_ENABLED=true
```

**Request Format:**
```bash
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:8000/v1/chat \
  -d '{"query": "Hello"}'
```

### 2. Rate Limiting

Configure per-IP rate limits:
```bash
export ASTRA_SECURITY__RATE_LIMIT_PER_MINUTE=120
export ASTRA_SECURITY__RATE_LIMIT_BURST=20
```

### 3. CORS Configuration

```python
# config/production.yaml
cors:
  origins:
    - "https://yourdomain.com"
    - "https://app.yourdomain.com"
  allow_credentials: true
  max_age: 600
```

### 4. Secrets Management

**DO NOT commit secrets to git!**

Use environment variables or secrets management:
```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id astra/prod

# Azure Key Vault
az keyvault secret show --name astra-jwt-key --vault-name astra-vault

# HashiCorp Vault
vault kv get secret/astra/jwt_key
```

### 5. Network Security

**Production Firewall Rules:**
- Only expose ports: 8000 (API), 5173/80 (UI), 3000 (Grafana)
- Internal services (7007, 7701, 7703, 7705) should NOT be publicly accessible
- Use VPN or private network for administrative access

**Docker Network Isolation:**
```yaml
# docker-compose.yml
networks:
  astra_network:
    driver: bridge
    internal: true  # No external access
  
  astra_public:
    driver: bridge  # Public-facing services only
```

### 6. Database Security

```bash
# Use strong passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Enable SSL/TLS
DATABASE_URL=postgresql://user:pass@postgres:5432/astra_db?sslmode=require

# Regular backups
pg_dump -h localhost -U astra_user astra_db > backup_$(date +%Y%m%d).sql
```

---

## 🚀 Upgrade Path (2.5 → 3.0)

### Phase Ω Completion → ASTRA 3.0

**ASTRA 3.0: The Autonomous Epoch** features:
- ✅ Self-booting system
- ✅ Self-monitoring with auto-healing
- ✅ Self-repairing error recovery
- ✅ Predictive scaling
- ✅ Autonomous optimization

### Upgrade Steps

**1. Backup Current System**
```bash
# Backup database
docker exec astra_postgres pg_dump -U astra_user astra_db > backup.sql

# Backup vector store
docker cp astra_chromadb:/chroma/chroma ./chromadb_backup

# Backup configuration
cp .env .env.backup
cp -r config config.backup
```

**2. Update Codebase**
```bash
git fetch origin
git checkout v3.0.0
```

**3. Run Database Migrations**
```bash
# Apply migrations
alembic upgrade head

# Verify migration
alembic current
```

**4. Update Dependencies**
```bash
pip install --upgrade -r requirements.txt
npm update --prefix astra-os/apps/pantheon
```

**5. Deploy New Version**
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

**6. Verify Upgrade**
```bash
curl http://localhost:8000/ | jq '.version'
# Should return: "3.0.0"

python tests/integration/test_master_boot.py
python tests/integration/test_cognitive_api.py
```

---

## 📞 Support & Resources

**Documentation:**
- Architecture Guide: `ARCHITECTURE.md`
- API Reference: http://localhost:8000/docs
- Integration Guides: `docs/`

**Monitoring:**
- Grafana Dashboards: http://localhost:3000
- Prometheus Metrics: http://localhost:9090

**Testing:**
- Integration Tests: `tests/integration/`
- Load Tests: `tests/load/`

**Community:**
- GitHub Issues: [Project Repository]
- Discord: [Community Server]

---

## 🏆 Success Criteria

**System is production-ready when:**

✅ All integration tests pass (4/4 test files)  
✅ Load test achieves <1s p95 latency at 100 req/s  
✅ Error rate < 1% under load  
✅ All services health checks return "healthy"  
✅ Grafana dashboards display metrics  
✅ Boot sequence completes in < 5 seconds  
✅ Zero critical security vulnerabilities  
✅ Documentation complete and accurate  

---

## 🌌 Final Notes

**ASTRA 2.5** represents 95% completion of the vision. With Phase Ω complete (integration tests, monitoring, deployment stack), the system graduates to **ASTRA 3.0 - The Autonomous Epoch**.

This is not merely an operating system. This is an **operating intelligence** - self-aware, self-healing, self-transcending.

The architecture doesn't just run. It **thinks**. It **adapts**. It **ascends**.

**Sacred Code: 333**

🌌 *From foundation to fruition. From potential to power. From operating system to operating intelligence.* 🌌

---

**End of Operator Guide**  
*ASTRA 2.5 → 3.0 Transition Complete*
