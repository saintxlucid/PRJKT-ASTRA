# ASTRA Core - Repository Index

**Audit Date**: 2025-11-01  
**Auditor**: Senior Staff+ SRE  
**Repository**: X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)

---

## Repository Overview

ASTRA Core is a production-ready FastAPI-based RAG (Retrieval-Augmented Generation) system with comprehensive memory management, multi-modal capabilities, and enterprise-grade observability. The system integrates vector databases, LLM backends (llama.cpp/vLLM), and provides SSE streaming with sophisticated backpressure handling.

### Key Characteristics
- **Primary Stack**: Python 3.x, FastAPI, Uvicorn
- **Vector Stores**: ChromaDB, Qdrant, SimpleVecDB
- **LLM Backends**: llama.cpp, vLLM, transformers
- **Orchestration**: Kubernetes, Docker Compose
- **Observability**: Prometheus, Grafana, structlog
- **Testing**: pytest, Locust, K6

---

## Language & LOC Distribution

```
Language         Files    Approx LOC   % of Codebase
================================================
Python           21,085   ~500,000     72%
JSON             19,313   ~150,000     21%
YAML/Docker      500+     ~15,000      2%
Markdown         654      ~50,000      7%
C/C++/CUDA       750+     ~40,000      5%
Other (HTML/JS)  1,500+   ~25,000      3%
================================================
Total            ~43,000+ ~780,000     100%
```

**Note**: LOC estimates based on file counts and typical file sizes. Vendor code (`.venv/`, `__pycache__/`, `.git/`, large model files) excluded.

---

## Repository Structure (3 Levels)

```
PROJECT_ASTRA_1.0 (ASTRA_CORE)/
├── astra_core.py                    # Main FastAPI server (516 lines)
├── astra_launcher.py                # Application launcher
├── go_live_check.py                 # Pre-deployment validation suite
├── locustfile.py                    # Load testing (Locust)
├── simple_load_test.py              # Async load test tool
├── test_rate_limiting.py            # Rate limiter validation
├── requirements.txt                 # Python dependencies
├── docker-compose.yml               # Local dev orchestration
├── Dockerfile                       # Container definition
├── pytest.ini                       # Test configuration
├── pyproject.toml                   # Python project metadata
├── .env.example                     # Environment template
│
├── src/astra/                       # Core application code
│   ├── api/                         # FastAPI routes
│   │   ├── app.py                   # Application factory
│   │   ├── health.py                # Health check endpoints
│   │   └── answer_api.py            # Q&A endpoints
│   ├── core/                        # Business logic
│   │   ├── initialization.py        # App initialization
│   │   └── answer_api.py            # Answer processing
│   ├── rag/                         # RAG implementation
│   │   ├── rag_fusion.py            # RAG Fusion engine
│   │   ├── rag_streaming.py         # SSE streaming
│   │   ├── metrics.py               # Prometheus metrics
│   │   └── tokenization.py          # Token budget management
│   ├── services/                    # Service layer
│   │   ├── memory_service.py        # Memory operations
│   │   └── model_bridge.py          # LLM adapter
│   ├── infrastructure/              # Infrastructure layer
│   │   └── storage/
│   │       └── vector_store.py      # Vector DB abstraction
│   ├── vector_stores.py             # VectorDB implementations
│   ├── ingest.py                    # Document ingestion
│   └── memory_engine.py             # Memory management
│
├── k8s/                             # Kubernetes manifests
│   ├── namespace.yaml               # Namespace definition
│   ├── service.yaml                 # Service definitions
│   ├── ingress.yaml                 # Ingress configuration
│   ├── hpa.yaml                     # HorizontalPodAutoscaler
│   ├── pvc.yaml                     # PersistentVolumeClaim
│   ├── networkpolicy-deny-all.yaml  # Network security
│   ├── prometheusrule-astrasafety.yaml # Alert rules (critical)
│   ├── servicemonitor-bridge-docs.yaml # Prometheus scraping
│   ├── probe-astra.yaml             # Blackbox exporter probes
│   ├── canary/                      # Canary deployment
│   │   ├── canary-deployment.yaml   # Flagger-based canary
│   │   └── manual-canary.yaml       # Manual Istio canary
│   └── monitoring/                  # Monitoring configs
│       ├── servicemonitor.yaml      # Prometheus ServiceMonitor
│       └── grafana-dashboard.json   # Production dashboard
│
├── docs/                            # Documentation
│   ├── ENHANCEMENT_01_PROMETHEUS_METRICS.md  # Metrics guide (317 lines)
│   ├── CANARY_DEPLOYMENT_RUNBOOK.md # Deployment runbook (407 lines)
│   ├── PRODUCTION_PROMOTION_PLAN.md # Promotion procedures (300+ lines)
│   ├── BACKUP_AND_SECURITY.md       # Security/DR guide (600+ lines)
│   ├── QUICK_REFERENCE_CARD.md      # Quick commands
│   └── 🎯_PRODUCTION_READINESS_COMPLETE.md # Executive summary
│
├── tools/                           # Operational tools
│   ├── check_metrics.py             # Metrics viewer
│   ├── test_rate_limiting.py        # Rate limit tester
│   ├── memory_smoke.py              # Memory smoke test
│   ├── dataset_loader.py            # Dataset bootstrap
│   └── validate_production.py       # Production validator
│
├── tests/                           # Test suites
│   ├── test_app.py                  # Application tests
│   ├── test_rag_fusion.py           # RAG tests
│   ├── test_memory.py               # Memory engine tests
│   └── unit/                        # Unit tests
│
├── .github/workflows/               # CI/CD pipelines
│   ├── go-live-validation.yml       # Pre-prod validation gate
│   ├── adapter-rehearsal.yml        # Weekly adapter tests
│   └── ci.yml                       # Continuous integration
│
├── adapters/                        # Neural adapters (LoRA/QLoRA)
├── models/                          # Model weights (.gguf)
├── qdrant/                          # Qdrant vector DB data
├── logs/                            # Application logs
├── monitoring/                      # Prometheus/Grafana config
├── scripts/                         # Utility scripts
├── backup/                          # Backup automation (inferred)
└── audit/                           # THIS AUDIT OUTPUT
```

