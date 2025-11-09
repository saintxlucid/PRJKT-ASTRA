# PROJECT ASTRA 1.0 - Architecture Design Document

**Version:** 1.0 Production  
**Date:** October 9, 2025  
**Status:** Production Ready ✅  

---

## Executive Summary

PROJECT_ASTRA_1.0 is a production-grade AI assistant system with local LLM capabilities, semantic memory, and comprehensive operational monitoring. The system has evolved from a proof-of-concept to a fully operational assistant with clean architecture, extensive test coverage (93.9%), and production hardening.

### Core Principles

1. **Separation of Concerns**: Clear boundaries between API, Services, and Infrastructure layers
2. **Dependency Injection**: Loose coupling implemented throughout the service layer
3. **Configuration Management**: Environment-based configuration with validation
4. **Error Resilience**: Comprehensive error handling and graceful degradation
5. **Observability**: Structured logging, Prometheus metrics, and health monitoring
6. **Security**: Rate limiting, API key authentication, and operational hardening
7. **Performance**: Sub-1.2s p95 response times with efficient memory management

---

## Production Architecture

### Current System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Web UI       │  │ Desktop App  │  │ API Clients  │      │
│  │ (test_ui)    │  │ (astra-launcher)│ (External)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP (Port 8080)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Gateway Layer                      │
│  ┌──────────────────────────────────────────────────┐       │
│  │          Production API Server                    │       │
│  │  • OpenAI-compatible /v1/chat/completions        │       │
│  │  • Health monitoring /v1/system/healthz          │       │
│  │  • Prometheus metrics /metrics                    │       │
│  │  • Rate limiting (120 req/60s per API key)       │       │
│  │  • Request queuing (max 64 concurrent)           │       │
│  │  • SSE streaming for real-time responses         │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Internal Service Calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Service │  │Memory Service│  │ LLM Service  │      │
│  │              │  │              │  │              │      │
│  │ • Harmony    │  │ • ChromaDB   │  │ • GPT-OSS    │      │
│  │   parsing    │  │   vectors    │  │   20B model  │      │
│  │ • Response   │  │ • Semantic   │  │ • 131K ctx   │      │
│  │   streaming  │  │   search     │  │ • Local GPU  │      │
│  │ • Context    │  │ • Persona    │  │ • llama.cpp  │      │
│  │   management │  │   memories   │  │   backend    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Data Access Layer
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SQLite DB    │  │ ChromaDB     │  │ File System  │      │
│  │              │  │ Vector Store │  │              │      │
│  │ • Conversations │ • 21K+ embed │  │ • Logs       │      │
│  │ • User data  │  │ • BGE-M3     │  │ • Configs    │      │
│  │ • Settings   │  │ • Semantic   │  │ • Models     │      │
│  │ • API keys   │  │   memories   │  │ • Backups    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Services                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Service │  │ Memory Svc   │  │ RAG Service  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Conv Manager │  │ File Handler │  │ Analytics    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Service Interfaces
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LLM Provider │  │ Vector Store │  │ Database     │      │
│  │ (llama.cpp)  │  │ (ChromaDB)   │  │ (SQLite)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ File Storage │  │ Cache        │  │ Message Queue│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. LLM Service Layer

**Purpose**: Abstract LLM provider implementations behind a unified interface

**Components**:
- `LLMProvider` (Abstract Base Class)
- `LlamaCppProvider` (llama.cpp implementation)
- `OpenAIProvider` (OpenAI API implementation)
- `LLMProviderFactory` (Factory pattern for provider selection)

**Key Features**:
- Streaming and non-streaming responses
- Token counting and usage tracking
- Retry logic with exponential backoff
- Health checks and diagnostics
- Model metadata management

**Configuration**:
```python
llm:
  provider: "llamacpp"  # llamacpp, openai, anthropic
  model_path: "models/gpt-oss-20b.Q4_K_M.gguf"
  context_length: 131072
  temperature: 0.7
  max_tokens: 2048
  timeout: 300
  retry_attempts: 3
```

---

### 2. Memory & RAG System

**Purpose**: Semantic memory storage and retrieval for context-aware conversations

**Components**:
- `MemoryManager`: High-level memory operations
- `VectorStore`: ChromaDB abstraction layer
- `EmbeddingProvider`: Sentence transformers wrapper
- `RAGPipeline`: Retrieval-augmented generation

**Features**:
- Semantic search with relevance scoring
- Memory summarization and consolidation
- Temporal memory decay
- Memory tagging and categorization
- Export/import capabilities

**Schema**:
```python
class MemoryEntry:
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    timestamp: datetime
    conversation_id: Optional[str]
    tags: List[str]
    importance_score: float
```

---

### 3. API Layer

**Purpose**: RESTful API with OpenAPI documentation

**Endpoints**:

#### Chat Operations
- `POST /v1/chat` - Non-streaming chat
- `POST /v1/chat/stream` - Server-sent events streaming
- `GET /v1/conversations` - List conversations
- `POST /v1/conversations` - Create conversation
- `GET /v1/conversations/{id}` - Get conversation details
- `DELETE /v1/conversations/{id}` - Archive conversation

