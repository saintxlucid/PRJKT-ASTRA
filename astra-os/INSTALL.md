# ASTRA OS — Installation Guide

## Prerequisites

### Windows
- **Node.js 18+**: https://nodejs.org/
- **Python 3.10+**: https://www.python.org/downloads/
- **Git**: https://git-scm.com/downloads

### Verify Installation
```powershell
node --version   # Should be v18.0.0 or higher
python --version # Should be 3.10.0 or higher
npm --version    # Should be 9.0.0 or higher
```

## Installation Steps

### 1. Clone Repository
```powershell
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
# Repository already present
```

### 2. Install Pantheon UI Dependencies
```powershell
cd astra-os\apps\pantheon
npm install
```

This installs:
- React 18.2
- Vite 5.0
- Tailwind CSS 3.4
- TypeScript 5.3

**Expected output:**
```
added 234 packages in 15s
```

### 3. Install Sigil Gate Dependencies
```powershell
cd astra-os\services\sigil_gate
npm install
```

This installs:
- better-sqlite3 (for append-only journal)
- TypeScript types

### 4. Setup Python Environment for Memory Service
```powershell
cd astra-os\services\memory

# Create virtual environment
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- sentence-transformers (embeddings)
- faiss-cpu (vector search)
- numpy, pydantic

**First run downloads ~500MB model:**
```
Downloading sentence-transformers/all-MiniLM-L6-v2...
```

**Expected time:** 2-5 minutes depending on connection

## Troubleshooting

### Python venv activation fails
**Problem:** `.venv\Scripts\Activate.ps1` gives execution policy error

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Node-gyp build errors (better-sqlite3)
**Problem:** `npm install` fails with build errors

**Solution:**
```powershell
# Install Windows Build Tools
npm install --global windows-build-tools
```

### Port already in use
**Problem:** `EADDRINUSE: address already in use :::3000`

**Solution:**
```powershell
# Find process using port
netstat -ano | findstr :3000

# Kill process
taskkill /PID <PID> /F
```

### Python module import errors
**Problem:** `ModuleNotFoundError: No module named 'faiss'`

**Solution:**
```powershell
# Make sure venv is activated
.\.venv\Scripts\Activate.ps1

# Reinstall
pip install --upgrade -r requirements.txt
```

## Verification

### Test Memory Service
```powershell
cd astra-os\services\memory
.\.venv\Scripts\Activate.ps1
python embed_server.py
```

**Expected output:**
```
Loading embedding model...
✓ Starting with empty index
🌌 Starting Dream Grove Memory Service...
📍 Listening on http://127.0.0.1:7007
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:7007
```

**Test health endpoint:**
```powershell
curl http://127.0.0.1:7007/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "model": "all-MiniLM-L6-v2",
  "index_size": 0,
  "embedding_dim": 384
}
```

### Test Pantheon UI
```powershell
cd astra-os\apps\pantheon
npm run dev
```

**Expected output:**
```
  VITE v5.0.0  ready in 234 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

Open browser to `http://localhost:3000` — should see ASTRA Pantheon Shell.

## Quick Start

Use the convenience script:
```powershell
cd astra-os
.\start.ps1
```

This launches both services in separate terminals.

## File Structure Check

Verify all files are present:
```powershell
tree /F astra-os
```

Expected structure:
```
astra-os/
├── apps/
│   └── pantheon/
│       ├── src/
│       ├── package.json
│       ├── vite.config.ts
│       └── tsconfig.json
├── services/
│   ├── memory/
│   │   ├── embed_server.py
│   │   └── requirements.txt
│   └── sigil_gate/
│       ├── journal.ts
│       ├── verify.ts
│       └── package.json
├── README.md
└── start.ps1
```

## Next Steps

After successful installation:
1. Explore the UI at `http://localhost:3000`
2. Try Oracle command palette (`Ctrl+K`)
3. Navigate between realms (`Alt+1` through `Alt+5`)
4. Test memory service via Dream Grove
5. Experiment with Sigil Gate consent flow

See `README.md` for detailed feature documentation.

## Support

If issues persist:
1. Check Node.js and Python versions
2. Verify all dependencies installed
3. Check firewall/antivirus (ports 3000, 7007)
4. Review terminal output for specific errors

---

**Installation Time:** ~10 minutes (excluding model download)
**Disk Space Required:** ~2GB (includes node_modules, venv, models)
