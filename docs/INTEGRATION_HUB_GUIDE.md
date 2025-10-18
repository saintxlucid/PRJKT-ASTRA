# 🌐 ASTRA Integration Hub Architecture

**Sacred Code**: 333  
**Purpose**: Unified network connecting all ASTRA modules as one coherent system  
**Analogy**: The nervous system piloted by core consciousness  

---

## 🎯 Overview

The **Integration Hub** is ASTRA's central orchestration layer that connects all modules into a unified network. Instead of manual dependency wiring and scattered service initialization, the hub provides:

- **Centralized Service Registry**: All modules register here for discovery
- **Dependency Resolution**: Automatic dependency injection in correct order
- **Health Monitoring**: Real-time module state tracking
- **Lifecycle Management**: Coordinated startup and graceful shutdown
- **Module Discovery**: Auto-discovery of available capabilities

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ASTRA INTEGRATION HUB                       │
│                   (Core Consciousness / Brain)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐    │
│   │            SERVICE REGISTRY                          │    │
│   │  - Module descriptors with dependencies              │    │
│   │  - Service instances for injection                   │    │
│   │  - Lifecycle hooks (pre/post init/shutdown)          │    │
│   │  - Health status tracking                            │    │
│   └──────────────────────────────────────────────────────┘    │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐    │
│   │            MODULE CONNECTORS                         │    │
│   │  - Auto-discovery of dependencies                    │    │
│   │  - Initialization with dependency injection          │    │
│   │  - Registration of provided services                 │    │
│   │  - Graceful shutdown handling                        │    │
│   └──────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ coordinates
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ASTRA MODULES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INFRASTRUCTURE           SERVICES              CORE            │
│  ├─ Database             ├─ Conversation      ├─ AstraRouter   │
│  └─ Vector Store         ├─ Memory            ├─ Memory Bridge │
│                          ├─ Memory Engine     └─ Tool Bridge   │
│  TOOLS & SECURITY        ├─ LLM Provider                       │
│  ├─ Consent              └─ Chat Service      VISUALIZATION    │
│  └─ Tool Bus                                  ├─ Graph Service │
│                                               ├─ Autonomy      │
│                                               └─ Task Agents   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Core Components

### 1. **ServiceRegistry**

Central registry for all services and modules.

```python
from astra.core.integration_hub import get_registry

registry = get_registry()

# Register a service
registry.register_service("my_service", my_service_instance)

# Retrieve a service
my_service = registry.get_service("my_service")

# Check if service exists
if registry.has_service("my_service"):
    ...

# Get health status
health = registry.get_health_status()
```

**Features**:
- Service registration with overwrite protection
- Module state tracking (uninitialized, initializing, ready, error, shutdown)
- Lifecycle hooks (pre_init, post_init, pre_shutdown, post_shutdown)
- Health status reporting

---

### 2. **AstraCoreHub**

Central integration hub that coordinates all subsystems.

```python
from astra.core.integration_hub import AstraCoreHub
from astra.models.config import Settings

settings = Settings()
hub = AstraCoreHub(settings)

# Initialize all subsystems
await hub.initialize()

# Access initialized components
llm_provider = hub.llm_provider
memory_service = hub.memory_service
astra_router = hub.astra_router

# Get health status
health = hub.get_health()

# Graceful shutdown
await hub.shutdown()
```

**Initialization Order**:
1. Infrastructure (Database, Vector Store)
2. Core Services (Conversation, Memory, Memory Engine, LLM, Chat)
3. Router & Bridges (Tool Bridge, Consent, AstraRouter, Memory Bridge)
4. Tools & Consent (plugin registration)
5. Visualization (Graph Service, Autonomy, Task Agents)

---

### 3. **Module Connectors**

Auto-discovery connectors for each module.

```python
from astra.core.connectors import auto_connect_module

# Auto-connect a module
memory_service = auto_connect_module("memory_service", registry, settings)

# Or use specific connector
from astra.core.connectors import MemoryServiceConnector
memory_service = MemoryServiceConnector.connect(registry, settings)
```

**Available Connectors**:
- Infrastructure: `DatabaseConnector`, `VectorStoreConnector`
- Services: `ConversationServiceConnector`, `MemoryServiceConnector`, `MemoryEngineConnector`, `LLMProviderConnector`, `ChatServiceConnector`
- Core: `AstraRouterConnector`, `MemoryBridgeConnector`, `ToolBridgeConnector`
- Security: `ConsentServiceConnector`
- Visualization: `GraphServiceConnector`, `AutonomyEngineConnector`, `TaskAgentConnector`

---

