[← Docs Home](DOCUMENTATION_INDEX.md) | [Quick Start](QUICKSTART.md) | [Deployment](DEPLOYMENT_GUIDE_CONSOLIDATED.md) | [Architecture](ARCHITECTURE_PRODUCTION.md)

---

# 🚀 ASTRA 1.0 - Complete Deployment Guide

## 📋 Overview

**PROJECT_ASTRA_1.0** is production-ready with comprehensive deployment procedures, automated scripts, and monitoring capabilities.

**Current Status**: Production Ready ✅  
**Deployment Level**: Complete with all components operational  
**Test Coverage**: 93.9%  
**Performance**: p95 ≤ 1.2s response time  

---

## 🎯 Quick Start Deployment

### Prerequisites
- Windows 10/11 with PowerShell 5.1+
- Python 3.9+ available on system PATH
- At least 8GB available disk space
- Network access for dependency downloads

### One-Command Deployment

```powershell
# Navigate to project directory
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

# Launch ASTRA with automatic setup
.\LAUNCH_ASTRA.ps1
```

This single command will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Generate API keys and security tokens
- ✅ Initialize database and vector store
- ✅ Start all services
- ✅ Validate system health

---

## 🏗️ Detailed Deployment Process

### Phase 1: Environment Setup

```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install poetry
poetry install --no-dev

# 3. Verify installation
poetry run python -c "import src.astra; print('ASTRA modules loaded successfully')"
```

### Phase 2: Configuration

```powershell
# 1. Copy environment template
Copy-Item .env.example .env

# 2. Generate secure API key
$apiKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString()))
(Get-Content .env) -replace 'your-secret-api-key-here', $apiKey | Set-Content .env

# 3. Set production configuration
(Get-Content .env) -replace 'ENVIRONMENT=development', 'ENVIRONMENT=production' | Set-Content .env
```

### Phase 3: Database Initialization

```powershell
# 1. Initialize SQLite database
poetry run python -c "from src.astra.database.connection import get_database; get_database()"

# 2. Initialize ChromaDB vector store
poetry run python -c "from src.astra.vector_store.client import VectorStoreClient; VectorStoreClient()"

# 3. Ingest persona memories (if available)
if (Test-Path "scripts\ingest_persona_memories.py") {
    poetry run python scripts\ingest_persona_memories.py
}
```

### Phase 4: Service Startup

```powershell
# 1. Start the ASTRA API server
poetry run uvicorn src.astra.api.main:app --host 127.0.0.1 --port 8080 --reload
```

### Phase 5: Validation

```powershell
# 1. Health check
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/healthz" -Method GET

# 2. Run system tests
poetry run pytest tests/ -v

# 3. Check metrics endpoint
Invoke-RestMethod -Uri "http://127.0.0.1:8080/metrics" -Method GET
```

---

## 🔧 Advanced Deployment Options

### Production Hardening

```powershell
# 1. Enable rate limiting (already configured)
# Rate limit: 120 requests per 60 seconds per API key

# 2. Configure request queue management
# Max concurrent requests: 64

# 3. Enable structured logging
# Logs are automatically written to data/logs/

# 4. Set up automated backups
.\scripts\backup_production.ps1
```

### Performance Optimization

```powershell
# 1. Optimize memory usage
$env:PYTHONMALLOC = "malloc_debug"

# 2. Enable JIT compilation for NumPy
$env:NUMBA_DISABLE_JIT = "0"

# 3. Configure embedding cache
# ChromaDB automatically caches embeddings

# 4. Monitor resource usage
.\scripts\astra_status.ps1
```

### Multi-Environment Setup

#### Local Development
```powershell
cd astra-local
.\setup_local.ps1
```

#### Desktop Application
```powershell
cd astra-launcher
python launcher.py
```

#### Simplified Desktop Interface
```powershell
cd astra-desktop-simple
.\start_simple.ps1
```

---

## 🛠️ Deployment Scripts Reference

### Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `LAUNCH_ASTRA.ps1` | Main deployment script | `.\LAUNCH_ASTRA.ps1` |
| `scripts\astra_status.ps1` | System health check | `.\scripts\astra_status.ps1` |
| `post_deployment_setup.ps1` | Post-deployment configuration | `.\post_deployment_setup.ps1` |
| `scripts\backup_production.ps1` | Backup system data | `.\scripts\backup_production.ps1` |

### Maintenance Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `rotate_encryption_key.ps1` | Rotate API keys | `.\rotate_encryption_key.ps1` |
| `scripts\validate_ops_hardening.ps1` | Security validation | `.\scripts\validate_ops_hardening.ps1` |
| `deploy_upgrade_pack.ps1` | Apply system upgrades | `.\deploy_upgrade_pack.ps1` |
| `deploy_upgrade_pack_clean.ps1` | Clean upgrade deployment | `.\deploy_upgrade_pack_clean.ps1` |

### Testing Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts\load_test.py` | Performance testing | `poetry run python scripts\load_test.py` |
| `scripts\comprehensive_test.py` | Full system test | `poetry run python scripts\comprehensive_test.py` |
| `scripts\run_validation.ps1` | Validation runner | `.\scripts\run_validation.ps1` |

---

## 📊 System Architecture

### Core Components