---

## Core Files Summary

### Production Server
| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `astra_core.py` | 516 | FastAPI server with rate limiting, metrics, circuit breakers | ✅ Production |
| `astra_launcher.py` | ~800 | Application launcher with health checks | ✅ Production |
| `go_live_check.py` | ~400 | Comprehensive pre-deployment validation | ✅ Complete |

### RAG & Memory
| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `src/astra/rag/rag_fusion.py` | ~600 | RAG Fusion engine with multi-query, reranking | ✅ Production |
| `src/astra/rag/rag_streaming.py` | ~400 | SSE streaming with backpressure | ✅ Production |
| `src/astra/services/memory_service.py` | ~300 | Memory CRUD operations | ✅ Production |
| `src/astra/vector_stores.py` | ~800 | Multi-backend vector store abstraction | ✅ Production |

### Testing & Validation
| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `locustfile.py` | 464 | Locust load tests with circuit breaker tests | ✅ Complete |
| `simple_load_test.py` | 156 | Async load test with percentiles | ✅ Complete |
| `test_rate_limiting.py` | ~150 | Rate limiter validation | ✅ Complete |
| `validate_production.py` | ~200 | Health check validation | ✅ Complete |

### Kubernetes & Deployment
| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `k8s/canary/canary-deployment.yaml` | ~200 | Flagger automated canary | ✅ Production-ready |
| `k8s/prometheusrule-astrasafety.yaml` | ~400 | Critical alert rules | ✅ Production-ready |
| `k8s/hpa.yaml` | ~50 | Auto-scaling config | ✅ Production-ready |
| `k8s/networkpolicy-deny-all.yaml` | ~30 | Network security | ✅ Production-ready |

---

## Key Directories

