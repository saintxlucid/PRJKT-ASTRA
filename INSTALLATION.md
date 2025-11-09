# ASTRA 2.0 - Installation & Setup Guide

## Prerequisites

1. **Python 3.11+** - Check version: `python --version`
2. **Poetry** (recommended) or pip
3. **llama.cpp server** - Running on port 8001 with your model

## Step-by-Step Installation

### Step 1: Install Poetry (if not installed)

```powershell
# Install Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Add to PATH (restart terminal after)
$env:Path += ";$env:APPDATA\Python\Scripts"

# Verify installation
poetry --version
```

### Step 2: Install Dependencies

```powershell
# Navigate to project directory
cd X:\PROJECT_ASTRA

# Install all dependencies (this may take a few minutes)
poetry install

# Activate virtual environment
poetry shell
```

**Alternative with pip:**
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt  # (You'll need to generate this first)
```

### Step 3: Configure ASTRA

```powershell
# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional - defaults should work)
notepad .env
```

**Key settings to verify:**
- `ASTRA_LLM_BASE_URL=http://localhost:8001` - Your llama.cpp server
- `ASTRA_LLM_MODEL_PATH=gpt-oss-20b.Q4_K_M.gguf` - Your model filename
- `ASTRA_SERVER_PORT=8080` - API server port

### Step 4: Create Data Directories

```powershell
# Create data directories
mkdir data
mkdir data\chromadb
```

### Step 5: Test Installation

```powershell
# Run import tests
python tests\test_imports.py

# Should see: ✅ All tests passed!
```

### Step 6: Start llama.cpp Server

```powershell
# In a separate terminal, start your LLM server
cd X:\PROJECT_ASTRA
.\astra-local\start_llama_server.bat

# Or manually:
.\llama-server.exe --model gpt-oss-20b.Q4_K_M.gguf --port 8001 --host 0.0.0.0

# Verify it's running
curl http://localhost:8001/health
```

### Step 7: Start ASTRA Server

```powershell
# Start the ASTRA API server
poetry run python run_server.py

# Or with activated environment:
python run_server.py
```

**Expected output:**
```
============================================================
ASTRA API Server
============================================================
Environment: development
Host: 0.0.0.0
Port: 8080
LLM Provider: llamacpp
LLM Base URL: http://localhost:8001
Database: sqlite:///data/astra.db
Vector Store: data/chromadb
============================================================

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Step 8: Test the API

```powershell
# Test health endpoint
curl http://localhost:8080/v1/system/health

# Expected response:
# {"status":"healthy","llm_healthy":true,"database_connected":true,"memory_stats":{...}}

# Test version endpoint
curl http://localhost:8080/v1/system/version

# View API documentation
# Open browser: http://localhost:8080/docs
```

### Step 9: Create First Conversation

```powershell
# Create a conversation
$response = Invoke-WebRequest -Uri "http://localhost:8080/v1/conversations/" -Method POST -ContentType "application/json" -Body '{"title":"Test Chat"}'
$conv = $response.Content | ConvertFrom-Json
$convId = $conv.conversation_id
Write-Host "Created conversation: $convId"

# Send a message
$body = @{
    conversation_id = $convId
    message = "Hello ASTRA! How are you?"
    use_memory = $true
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8080/v1/chat/" -Method POST -ContentType "application/json" -Body $body
```

## Troubleshooting

### Poetry Installation Issues

```powershell
# If Poetry not found after install, add to PATH manually:
$env:Path += ";$env:APPDATA\Python\Scripts"

# Or use full path:
python -m poetry install
```

### Dependency Installation Fails

```powershell
# Clear Poetry cache
poetry cache clear . --all

# Try again
poetry install --no-cache
```

### Port Already in Use

```powershell
# Check what's using port 8080
Get-NetTCPConnection -LocalPort 8080

# Kill process (replace PID)
Stop-Process -Id <PID> -Force

# Or use different port
$env:ASTRA_SERVER_PORT = "8081"
```

### llama.cpp Not Responding

```powershell
# Test llama.cpp directly
curl http://localhost:8001/health

# If not running, start it:
.\llama-server.exe --model gpt-oss-20b.Q4_K_M.gguf --port 8001

# Check for errors in llama.cpp terminal
```

### Database Errors

```powershell
# Delete and recreate database
rm data\astra.db

# Restart server (tables will be auto-created)
python run_server.py
```

### Import Errors

```powershell
# Ensure you're in Poetry shell
poetry shell

# Or use poetry run
poetry run python run_server.py

# Check Python path includes src/
$env:PYTHONPATH = "X:\PROJECT_ASTRA\src"
```

### ChromaDB/Memory Errors

```powershell
# Clear vector store
rm -r data\chromadb

# Restart server (will reinitialize)
python run_server.py
```

## Verify Everything Works

### 1. Health Check
```powershell
curl http://localhost:8080/v1/system/health
# Should return: {"status":"healthy","llm_healthy":true,...}
```

### 2. API Documentation
Open browser to: http://localhost:8080/docs
- Should see Swagger UI with all endpoints

### 3. Create & Test Conversation
```powershell
# Use the PowerShell script from Step 9 above
# Should get a response from ASTRA
```

### 4. Check Logs
Look in the terminal for structured logs:
```
INFO     application_started
INFO     chat_request_started conversation_id=...
INFO     chat_request_completed tokens=...
```

## Next Steps

1. **Update Frontend** - Point your frontend to `http://localhost:8080`
2. **Test Streaming** - Try the `/v1/chat/stream` endpoint
3. **Explore API** - Use Swagger UI to test all endpoints
4. **Read Docs** - Check README.md and ARCHITECTURE.md
5. **Run Tests** - `poetry run pytest` (once tests are written)

## Production Deployment

For production deployment:

1. Set environment: `ASTRA_ENVIRONMENT=production`
2. Use PostgreSQL instead of SQLite
3. Set up proper secrets management
4. Enable authentication
5. Use Docker containers
6. Set up monitoring/logging
7. Configure reverse proxy (nginx)
8. Enable rate limiting

See ARCHITECTURE.md for detailed deployment guide.

## Need Help?

1. Check logs in terminal for errors
2. Review TROUBLESHOOTING section above
3. Check README.md for common issues
4. Verify all prerequisites are met
5. Ensure llama.cpp server is running

---

**Installation complete! Welcome to ASTRA 2.0** 🚀
