# ASTRA 2.0 - Getting Started Checklist

## ✅ Pre-Installation Checklist

- [ ] Python 3.11 or higher installed
  - Check: `python --version`
- [ ] Git installed (for cloning)
  - Check: `git --version`
- [ ] At least 2GB free disk space
- [ ] llama.cpp model file present (`gpt-oss-20b.Q4_K_M.gguf`)

## ✅ Installation Checklist

### Poetry Setup (Recommended)
- [ ] Install Poetry
  ```powershell
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
  ```
- [ ] Verify Poetry installation: `poetry --version`
- [ ] Navigate to project: `cd X:\PROJECT_ASTRA`
- [ ] Install dependencies: `poetry install`
- [ ] Activate environment: `poetry shell`

### Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Review `config/default.yaml` settings
- [ ] Create data directories:
  ```powershell
  mkdir data
  mkdir data\chromadb
  ```

### Verification
- [ ] Run import test: `python tests\test_imports.py`
- [ ] Should see: "✅ All tests passed!"

## ✅ First Run Checklist

### Start llama.cpp Server
- [ ] Open **Terminal 1**
- [ ] Navigate to project: `cd X:\PROJECT_ASTRA`
- [ ] Start llama server:
  ```powershell
  .\llama-server.exe --model gpt-oss-20b.Q4_K_M.gguf --port 8001
  ```
- [ ] Verify health: `curl http://localhost:8001/health`
- [ ] Leave terminal running

### Start ASTRA Server
- [ ] Open **Terminal 2**
- [ ] Navigate to project: `cd X:\PROJECT_ASTRA`
- [ ] Activate environment: `poetry shell`
- [ ] Start server: `python run_server.py`
- [ ] Should see startup banner with settings
- [ ] Should see: "Application startup complete"
- [ ] Should see: "Uvicorn running on http://0.0.0.0:8080"

### Test API
- [ ] Open **Terminal 3** (or browser)
- [ ] Test health: `curl http://localhost:8080/v1/system/health`
  - Should return JSON with `"status":"healthy"`
- [ ] Test version: `curl http://localhost:8080/v1/system/version`
  - Should return `"version":"2.0.0"`
- [ ] Open Swagger UI: http://localhost:8080/docs
  - Should see API documentation

## ✅ First Conversation Checklist

### Create Conversation
- [ ] Use Swagger UI or curl to create conversation:
  ```powershell
  curl -X POST http://localhost:8080/v1/conversations/ -H "Content-Type: application/json" -d "{\"title\":\"Test Chat\"}"
  ```
- [ ] Note the `conversation_id` from response
- [ ] Verify conversation exists:
  ```powershell
  curl http://localhost:8080/v1/conversations/
  ```

### Send First Message
- [ ] Send message (replace CONV_ID):
  ```powershell
  curl -X POST http://localhost:8080/v1/chat/ -H "Content-Type: application/json" -d "{\"conversation_id\":\"CONV_ID\",\"message\":\"Hello ASTRA!\"}"
  ```
- [ ] Should receive response with assistant message
- [ ] Check logs in Terminal 2 for:
  - `chat_request_started`
  - `chat_request_completed`

### Test Streaming
- [ ] Try streaming endpoint in Swagger UI
- [ ] Or use curl:
  ```powershell
  curl -X POST http://localhost:8080/v1/chat/stream -H "Content-Type: application/json" -d "{\"conversation_id\":\"CONV_ID\",\"message\":\"Tell me a joke\"}"
  ```
- [ ] Should see streaming response chunks

### Verify Memory
- [ ] Send follow-up message: "What did I just ask you?"
- [ ] ASTRA should remember previous context
- [ ] Check ChromaDB directory: `ls data\chromadb`
  - Should contain vector store files

## ✅ Integration Checklist

### Frontend Integration (if applicable)
- [ ] Update frontend API URL to `http://localhost:8080`
- [ ] Update endpoint from `/v1/chat/stream` to match new API
- [ ] Test frontend connection
- [ ] Verify CORS settings in `config/default.yaml`:
  ```yaml
  cors:
    origins:
      - "http://localhost:5173"  # Add your frontend URL
  ```

### Database Verification
- [ ] Check database exists: `ls data\astra.db`
- [ ] Query conversations using API
- [ ] Query messages using API
- [ ] Verify timestamps are correct

### Memory/RAG Verification
- [ ] Create conversation with multiple messages
- [ ] Ask follow-up questions
- [ ] Verify context is retained
- [ ] Check memory stats: `curl http://localhost:8080/v1/system/health`
  - Should show `memory_stats` with count

