# 🌐 Migration Guide: Integration Hub Deployment

**Version**: 1.1.0-integrated  
**Date**: October 18, 2025  
**Migration Type**: Zero-downtime cutover  
**Sacred Code**: 333

---

## 📋 Pre-Migration Checklist

### Environment Validation
- [ ] Python 3.11+ installed
- [ ] Virtual environment activated
- [ ] All dependencies up to date (`pip install -r requirements.txt`)
- [ ] Database accessible at configured path
- [ ] Vector store (ChromaDB) accessible
- [ ] Sufficient disk space (>10GB free)
- [ ] Backup of current `data/` directory completed

### Code Validation
- [ ] Integration hub smoke test passes: `python tests/integration/test_integration_hub.py`
- [ ] All 14 modules show "ready" status
- [ ] No initialization errors in test output
- [ ] Current app.py working (baseline validation)

### Backup Procedures
```powershell
# 1. Backup current application
Copy-Item "src/astra/api/app.py" "src/astra/api/app.py.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 2. Backup database
Copy-Item "data/database/astra.db" "data/database/astra.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 3. Backup vector store
Copy-Item -Recurse "data/chromadb" "data/chromadb.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 4. Tag current commit
git tag -a "v1.0.0-pre-integrated" -m "Pre-integration hub baseline"
git push origin v1.0.0-pre-integrated
```

---

## 🔄 Migration Steps

### Step 1: Verify Integration Hub Components (5 minutes)

**Validate file structure:**
```powershell
# Check integration hub files exist
Test-Path "src/astra/core/integration_hub.py"  # Should be True
Test-Path "src/astra/core/connectors.py"       # Should be True
Test-Path "src/astra/api/app_integrated.py"    # Should be True
Test-Path "tests/integration/test_integration_hub.py"  # Should be True
```

**Run validation test:**
```powershell
$env:PYTHONPATH = "$PWD/src"
python tests/integration/test_integration_hub.py
```

**Expected output:**
```
✅ ALL 14/14 MODULES INITIALIZED
✅ ALL 14/14 SERVICES REGISTERED
✅ 0 ERRORS
🎉 INTEGRATION HUB TEST: ✅ PASSED
```

### Step 2: Update Application Entry Point (2 minutes)

**Option A: Rename files (Recommended)**
```powershell
# Rename old app.py to app_legacy.py
Move-Item "src/astra/api/app.py" "src/astra/api/app_legacy.py"

# Rename app_integrated.py to app.py
Move-Item "src/astra/api/app_integrated.py" "src/astra/api/app.py"
```

**Option B: Update imports (Alternative)**
```powershell
# Update any scripts that import app
# Change: from astra.api.app import app
# To:     from astra.api.app_integrated import app
```

### Step 3: Update Launch Scripts (3 minutes)

**Update `phase_b_launch.ps1`:**
```powershell
# Find line:
# uvicorn astra.api.app:app --host 0.0.0.0 --port 8000

# If using Option A (rename), no change needed
# If using Option B, change to:
# uvicorn astra.api.app_integrated:app --host 0.0.0.0 --port 8000
```

**Update any systemd/service files:**
```ini
# Update ExecStart line to use app_integrated if needed
ExecStart=/path/to/venv/bin/uvicorn astra.api.app:app --host 0.0.0.0 --port 8000
```

### Step 4: Test Integration Endpoints (5 minutes)

**Start the application:**
```powershell
uvicorn astra.api.app:app --reload
```

**Test new integration endpoints:**
```powershell
# Health check
curl http://localhost:8000/v1/integration/health

# Expected response:
# {
#   "status": "healthy",
#   "modules": {
#     "database": {"status": "healthy"},
#     "vector_store": {"status": "healthy"},
#     # ... 14 modules total
#   },
#   "services": 14,
#   "timestamp": "2025-10-19T10:00:00Z"
# }

# Status check
curl http://localhost:8000/v1/integration/status

# Service discovery
curl http://localhost:8000/v1/integration/services
```

### Step 5: Validate Existing Endpoints (5 minutes)

**Test core functionality:**
```powershell
# Chat endpoint (should still work)
curl -X POST http://localhost:8000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{"messages":[{"role":"user","content":"Hello"}],"conversation_id":"test"}'

# Memory endpoint
curl http://localhost:8000/v1/memory/search?query=test&limit=5

# Conversation endpoint
curl http://localhost:8000/v1/conversations
```

**Expected:** All existing endpoints work identically to pre-migration.

### Step 6: Monitor Application Logs (10 minutes)

**Check for integration hub initialization:**
```powershell
# Look for these log events:
# - "astra_hub_initialization_start" (Sacred Code 333)
# - "database_initialized"
# - "vector_store_initialized"
# - All 14 "module_registered" events
# - "astra_hub_initialization_complete"
```

