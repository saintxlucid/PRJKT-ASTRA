# 🚀 ASTRA OS — 5-Minute Quickstart

Get ASTRA running locally in 5 minutes.

## Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+**
- **Docker & Docker Compose** (for production deployment)
- **Git**

## Installation

### 1. Clone Repository

```bash
git clone <repository_url>
cd PROJECT_ASTRA_1.0
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

## Running ASTRA (Development Mode)

### Option A: Docker Compose (Recommended)

Simplest way to run the full stack:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Access:
- **Master API**: http://localhost:8000
- **Pantheon UI**: http://localhost:5173
- **Grafana**: http://localhost:3001 (admin/astra)
- **Prometheus**: http://localhost:9090

### Option B: Manual (Individual Services)

**Terminal 1: Master API**
```bash
python astra_master.py
```

**Terminal 2: Pantheon UI**
```bash
cd astra-os/apps/pantheon
npm run dev
```

**Terminal 3: Memory Service (Optional)**
```bash
cd astra-os/services/memory
python server.py
```

## Verify Installation

### Check System Status

```bash
# System info
curl http://localhost:8000/

# Boot status (9 phases)
curl http://localhost:8000/v1/boot/status

# Cognitive system
curl http://localhost:8000/v1/cognitive/status

# Agent system
curl http://localhost:8000/v1/agent/status
```

### Run Integration Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx anyio

# Run smoke tests
pytest tests/integration/test_smoke.py -v

# Run full integration suite
pytest tests/integration/ -v
```

### Access UI

Open browser: http://localhost:5173

Features:
- **Chat Interface**: Interact with ASTRA's cognitive system
- **Agent Panel**: Monitor autonomous agent tasks
- **Memory Browser**: Explore semantic memory
- **System Dashboard**: View boot status and metrics

## Quick Chat Test

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is ASTRA?", "stream": false}'
```

## Next Steps

- **Production Deployment**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **API Reference**: Visit http://localhost:8000/docs
- **Architecture**: See [ASTRA_OPERATOR_GUIDE.md](../ASTRA_OPERATOR_GUIDE.md)
- **Performance Testing**: `locust -f ops/locustfile.py --host http://localhost:8000`

## Troubleshooting

**Port already in use:**
```bash
# Find process using port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Find process using port 8000 (Linux/macOS)
lsof -i :8000
kill -9 <pid>
```

**Dependencies missing:**
```bash
# Update pip
python -m pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Docker issues:**
```bash
# Reset Docker environment
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

## Configuration

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=sqlite:///./data/astra.db

# LLM
ASTRA_LLM__MODEL_PATH=./data/models/gpt-oss-20b.Q4_K_M.gguf

# Services
MEMORY_SERVICE_URL=http://localhost:7007
SIGIL_GATE_URL=http://localhost:7701
SUPERVISOR_URL=http://localhost:7703

# Logging
ASTRA_LOG_LEVEL=INFO
```

---

**Ready to ascend!** 🌌

For production deployment with PostgreSQL, Prometheus, and Grafana, see [DEPLOYMENT.md](./DEPLOYMENT.md).