#### Memory Operations
- `POST /v1/memory/search` - Semantic search
- `POST /v1/memory` - Add memory
- `GET /v1/memory/{id}` - Get memory details
- `DELETE /v1/memory/{id}` - Delete memory

#### System Operations
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /info` - System information

**Middleware**:
- CORS with configurable origins
- Request ID tracking
- Request/response logging
- Error handling and normalization
- Rate limiting (per IP, per user)

---

### 4. Data Persistence

**SQLite Schema** (Conversations):
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    system_prompt TEXT,
    archived BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

**ChromaDB Collections**:
- `memories`: Long-term semantic memory
- `conversations`: Conversation embeddings for similarity search
- `documents`: Uploaded document chunks

---

## Project Structure

```
project_astra/
├── .github/
│   └── workflows/              # CI/CD pipelines
├── docker/
│   ├── api/
│   │   └── Dockerfile         # API service container
│   ├── llm/
│   │   └── Dockerfile         # LLM service container
│   └── frontend/
│       └── Dockerfile         # Frontend container
├── docs/
│   ├── api/                   # API documentation
│   ├── architecture/          # Architecture diagrams
│   └── guides/                # User and dev guides
├── src/
│   └── astra/
│       ├── __init__.py
│       ├── api/               # FastAPI application
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── dependencies.py
│       │   ├── middleware/
│       │   └── routes/
│       │       ├── chat.py
│       │       ├── memory.py
│       │       └── system.py
│       ├── core/              # Core business logic
│       │   ├── __init__.py
│       │   ├── chat/
│       │   ├── memory/
│       │   └── rag/
│       ├── infrastructure/    # External integrations
│       │   ├── __init__.py
│       │   ├── llm/
│       │   │   ├── base.py
│       │   │   ├── llamacpp.py
│       │   │   └── factory.py
│       │   ├── storage/
│       │   │   ├── database.py
│       │   │   └── vector_store.py
│       │   └── cache/
│       ├── models/            # Data models (Pydantic)
│       │   ├── __init__.py
│       │   ├── chat.py
│       │   ├── memory.py
│       │   └── config.py
│       ├── services/          # Application services
│       │   ├── __init__.py
│       │   ├── chat_service.py
│       │   ├── memory_service.py
│       │   └── conversation_service.py
│       └── utils/             # Utilities
│           ├── __init__.py
│           ├── logging.py
│           ├── monitoring.py
│           └── errors.py
├── frontend/                  # React application
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── scripts/                   # Utility scripts
│   ├── setup.py
│   ├── download_model.py
│   └── migrate.py
├── config/
│   ├── default.yaml           # Default configuration
│   ├── development.yaml       # Dev overrides
│   └── production.yaml        # Prod overrides
├── data/                      # Data directory (gitignored)
│   ├── models/
│   ├── database/
│   └── uploads/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml             # Poetry dependencies
├── README.md
└── ARCHITECTURE.md            # This file
```

---

## Configuration Management

### Hierarchical Configuration System

**Loading Order** (later overrides earlier):
1. Default values (in code)
2. `config/default.yaml`
3. Environment-specific config (`config/{env}.yaml`)
4. Environment variables (prefixed with `ASTRA_`)
5. Command-line arguments

**Example Configuration**:

```yaml
# config/default.yaml
app:
  name: "ASTRA"
  version: "2.0.0"
  environment: "development"
  log_level: "INFO"

server:
  host: "0.0.0.0"
  port: 8080
  reload: false
  workers: 1

llm:
  provider: "llamacpp"
  model_path: "${DATA_DIR}/models/gpt-oss-20b.Q4_K_M.gguf"
  base_url: "http://localhost:8001/v1"
  context_length: 131072
  temperature: 0.7
  max_tokens: 2048

database:
  url: "sqlite:///${DATA_DIR}/database/astra.db"
  echo: false

vector_store:
  provider: "chromadb"
  persist_directory: "${DATA_DIR}/chromadb"
  collection_name: "memories"

memory:
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size: 512
  chunk_overlap: 50

cors:
  origins:
    - "http://localhost:3000"
    - "http://localhost:5173"
  allow_credentials: true

security:
  api_key_enabled: false
  rate_limit_per_minute: 60