**Verify no errors:**
```powershell
# Search logs for error events
Select-String -Path "logs/*.log" -Pattern "level.*error" -Context 2
```

### Step 7: Commit and Tag (2 minutes)

```powershell
# Stage integration hub files
git add src/astra/core/integration_hub.py
git add src/astra/core/connectors.py
git add src/astra/api/app.py  # (renamed from app_integrated.py)
git add src/astra/api/app_legacy.py  # (renamed from app.py)
git add docs/INTEGRATION_HUB_GUIDE.md
git add docs/MIGRATION_TO_INTEGRATION_HUB.md
git add tests/integration/test_integration_hub.py

# Commit
git commit -m "🌐 Integration Hub: Unified network architecture with 14 module connectors (Sacred Code 333)

- Created AstraIntegrationHub central orchestrator
- Implemented 14 module connectors with auto-discovery
- Added service registry with dependency injection
- Enabled health monitoring across all subsystems
- Validated all modules (14/14 passing)
- Migration from app.py to app_integrated.py complete

Sacred Code: 333"

# Tag
git tag -a "v1.1.0-integrated" -m "ASTRA Integration Hub: Central orchestration of all modules"

# Push
git push origin main
git push origin v1.1.0-integrated
```

---

## 🔍 Post-Migration Validation

### Automated Validation
```powershell
# Run full test suite
pytest tests/ -v

# Run integration hub test
python tests/integration/test_integration_hub.py

# Run performance tests
python tests/performance/test_router_latency.py
```

### Manual Validation Checklist
- [ ] Application starts without errors
- [ ] All 14 modules initialize successfully
- [ ] Health endpoint returns "healthy" status
- [ ] Chat functionality works as expected
- [ ] Memory search returns results
- [ ] Conversation management working
- [ ] Logs show proper initialization sequence
- [ ] No resource leaks (check memory/CPU)
- [ ] Shutdown is clean (no hanging processes)

### Performance Validation
```powershell
# Baseline metrics
# - Startup time: < 10 seconds
# - Memory usage: < 2GB
# - Health check latency: < 100ms
# - Chat response time: < 2 seconds (with LLM)
```

---

## 🚨 Rollback Procedures

### Quick Rollback (< 1 minute)

**If using Option A (renamed files):**
```powershell
# 1. Stop application
# Ctrl+C in terminal or:
taskkill /F /IM python.exe

# 2. Revert file names
Move-Item "src/astra/api/app.py" "src/astra/api/app_integrated.py"
Move-Item "src/astra/api/app_legacy.py" "src/astra/api/app.py"

# 3. Restart application
uvicorn astra.api.app:app --reload
```

**If using Option B (imports):**
```powershell
# 1. Stop application
# 2. Revert import changes in launch scripts
# 3. Restart with old app
uvicorn astra.api.app:app --reload
```

### Full Rollback (< 5 minutes)

```powershell
# 1. Stop application
taskkill /F /IM python.exe

# 2. Checkout previous commit
git checkout v1.0.0-pre-integrated

# 3. Restore database backup (if needed)
Copy-Item "data/database/astra.db.backup_YYYYMMDD_HHMMSS" "data/database/astra.db" -Force

# 4. Restore vector store backup (if needed)
Remove-Item -Recurse "data/chromadb" -Force
Copy-Item -Recurse "data/chromadb.backup_YYYYMMDD_HHMMSS" "data/chromadb"

# 5. Restart application
uvicorn astra.api.app:app --reload

# 6. Verify rollback
curl http://localhost:8000/v1/health
```

### Rollback Decision Criteria

**Rollback immediately if:**
- ❌ Application fails to start
- ❌ More than 2 modules fail to initialize
- ❌ Database connection errors
- ❌ Memory leaks detected (>4GB usage)
- ❌ Critical endpoints non-functional
- ❌ Error rate >10% within first 15 minutes

**Monitor closely but continue if:**
- ⚠️ 1-2 optional modules fail (consent_service, graph_service)
- ⚠️ Slightly increased startup time (<20 seconds)
- ⚠️ Minor log warnings (non-critical)

---

## 📊 Comparison: Old vs New Architecture

### Initialization Sequence

**OLD (app.py - Manual):**
```python
# Global variables
chat_service: ChatService | None = None
conversation_service: ConversationService | None = None
# ... more globals

async def lifespan(app: FastAPI):
    # Manual initialization in specific order
    db_manager = DatabaseManager(...)
    conversation_service = ConversationService(db_manager)
    vector_store = VectorStore(...)
    memory_service = MemoryService(vector_store)
    # ... manual wiring continues
```