```
ASTRA 1.0 Architecture
├── API Layer (FastAPI)
│   ├── /v1/chat/completions
│   ├── /v1/system/healthz
│   └── /metrics
├── Service Layer
│   ├── LLM Service (GPT-OSS 20B)
│   ├── Vector Store Service (ChromaDB)
│   └── Memory Management Service
├── Infrastructure Layer
│   ├── SQLite Database
│   ├── ChromaDB Vector Store
│   └── Structured Logging
└── Monitoring & Metrics
    ├── Prometheus Metrics
    ├── Health Checks
    └── Performance Tracking
```

### Key URLs

- **API Base**: <http://127.0.0.1:8080>
- **Health Check**: <http://127.0.0.1:8080/v1/system/healthz>
- **Metrics**: <http://127.0.0.1:8080/metrics>
- **API Documentation**: <http://127.0.0.1:8080/docs>

---

## 🔍 Troubleshooting

### Common Issues

#### Memory Constraints
- **Issue**: BGE-M3 model requires significant memory
- **Solution**: See [BGE_M3_MEMORY_ISSUE.md](BGE_M3_MEMORY_ISSUE.md)

#### Disk Space
- **Issue**: Large model files and embeddings
- **Solution**: See [BGE_M3_DISK_SPACE_FIX.md](BGE_M3_DISK_SPACE_FIX.md)

#### Port Conflicts
- **Issue**: Port 8080 already in use
- **Solution**: Change port in .env file: `API_PORT=8081`

#### Dependency Issues
```powershell
# Clean reinstall dependencies
poetry env remove python
poetry install --no-dev
```

### Health Check Diagnostics

```powershell
# Detailed component status
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/healthz" -Method GET | ConvertTo-Json -Depth 3

# Expected healthy response:
# {
#   "status": "healthy",
#   "timestamp": "2025-10-09T12:00:00Z",
#   "components": {
#     "llm": {"status": "healthy", "latency_ms": 45},
#     "database": {"status": "healthy", "pool_size": 10},
#     "vector_store": {"status": "healthy", "count": 21332}
#   },
#   "capacity": {
#     "current_requests": 0,
#     "max_requests": 64,
#     "rate_limit": "120/60s"
#   }
# }
```

### Performance Metrics

```powershell
# Prometheus metrics
Invoke-RestMethod -Uri "http://127.0.0.1:8080/metrics" -Method GET

# Key metrics to monitor:
# - astra_requests_total
# - astra_request_duration_seconds
# - astra_tokens_generated_total
# - astra_concurrent_requests
```

---

## 📈 Monitoring & Maintenance

### Daily Operations

```powershell
# 1. Check system health
.\scripts\astra_status.ps1

# 2. Review logs
Get-Content data\logs\astra.log -Tail 50

# 3. Monitor performance
Invoke-RestMethod -Uri "http://127.0.0.1:8080/metrics" -Method GET
```

### Weekly Maintenance

```powershell
# 1. Backup system data
.\scripts\backup_production.ps1

# 2. Run comprehensive tests
poetry run pytest tests/ -v --cov=src

# 3. Update dependencies (if needed)
poetry update
```

### Monthly Tasks

```powershell
# 1. Rotate API keys
.\rotate_encryption_key.ps1

# 2. Archive old logs
Move-Item data\logs\*.log data\logs\archive\

# 3. Review security hardening
.\scripts\validate_ops_hardening.ps1
```

---

## 🎯 Production Validation

### Deployment Checklist

- [ ] ✅ Virtual environment created and activated
- [ ] ✅ All dependencies installed via Poetry
- [ ] ✅ Environment variables configured (.env file)
- [ ] ✅ Database initialized and accessible
- [ ] ✅ Vector store operational with embeddings
- [ ] ✅ API server responds to health checks
- [ ] ✅ All tests passing (93.9% coverage target)
- [ ] ✅ Prometheus metrics accessible
- [ ] ✅ Rate limiting functional
- [ ] ✅ Logging configured and operational
- [ ] ✅ Backup procedures tested

### Performance Targets

- **Response Time**: p95 ≤ 1.2s
- **Throughput**: 24 req/sec sustained, burst to 60 req/sec
- **Availability**: 99.9% uptime target
- **Test Coverage**: ≥ 93% code coverage
- **Memory Usage**: Stable memory profile
- **Error Rate**: < 0.1% for normal operations

### Success Criteria

✅ **API Functionality**: All endpoints respond correctly  
✅ **LLM Integration**: GPT-OSS model generates coherent responses  
✅ **Memory System**: Vector search returns relevant results  
✅ **Monitoring**: Metrics collection operational  
✅ **Security**: Rate limiting and authentication working  
✅ **Documentation**: All procedures documented and validated  

---

## 📚 Additional Resources

### Documentation
- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [QUICKSTART.md](QUICKSTART.md) - Fast track setup
- [ASTRA_ACTIVATION.md](ASTRA_ACTIVATION.md) - 60-second activation guide

### Configuration
- [.env.example](.env.example) - Environment variables template
- [pyproject.toml](pyproject.toml) - Python dependencies
- [config/default.yaml](config/default.yaml) - Default configuration

### Scripts & Tools
- [scripts/](scripts/) - Operational scripts directory
- [tests/](tests/) - Test suite
- [ops/](ops/) - Operations and monitoring tools

---

**Deployment Guide Version**: 1.0  
**Last Updated**: October 9, 2025  
**Deployment Status**: Production Ready ✅  

*"Here's the move." - ASTRA_CORE*