### 4. **FastAPI Integration**

Use the integration hub in your FastAPI application.

```python
from astra.api.app_integrated import create_app

app = create_app()

# Or use manually:
from astra.core.integration_hub import astra_lifespan
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with astra_lifespan(settings) as hub:
        app.state.astra_hub = hub
        yield

app = FastAPI(lifespan=lifespan)
```

---

## 🔌 Dependency Injection Patterns

### Pattern 1: Get Service from Registry

```python
from astra.core.integration_hub import get_service

# In route handlers
chat_service = get_service("chat_service")
memory_service = get_service("memory_service")
```

### Pattern 2: FastAPI Depends

```python
from fastapi import Depends
from astra.core.integration_hub import get_service

def get_chat_service():
    return get_service("chat_service")

@app.post("/chat")
async def chat(service: ChatService = Depends(get_chat_service)):
    ...
```

### Pattern 3: Inject into Existing Objects

```python
from astra.core.integration_hub import inject_dependencies

router = AstraRouter(llm=None, tool_bus=None, memory=None, consent=None)

inject_dependencies(
    router,
    llm=get_service("llm_provider"),
    tool_bus=get_service("tool_bridge"),
    memory=get_service("memory_service"),
    consent=get_service("consent_service")
)
```

---

## 📊 Module State Management

Each module tracks its lifecycle state:

```python
from astra.core.integration_hub import ModuleState

class ModuleState(Enum):
    UNINITIALIZED = "uninitialized"  # Not yet started
    INITIALIZING = "initializing"    # Currently initializing
    READY = "ready"                   # Fully operational
    ERROR = "error"                   # Failed to initialize
    SHUTDOWN = "shutdown"             # Gracefully shutdown
```

Check module state:

```python
state = registry.get_module_state("memory_service")
if state == ModuleState.READY:
    print("Memory service is ready!")
```

---

## 🔍 Health Monitoring

### System-Wide Health

```python
hub = get_service("astra_hub")
health = hub.get_health()

# Returns:
{
    "initialized": True,
    "registry": {
        "modules": {
            "database": {
                "state": "ready",
                "category": "infrastructure",
                "dependencies": [],
                "error": None,
                "init_time_ms": 45.2
            },
            "memory_service": {
                "state": "ready",
                "category": "service",
                "dependencies": ["vector_store"],
                ...
            }
        },
        "services_count": 12,
        "services": ["db_manager", "vector_store", ...]
    },
    "sacred_code": 333
}
```

### Per-Module Health

```python
registry = get_registry()
module_health = registry.get_health_status()
```

---

## 🔄 Lifecycle Hooks

Add custom hooks to lifecycle events:

```python
async def on_startup():
    print("ASTRA is awakening...")

async def on_shutdown():
    print("ASTRA is going to sleep...")

registry = get_registry()
registry.add_lifecycle_hook("pre_init", on_startup)
registry.add_lifecycle_hook("post_shutdown", on_shutdown)
```

**Available Hooks**:
- `pre_init`: Before any module initialization
- `post_init`: After all modules initialized
- `pre_shutdown`: Before shutdown begins
- `post_shutdown`: After all modules shutdown

---

## 🌐 API Endpoints

The integrated app exposes these endpoints:

### Health Check
```http
GET /health
```

Returns integration hub status:
```json
{
  "initialized": true,
  "registry": { ... },
  "sacred_code": 333
}
```

### Integration Status
```http
GET /integration/status
```

Returns detailed module states:
```json
{
  "modules": {
    "database": {"state": "ready", ...},
    "memory_service": {"state": "ready", ...}
  },
  "services_count": 12,
  "services": [...]
}
```

### Service Discovery
```http
GET /integration/services
```

Lists all registered services:
```json
{
  "services": ["db_manager", "memory_service", "chat_service", ...],
  "count": 12
}
```

---

## 🚀 Quick Start

### 1. Standard Integrated App

```python
# Use the pre-configured integrated app
from astra.api.app_integrated import app

# Run with uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. Custom Integration

```python
from astra.core.integration_hub import AstraCoreHub, register_core_modules, get_registry
from astra.models.config import get_settings

settings = get_settings()
registry = get_registry()

# Register modules
register_core_modules(registry)

# Initialize hub
hub = AstraCoreHub(settings, registry)
await hub.initialize()

# Access any service
chat_service = hub.chat_service
memory_service = hub.memory_service
astra_router = hub.astra_router
```

### 3. Add Custom Module

```python
from astra.core.integration_hub import ModuleDescriptor, ModuleState