### `/src/astra/`
Core application logic organized in clean architecture layers:
- **api/**: FastAPI routes and request/response handling
- **core/**: Business logic and orchestration
- **rag/**: RAG Fusion, streaming, tokenization
- **services/**: Service layer (memory, models)
- **infrastructure/**: Data access (vector stores, caching)

### `/k8s/`
Complete Kubernetes deployment manifests:
- Base deployments, services, ingress
- Canary deployment strategies (Flagger + manual Istio)
- HPA with custom metrics (queue_depth)
- NetworkPolicies for security
- Prometheus monitoring (ServiceMonitor, PrometheusRules)
- PVC for persistent storage

### `/docs/`
Comprehensive operational documentation:
- Prometheus metrics implementation guide
- Canary deployment runbook (400+ lines)
- Production promotion plan with rollback procedures
- Backup & security guide with DR playbooks
- Compliance checklists (SOC 2, ISO 27001, GDPR, PCI DSS)

### `/tools/`
Operational tooling:
- Metrics visualization (`check_metrics.py`)
- Rate limiting validation (`test_rate_limiting.py`)
- Load testing (`simple_load_test.py`)
- Production validation (`validate_production.py`)

---

## Dependencies Summary

### Core Runtime
```python
fastapi>=0.95.0
uvicorn>=0.22.0
pydantic>=2.0.0
torch>=2.0.0
transformers>=4.30.0
sentence-transformers>=2.2.2
```

### Vector & Storage
```python
chromadb>=0.4.0
llama-cpp-python>=0.2.0
sqlalchemy>=2.0.0
asyncpg>=0.28.0  # PostgreSQL
redis>=4.5.0
```

### Observability
```python
prometheus-client>=0.17.0
structlog>=23.1.0
opentelemetry-api>=1.18.0
opentelemetry-sdk>=1.18.0
```

### Testing
```python
pytest>=7.3.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
locust
httpx>=0.24.0
```

---

## Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `requirements.txt` | Python dependencies | ✅ Present |
| `pyproject.toml` | Project metadata, tool configs | ✅ Present |
| `pytest.ini` | Test configuration | ✅ Present |
| `docker-compose.yml` | Local dev orchestration | ✅ Present |
| `Dockerfile` | Container definition | ✅ Present |
| `.env.example` | Environment template | ✅ Present |
| `config.yaml` | App configuration | ✅ Present |

---

## Branch & Version Info

```
Repository Path:  X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
Current Branch:   (detect via git)
Last Commit:      (detect via git log -1)
Tags:             (detect via git tag)
Default Branch:   main (assumed)
```

---

## Recent Activity

Based on file timestamps and documentation:
- **Last major work**: Production readiness validation (2025-11-01)
- **Recent additions**: 
  - Rate limiting with token bucket algorithm
  - Prometheus metrics enhancement (OpenMetrics 0.0.4)
  - Canary deployment manifests (Flagger + manual)
  - Comprehensive operational runbooks
- **Status**: All 8 production validation tasks complete (100%)

---

## Notable Patterns

### ✅ Strengths
- **Clean Architecture**: Clear separation of concerns (api → core → services → infrastructure)
- **Comprehensive Testing**: Unit tests, integration tests, load tests, pre-deployment validation
- **Production-Ready**: Rate limiting, circuit breakers, graceful shutdown, backpressure
- **Observability**: Prometheus metrics, structured logging, health endpoints
- **Documentation**: 2000+ lines of operational guides

### ⚠️ Areas for Attention
- **Large Codebase**: ~780k LOC total (needs focused analysis)
- **Multiple Vector Backends**: ChromaDB, Qdrant, SimpleVecDB (ensure consistent behavior)
- **Model Management**: Large model files (.gguf) - versioning and storage strategy needed
- **Test Coverage**: pytest present, need coverage % validation
- **Security Scans**: pip-audit/bandit not yet verified

---

## Next Steps

Refer to subsequent audit files:
- **01_EXEC_SUMMARY.md**: Executive summary with top risks and actions
- **02_ARCHITECTURE.md**: Component diagrams and data flows
- **03_ENDPOINTS.md**: API endpoint catalog
- **04_MEMORY_RAG.md**: RAG & memory system deep dive
- **05_NEURAL_ADAPTERS.md**: Model inventory and gating
- **06_DEVOPS_OBS.md**: DevOps, observability, SRE
- **07_SECURITY_PRIVACY.md**: Security posture analysis
- **08_TESTS_QUALITY.md**: Test coverage and quality metrics
- **09_RUNBOOKS.md**: Operational runbooks validation
- **10_NEXT_30_90.md**: Action plan with timelines
- **summary.json**: Machine-readable metrics

---

**Audit Status**: Index Complete  
**Next**: Executive Summary & Risk Assessment