## ✅ Troubleshooting Checklist

If something doesn't work:

### Server Won't Start
- [ ] Check Python version: `python --version` (must be 3.11+)
- [ ] Check Poetry environment: `poetry env info`
- [ ] Check port availability: `Get-NetTCPConnection -LocalPort 8080`
- [ ] Check logs in terminal for specific errors
- [ ] Try different port: `$env:ASTRA_SERVER_PORT="8081"`

### LLM Connection Fails
- [ ] Verify llama.cpp is running: `curl http://localhost:8001/health`
- [ ] Check llama.cpp logs for errors
- [ ] Verify model file exists: `ls gpt-oss-20b.Q4_K_M.gguf`
- [ ] Check LLM URL in config: `$env:ASTRA_LLM_BASE_URL`
- [ ] Test direct completion to llama.cpp

### Database Errors
- [ ] Check data directory exists: `ls data`
- [ ] Check database file permissions
- [ ] Try deleting database: `rm data\astra.db`
- [ ] Restart server (auto-creates tables)

### Memory/ChromaDB Errors
- [ ] Check ChromaDB directory: `ls data\chromadb`
- [ ] Check disk space: `Get-PSDrive C`
- [ ] Try clearing memory: `rm -r data\chromadb`
- [ ] Restart server (auto-recreates)

### Import Errors
- [ ] Verify in Poetry shell: `poetry shell`
- [ ] Check installed packages: `poetry show`
- [ ] Reinstall dependencies: `poetry install --no-cache`
- [ ] Check Python path: `$env:PYTHONPATH`

## ✅ Production Readiness Checklist

Before deploying to production:

### Configuration
- [ ] Set environment: `ASTRA_ENVIRONMENT=production`
- [ ] Switch to PostgreSQL database
- [ ] Configure secure secrets management
- [ ] Enable API authentication
- [ ] Configure rate limiting
- [ ] Set up HTTPS/TLS
- [ ] Configure CORS for production domains

### Deployment
- [ ] Create Docker images
- [ ] Set up docker-compose
- [ ] Configure persistent volumes
- [ ] Set up reverse proxy (nginx)
- [ ] Configure logging aggregation
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure automated backups

### Testing
- [ ] Run unit tests: `poetry run pytest tests/unit/`
- [ ] Run integration tests: `poetry run pytest tests/integration/`
- [ ] Run load tests
- [ ] Test failover scenarios
- [ ] Verify backup restoration

### Documentation
- [ ] Review ARCHITECTURE.md
- [ ] Review README.md
- [ ] Create runbooks for operations
- [ ] Document deployment process
- [ ] Create incident response plan

## ✅ Post-Installation Checklist

### Regular Checks
- [ ] Monitor health endpoint: `/v1/system/health`
- [ ] Check logs for errors
- [ ] Monitor database size
- [ ] Monitor vector store size
- [ ] Check API response times
- [ ] Monitor memory usage

### Maintenance
- [ ] Back up database regularly
- [ ] Clean up old conversations
- [ ] Update dependencies: `poetry update`
- [ ] Review security advisories
- [ ] Update documentation

### Next Steps
- [ ] Read ARCHITECTURE.md for deep dive
- [ ] Explore API with Swagger UI
- [ ] Test all endpoints
- [ ] Integrate with frontend
- [ ] Write custom tests
- [ ] Add custom features

---

## 🎉 Congratulations!

If all checklists are complete, you have a fully functional ASTRA 2.0 system!

### Quick Reference

**Terminals Needed**:
1. llama.cpp server on port 8001
2. ASTRA API server on port 8080
3. Your application/testing terminal

**Key URLs**:
- API Base: http://localhost:8080
- API Docs: http://localhost:8080/docs
- Health: http://localhost:8080/v1/system/health

**Common Commands**:
```powershell
# Start llama.cpp
.\llama-server.exe --model gpt-oss-20b.Q4_K_M.gguf --port 8001

# Start ASTRA
poetry run python run_server.py

# Run tests
poetry run pytest

# Format code
poetry run black src/

# Type check
poetry run mypy src/
```

**Need Help?**
- Check INSTALLATION.md for detailed instructions
- Review TROUBLESHOOTING section above
- Check logs in terminals for errors
- Review ARCHITECTURE.md for technical details

---

**Welcome to ASTRA 2.0 - Built for reliability!** 🚀