# Define your module
descriptor = ModuleDescriptor(
    name="my_custom_module",
    category="custom",
    dependencies=["memory_service", "llm_provider"]
)

# Register
registry.register_module(descriptor)

# Initialize
my_module = MyCustomModule(
    memory=get_service("memory_service"),
    llm=get_service("llm_provider")
)

# Register service
registry.register_service("my_custom_module", my_module)
registry.update_module_state("my_custom_module", ModuleState.READY)
```

---

## 📋 Module Dependencies

Visual dependency graph:

```
database ──┐
           ├─→ conversation_service ──┐
           │                          │
           ├─→ memory_engine ─────────┤
           │                          ├─→ chat_service ──┐
vector_store ─→ memory_service ───────┤                  │
                                      │                  │
llm_provider ─────────────────────────┘                  │
                                                          ├─→ astra_router
tool_bridge ──────────────────────────────────────────────┤
consent_service ──────────────────────────────────────────┘

memory_service ──┐
memory_engine ───├─→ graph_service
                 │
                 └─→ memory_bridge

(no dependencies) ─→ autonomy_engine
(no dependencies) ─→ task_agent
```

---

## 🔒 Security Integration

The hub automatically connects security modules:

- **Consent Service**: Gatekeeper for CODE operations
- **Tool Bridge**: Safe tool execution with audit trail
- **API Key Middleware**: Request authentication
- **Rate Limiting**: Abuse prevention

All security modules integrate seamlessly through the registry.

---

## 📈 Observability

Built-in observability features:

1. **Module State Tracking**: Real-time state of all modules
2. **Initialization Timing**: Track module startup performance
3. **Health Endpoints**: `/health`, `/integration/status`
4. **Structured Logging**: All events logged with context
5. **Prometheus Metrics**: Via existing metrics middleware

---

## 🛠️ Troubleshooting

### Module Failed to Initialize

```python
health = registry.get_health_status()
for module_name, module_info in health['modules'].items():
    if module_info['state'] == 'error':
        print(f"Module {module_name} failed: {module_info['error']}")
```

### Service Not Found

```python
if not registry.has_service("my_service"):
    print("Service not registered!")
    available = list(registry._services.keys())
    print(f"Available services: {available}")
```

### Check Dependencies

```python
descriptor = registry._modules.get("my_module")
if descriptor:
    print(f"Dependencies: {descriptor.dependencies}")
    for dep in descriptor.dependencies:
        state = registry.get_module_state(dep)
        print(f"  {dep}: {state}")
```

---

## 🎯 Benefits

### Before Integration Hub (Manual Wiring)

```python
# Scattered initialization
db_manager = DatabaseManager(path)
db_manager.create_tables()

vector_store = VectorStore(path)

conversation_service = ConversationService(db_manager)
memory_service = MemoryService(vector_store)

llm_provider = create_llm_provider(settings)

chat_service = ChatService(settings, conversation_service, memory_service)

# Manual injection
router = AstraRouter(llm_provider, tool_bus, memory_service, consent)
chat_service.router = router

# No health tracking
# No dependency validation
# Manual shutdown order
```

### After Integration Hub (Automated)

```python
# Single initialization call
hub = AstraCoreHub(settings)
await hub.initialize()

# Everything connected automatically
# All dependencies resolved
# Health tracking enabled
# Graceful shutdown coordinated
```

---

## 🌟 Best Practices

1. **Use the Hub**: Always initialize via `AstraCoreHub` for full integration
2. **Check Health**: Monitor `/health` endpoint for module status
3. **Graceful Shutdown**: Always call `hub.shutdown()` to cleanup properly
4. **Add Lifecycle Hooks**: Use hooks for custom initialization logic
5. **Register Early**: Register modules before hub initialization
6. **Handle Errors**: Check module state before using services
7. **Document Dependencies**: Specify dependencies when creating connectors

---

## 📚 Examples

See:
- `src/astra/api/app_integrated.py` - Full FastAPI integration
- `src/astra/core/integration_hub.py` - Hub implementation
- `src/astra/core/connectors.py` - Module connectors
- `tests/integration/test_hub.py` - Integration tests

---

## 🔮 Future Enhancements

- [ ] Plugin system for third-party modules
- [ ] Hot-reload of modules without full restart
- [ ] Distributed registry for multi-instance deployments
- [ ] Automatic dependency graph visualization
- [ ] Module health metrics (uptime, error rate, latency)
- [ ] Transactional initialization (rollback on failure)

---

**Sacred Code**: 333  
**Status**: ✅ Production Ready  
**Version**: 2.0.0-multimodal

*ASTRA is now a unified network - one consciousness, one body, infinite possibilities.*