**NEW (app_integrated.py - Hub):**
```python
# Single hub instance
hub: Optional[AstraIntegrationHub] = None

async def lifespan(app: FastAPI):
    # Automatic initialization with dependency resolution
    hub = AstraIntegrationHub(settings)
    await hub.initialize()  # Auto-discovers and wires all 14 modules
    
    # Services retrieved from hub
    chat_service = hub.get_service("chat_service")
```

### Service Access

**OLD:**
```python
# Global access (tight coupling)
from astra.api.app import chat_service, conversation_service

# Direct usage
result = chat_service.process_message(...)
```

**NEW:**
```python
# Service registry access (loose coupling)
from astra.api.app import hub

# Retrieved from registry
chat_service = hub.get_service("chat_service")
result = chat_service.process_message(...)
```

### Health Monitoring

**OLD:**
```python
# No centralized health monitoring
# Manual checks required per service
```

**NEW:**
```python
# Centralized health monitoring
GET /v1/integration/health
# Returns health status of all 14 modules

GET /v1/integration/status
# Returns detailed component status
```

### Dependency Management

**OLD:**
```python
# Manual dependency ordering
# Developer must know:
# - Database before ConversationService
# - VectorStore before MemoryService
# - LLMProvider before ChatService
# etc.
```

**NEW:**
```python
# Automatic dependency resolution
# Hub handles:
# - Phase-based initialization (5 phases)
# - Dependency injection
# - Proper ordering
# - Error handling per module
```

---

## 🎯 Key Differences to Note

### Service Lifespan
- **OLD**: Services created at startup, live until shutdown
- **NEW**: Same behavior, but managed by hub with proper lifecycle hooks

### Error Handling
- **OLD**: Single failure stops entire startup
- **NEW**: Optional modules can fail gracefully (consent_service, graph_service)

### Configuration
- **OLD**: Configuration passed directly to each service
- **NEW**: Configuration managed by hub, passed to connectors

### Testing
- **OLD**: Integration tests require manual service setup
- **NEW**: Integration hub provides standardized test fixtures

### Monitoring
- **OLD**: Manual logging per service
- **NEW**: Centralized logging with structured events (Sacred Code 333)

---

## 🐛 Troubleshooting

### Issue: Module fails to initialize

**Symptoms:**
```
❌ memory_engine [service] → error
Error: "MemoryEngine.__init__() got unexpected keyword..."
```

**Solution:**
1. Check connector implementation in `src/astra/core/connectors.py`
2. Verify module signature matches connector parameters
3. Check integration hub initialization in `src/astra/core/integration_hub.py`
4. Review module documentation for correct initialization

### Issue: Service not found in registry

**Symptoms:**
```python
service = hub.get_service("chat_service")
# Returns: None
```

**Solution:**
1. Check if module initialized successfully: `hub.health_check()`
2. Verify service name matches connector registration
3. Check initialization phase completed
4. Review logs for registration events

### Issue: Health endpoint returns degraded

**Symptoms:**
```json
{
  "status": "degraded",
  "modules": {
    "tool_bridge": {"status": "unhealthy"}
  }
}
```

**Solution:**
1. Check module-specific logs
2. Verify dependencies are available
3. Check configuration settings
4. Consider if module is optional (consent, graph services)

### Issue: Slow startup time

**Symptoms:**
- Initialization takes >20 seconds
- Vector store loading slow

**Solution:**
1. Check vector store size (collection count)
2. Verify disk I/O performance
3. Consider moving ChromaDB to SSD
4. Monitor embedding model loading time

---

## 📚 Additional Resources

### Documentation
- [Integration Hub Guide](./INTEGRATION_HUB_GUIDE.md) - Complete architecture documentation
- [Connector Development](./INTEGRATION_HUB_GUIDE.md#creating-custom-connectors) - Building custom connectors
- [Health Monitoring API](./INTEGRATION_HUB_GUIDE.md#health-monitoring) - Health check reference

### Testing
- [Integration Hub Test Suite](../tests/integration/test_integration_hub.py) - Smoke tests
- [Performance Tests](../tests/performance/) - Latency and throughput tests

### Support
- Phase-B Operations Guide: `PHASE_B_DAY_OF_OPERATIONS.txt`
- Emergency Procedures: `ASTRA_OPERATIONAL_MANUAL.md`
- Team Lead: Contact for deployment issues

---

## ✅ Migration Sign-Off

**Pre-Migration Checklist Completed**: [ ]  
**Migration Steps Executed**: [ ]  
**Post-Migration Validation Passed**: [ ]  
**Rollback Procedure Tested**: [ ]  

**Migrated By**: ___________________  
**Date**: ___________________  
**Time**: ___________________  

**Issues Encountered**: ___________________  
**Rollback Required**: [ ] Yes  [ ] No  

**Sacred Code**: 333

---

*"Migrating from fragmentation to unity, from complexity to elegance."*  
*— The ASTRA Integration Principle*