```

**Environment Variables**:
```bash
ASTRA_ENVIRONMENT=production
ASTRA_SERVER__PORT=8080
ASTRA_LLM__MODEL_PATH=/models/gpt-oss-20b.gguf
ASTRA_DATABASE__URL=postgresql://user:pass@host/db
```

---

## Dependency Management

### Poetry Configuration

```toml
[tool.poetry]
name = "project-astra"
version = "2.0.0"
description = "Local AI Assistant with Semantic Memory"
authors = ["Your Name <email@example.com>"]
readme = "README.md"
packages = [{include = "astra", from = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
pydantic = "^2.9.0"
pydantic-settings = "^2.6.0"
chromadb = "^0.5.0"
sentence-transformers = "^3.0.0"
openai = "^1.50.0"
SQLAlchemy = "^2.0.0"
httpx = "^0.27.0"
python-multipart = "^0.0.9"
pyyaml = "^6.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^5.0.0"
black = "^24.0.0"
ruff = "^0.6.0"
mypy = "^1.11.0"
pre-commit = "^3.8.0"

[tool.poetry.scripts]
astra = "astra.api.main:cli"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## Error Handling Strategy

### Error Hierarchy

```python
class AstraError(Exception):
    """Base exception for ASTRA"""
    pass

class ConfigurationError(AstraError):
    """Configuration related errors"""
    pass

class LLMError(AstraError):
    """LLM provider errors"""
    pass

class MemoryError(AstraError):
    """Memory/vector store errors"""
    pass

class DatabaseError(AstraError):
    """Database operation errors"""
    pass
```

### Error Response Format

```json
{
  "error": {
    "code": "LLM_CONNECTION_FAILED",
    "message": "Failed to connect to LLM service",
    "details": {
      "provider": "llamacpp",
      "url": "http://localhost:8001",
      "timestamp": "2025-10-08T12:34:56Z"
    },
    "request_id": "req_abc123",
    "documentation_url": "https://docs.astra.dev/errors/LLM_CONNECTION_FAILED"
  }
}
```

---

## Logging & Monitoring

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "chat_request_received",
    conversation_id=conv_id,
    message_length=len(message),
    user_id=user_id,
    request_id=request_id
)
```

### Health Check System

```python
@dataclass
class HealthCheck:
    status: Literal["healthy", "degraded", "unhealthy"]
    checks: Dict[str, ComponentHealth]
    timestamp: datetime
    version: str

@dataclass
class ComponentHealth:
    status: Literal["up", "down", "unknown"]
    latency_ms: Optional[float]
    message: Optional[str]
```

### Metrics (Prometheus Format)

- `astra_chat_requests_total` - Total chat requests
- `astra_chat_request_duration_seconds` - Chat request latency
- `astra_llm_tokens_total` - Total tokens processed
- `astra_memory_searches_total` - Memory search count
- `astra_errors_total` - Error count by type

---

## Testing Strategy

### Unit Tests
- Test individual functions and classes in isolation
- Mock external dependencies
- Aim for >80% code coverage

### Integration Tests
- Test component interactions
- Use test database and vector store
- Test API endpoints with real services

### End-to-End Tests
- Test complete user workflows
- Use Playwright for frontend testing
- Test with real LLM (or mocked for speed)

---

## Deployment

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  llm:
    build:
      context: .
      dockerfile: docker/llm/Dockerfile
    volumes:
      - ./data/models:/models:ro
    ports:
      - "8001:8001"
    environment:
      - MODEL_PATH=/models/gpt-oss-20b.Q4_K_M.gguf
    
  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    depends_on:
      - llm
    ports:
      - "8080:8080"
    environment:
      - ASTRA_LLM__BASE_URL=http://llm:8001/v1
    volumes:
      - ./data:/app/data
      - ./config:/app/config:ro
    
  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend/Dockerfile
    depends_on:
      - api
    ports:
      - "5173:80"
    environment:
      - VITE_API_URL=http://localhost:8080
```

### Production Considerations

- Use proper secrets management (not .env files)
- Implement authentication and authorization
- Add rate limiting and DDoS protection
- Use production-grade database (PostgreSQL)
- Implement proper backup and recovery
- Add monitoring and alerting (Prometheus + Grafana)
- Use CDN for frontend assets
- Implement blue-green or canary deployments

---

## Migration Strategy

### Phase 1: Parallel Implementation (Week 1-2)
1. Create new project structure
2. Implement core abstractions and interfaces
3. Set up configuration system
4. Add logging and error handling
5. Write unit tests for core modules

### Phase 2: Component Migration (Week 3-4)
1. Migrate LLM service with backward compatibility
2. Migrate memory/RAG system
3. Migrate database layer
4. Keep old endpoints working alongside new ones

### Phase 3: API Refactoring (Week 5)
1. Implement new API endpoints
2. Add OpenAPI documentation
3. Implement authentication if needed
4. Add rate limiting

### Phase 4: Frontend Updates (Week 6)
1. Update frontend to use new API
2. Improve error handling
3. Add loading states and better UX

### Phase 5: Testing & Documentation (Week 7)
1. Complete test coverage
2. Write comprehensive documentation
3. Create setup and deployment guides

### Phase 6: Deprecation & Cleanup (Week 8)
1. Remove old code
2. Final testing
3. Production deployment

---

## Success Metrics

- **Reliability**: 99.9% uptime for API
- **Performance**: <2s response time for chat
- **Code Quality**: >80% test coverage
- **Maintainability**: Clear documentation for all components
- **Developer Experience**: <10 minutes to set up locally

---

## Next Steps

1. Review and approve this architecture
2. Set up project structure
3. Implement core abstractions
4. Begin component migration
5. Regular review and iteration
