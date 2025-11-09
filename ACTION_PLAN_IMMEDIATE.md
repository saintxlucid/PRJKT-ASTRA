# ASTRA CORE - Immediate Action Plan

**Date:** October 16, 2025  
**Status:** Ready to Execute  
**Goal:** Unblock critical enhancements and complete partial implementations

---

## 🚨 A. IMMEDIATE UNBLOCK: Free Disk Space (2GB+)

### Windows PowerShell - Inspect Big Files

```powershell
# Show top 30 largest files on C:
Get-ChildItem -Path C:\ -Recurse -ErrorAction SilentlyContinue |
  Where-Object { -not $_.PSIsContainer } |
  Sort-Object Length -Descending |
  Select-Object -First 30 FullName,@{Name='MB';Expression={[math]::Round($_.Length/1MB,2)}}
```

### Safe Quick Wins (Pick What Applies)

```powershell
# 1. Move large model files to external storage
Move-Item -Path "C:\models\old_model.gguf" -Destination "D:\models_archive\"

# 2. Archive old logs
Compress-Archive -Path "C:\logs\old" -DestinationPath "D:\archive\logs-2025-10-16.zip"
Remove-Item -Path "C:\logs\old" -Recurse -Force

# 3. Clean temp files
Remove-Item -Path "C:\Users\*\AppData\Local\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

# 4. Docker cleanup (if installed)
docker system prune -a --volumes --force

# 5. Python cache cleanup
Get-ChildItem -Path "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### Linux Alternative

```bash
# Show largest files
sudo find / -xdev -type f -printf "%s\t%p\n" 2>/dev/null | sort -nr | head -n 40

# Clean package caches (Debian/Ubuntu)
sudo apt-get clean

# Journal logs cleanup
sudo journalctl --vacuum-size=200M

# Docker reclaim
sudo docker system prune -a --volumes --force
```

**✅ Completion Check:** Run `Get-PSDrive C | Select-Object Free` - should show 2GB+ freed

---

## 🔧 B. BRIDGE MODULE: Minimal Secure Skeleton

### Create `src/astra/bridge/bridge_server.py`

```python
"""
ASTRA Bridge - Tool Execution Server
Minimal, secure skeleton for LLM function calling
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import subprocess
import shlex
import requests
import os
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

app = FastAPI(title="ASTRA Bridge v1.0", version="1.0.0")

# Security: API Token validation
BRIDGE_TOKEN = os.getenv("BRIDGE_API_TOKEN", "dev-token-change-me")

def verify_token(authorization: str = Header(...)) -> bool:
    """Verify Bearer token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.replace("Bearer ", "")
    if token != BRIDGE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    return True

# Request/Response models
class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any] = {}

class ToolResult(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Tool Registry
TOOLS: Dict[str, callable] = {}

def register_tool(name: str, fn: callable):
    """Register a tool adapter"""
    TOOLS[name] = fn
    logger.info("tool_registered", name=name)

# --- TOOL ADAPTERS ---

# Adapter 1: Safe Shell (Whitelist Only)
ALLOWED_CMDS = {
    "ls": "/bin/ls",
    "du": "/usr/bin/du",
    "dir": "C:\\Windows\\System32\\cmd.exe /c dir",
}

def shell_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute whitelisted shell commands"""
    cmd = args.get("cmd", "")
    cmd_name = cmd.split()[0]
    
    if cmd_name not in ALLOWED_CMDS:
        raise ValueError(f"Command '{cmd_name}' not allowed. Allowed: {list(ALLOWED_CMDS.keys())}")
    
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            timeout=30,
            text=True
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
    except subprocess.TimeoutExpired:
        raise ValueError("Command timeout (>30s)")
    except Exception as e:
        raise ValueError(f"Execution failed: {str(e)}")

# Adapter 2: LLM Call (llama.cpp)
def llama_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Call local llama.cpp server"""
    url = os.getenv("ASTRA_LLM_BASE_URL", "http://127.0.0.1:8001")
    
    payload = {
        "model": args.get("model", "gpt-oss-20b"),
        "messages": args.get("messages", []),
        "max_tokens": args.get("max_tokens", 512),
        "temperature": args.get("temperature", 0.7)
    }
    
    try:
        resp = requests.post(
            f"{url}/v1/chat/completions",
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise ValueError(f"LLM call failed: {str(e)}")

# Adapter 3: File Reader (Safe paths only)
ALLOWED_DIRS = [
    "X:\\PROJECT_ASTRA_1.0 (ASTRA_CORE)\\data",
    "/home/user/astra/data"
]

def file_reader_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read files from allowed directories only"""
    path = args.get("path", "")
    
    # Security: Check path is in allowed dirs
    allowed = any(path.startswith(d) for d in ALLOWED_DIRS)
    if not allowed:
        raise ValueError(f"Path not allowed. Must start with: {ALLOWED_DIRS}")
    
    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read(10000)  # Max 10KB
        return {"content": content, "size": len(content)}
    except Exception as e:
        raise ValueError(f"Read failed: {str(e)}")

# Register all tools
register_tool("shell", shell_tool)
register_tool("llama", llama_tool)
register_tool("file_reader", file_reader_tool)

# --- API ENDPOINTS ---

@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "tools": list(TOOLS.keys())}

@app.post("/call", response_model=ToolResult)
def call_tool(payload: ToolCall, authorized: bool = Depends(verify_token)):
    """Execute a tool with authorization"""
    logger.info("tool_call_received", tool=payload.tool_name, args=payload.args)
    
    tool_fn = TOOLS.get(payload.tool_name)
    if not tool_fn:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.tool_name}' not found")
    
    try:
        result = tool_fn(payload.args)
        logger.info("tool_call_success", tool=payload.tool_name)
        return ToolResult(ok=True, result=result)
    except ValueError as e:
        logger.warning("tool_call_failed", tool=payload.tool_name, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("tool_call_error", tool=payload.tool_name, error=str(e))
        raise HTTPException(status_code=500, detail="Internal tool error")

@app.get("/tools")
def list_tools(authorized: bool = Depends(verify_token)):
    """List available tools"""
    return {
        "tools": [
            {
                "name": "shell",
                "description": "Execute whitelisted shell commands",
                "allowed_cmds": list(ALLOWED_CMDS.keys())
            },
            {
                "name": "llama",
                "description": "Call local LLM server",
                "args": ["model", "messages", "max_tokens", "temperature"]
            },
            {
                "name": "file_reader",
                "description": "Read files from allowed directories",
                "allowed_dirs": ALLOWED_DIRS
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)
```

### Create `tests/bridge/test_bridge_server.py`

```python
"""Unit tests for Bridge Server"""
import pytest
from fastapi.testclient import TestClient
from src.astra.bridge.bridge_server import app, BRIDGE_TOKEN

client = TestClient(app)

def test_health_endpoint():
    """Health check should work without auth"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_unauthorized_access():
    """Calls without token should fail"""
    resp = client.post("/call", json={"tool_name": "shell", "args": {}})
    assert resp.status_code == 403

def test_authorized_call():
    """Valid token should allow access"""
    headers = {"Authorization": f"Bearer {BRIDGE_TOKEN}"}
    resp = client.post(
        "/call",
        json={"tool_name": "shell", "args": {"cmd": "ls"}},
        headers=headers
    )
    assert resp.status_code in [200, 400]  # 400 if cmd not found on Windows

def test_list_tools():
    """List tools endpoint"""
    headers = {"Authorization": f"Bearer {BRIDGE_TOKEN}"}
    resp = client.get("/tools", headers=headers)
    assert resp.status_code == 200
    assert "tools" in resp.json()
```

### Run Bridge Server

```powershell
# Set token
$env:BRIDGE_API_TOKEN = "astra-bridge-secret-token-2025"

# Run server
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python -m uvicorn src.astra.bridge.bridge_server:app --host 127.0.0.1 --port 8888

# Test in another terminal
curl http://127.0.0.1:8888/health
```

**✅ Completion Check:** Health endpoint returns 200, tools endpoint requires auth

---

## 📄 C. DOCUMENT INTELLIGENCE: PDF Ingest Pipeline

### Create `src/astra/services/document_service.py`

```python
"""
Document Intelligence Service
PDF ingestion, chunking, embedding, indexing
"""
import fitz  # pip install pymupdf
import hashlib
import json
import os
from pathlib import Path
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()

class DocumentService:
    """Document ingestion and indexing service"""
    
    def __init__(self, index_path: str = "data/document_index.jsonl"):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        logger.info("extracting_text", path=pdf_path)
        
        text_parts = []
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(f"[Page {page_num}]\n{page_text}")
            doc.close()
        except Exception as e:
            logger.error("extraction_failed", path=pdf_path, error=str(e))
            raise
        
        full_text = "\n\n".join(text_parts)
        logger.info("extraction_complete", path=pdf_path, chars=len(full_text))
        return full_text
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 800,
        overlap: int = 100
    ) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += chunk_size - overlap
        
        logger.info("chunking_complete", total_chunks=len(chunks))
        return chunks
    
    def generate_embedding(self, text: str) -> str:
        """Generate embedding (placeholder - replace with real model)"""
        # TODO: Replace with sentence-transformers or OpenAI embeddings
        return hashlib.sha256(text.encode()).hexdigest()
    
    def ingest_document(
        self,
        pdf_path: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Ingest PDF into index"""
        logger.info("ingesting_document", path=pdf_path)
        
        # Extract and chunk
        text = self.extract_text(pdf_path)
        chunks = self.chunk_text(text)
        
        # Generate records
        doc_name = Path(pdf_path).stem
        records = []
        
        for i, chunk in enumerate(chunks):
            record = {
                "id": f"{doc_name}_chunk_{i}",
                "document": doc_name,
                "chunk_index": i,
                "text": chunk,
                "embedding": self.generate_embedding(chunk),
                "metadata": metadata or {}
            }
            records.append(record)
        
        # Append to index
        with open(self.index_path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        
        logger.info("ingestion_complete", document=doc_name, chunks=len(records))
        return len(records)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search index (naive implementation - replace with vector search)"""
        query_lower = query.lower()
        results = []
        
        if not self.index_path.exists():
            return results
        
        with open(self.index_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                # Simple keyword match (replace with semantic search)
                if query_lower in record["text"].lower():
                    results.append(record)
        
        return results[:top_k]

# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python document_service.py <pdf_path>")
        sys.exit(1)
    
    service = DocumentService()
    chunks = service.ingest_document(sys.argv[1])
    print(f"✅ Ingested {chunks} chunks")
```

### Create `tests/services/test_document_service.py`

```python
"""Unit tests for Document Service"""
import pytest
from src.astra.services.document_service import DocumentService
import tempfile
from pathlib import Path

@pytest.fixture
def doc_service():
    """Create service with temp index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "test_index.jsonl"
        yield DocumentService(str(index_path))

def test_chunking(doc_service):
    """Test text chunking"""
    text = " ".join([f"word{i}" for i in range(1000)])
    chunks = doc_service.chunk_text(text, chunk_size=100, overlap=20)
    
    assert len(chunks) > 1
    assert all(len(c.split()) <= 100 for c in chunks)

def test_embedding_generation(doc_service):
    """Test embedding generation"""
    text = "This is a test document"
    embedding = doc_service.generate_embedding(text)
    
    assert embedding is not None
    assert len(embedding) > 0

def test_search_empty_index(doc_service):
    """Search on empty index returns empty"""
    results = doc_service.search("test query")
    assert results == []
```

### Install Dependencies

```powershell
pip install pymupdf  # For PDF processing
```

### Test Ingestion

```powershell
# Create a sample PDF or use existing
python src/astra/services/document_service.py "path/to/sample.pdf"

# Check index created
Get-Content "data/document_index.jsonl" | Select-Object -First 5
```

**✅ Completion Check:** PDF ingested, chunks written to index, search returns results

---

## 🧪 D. TESTS & COVERAGE

### Run Existing Tests

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
pytest -v --cov=src/astra --cov-report=term-missing
```

### Add Missing Tests

```powershell
# Test bridge server
pytest tests/bridge/test_bridge_server.py -v

# Test document service
pytest tests/services/test_document_service.py -v

# Check coverage
coverage report --show-missing
```

**Target:** Maintain >93.9% coverage, aim for 98%+

---

## ✅ E. PR / RELEASE CHECKLIST

Use this for every merge to `main`:

- [ ] **Lint:** `ruff check src/` passes
- [ ] **Tests:** `pytest -q --maxfail=1` passes
- [ ] **Coverage:** No drop >1% from baseline (93.9%)
- [ ] **Security:** New endpoints reviewed, no hardcoded secrets
- [ ] **Docs:** README/runbook updated for new commands
- [ ] **Migration:** Model paths, DB schema changes documented
- [ ] **Tag:** Version bumped, changelog updated

---

## 🗺️ F. TACTICAL ROADMAP

### Phase 1: Stability / Unblock (This Week)

1. ✅ Free disk space (2GB+) - **Complete section A above**
2. ✅ Bridge server with 3 adapters - **Complete section B above**
3. ✅ PDF ingestion pipeline - **Complete section C above**
4. 🔄 Docker Compose for local dev (next)

### Phase 1.5: Polish / Infra (Next 2 Weeks)

1. Prometheus metrics + Grafana dashboard
2. Health checks on all components
3. Encrypted secrets management
4. Backup runbook for models

### Phase 2.0: Scale Features (Next Month)

1. Production React web UI + OAuth2
2. RAG pipeline with re-ranker
3. Multi-user tenancy
4. Kubernetes manifests

---

## 🔐 G. SECURITY QUICK CHECKLIST

- [ ] Bridge uses token auth (`BRIDGE_API_TOKEN` env var)
- [ ] Whitelist-only shell commands
- [ ] File reader restricted to allowed directories
- [ ] Secrets in env vars, not code
- [ ] Model files have restricted permissions
- [ ] Alerts set up for anomalies

---

## 📋 H. QUICK REMEDIATION PRs

Open these PRs **today**:

1. **`fix/disk-cleanup-scripts`**
   - Add PowerShell cleanup script
   - Add Linux cleanup script
   - Update README with cleanup instructions

2. **`feature/bridge-server`**
   - Add `src/astra/bridge/bridge_server.py`
   - Add `tests/bridge/test_bridge_server.py`
   - Update docs with bridge API reference

3. **`feature/document-intelligence`**
   - Add `src/astra/services/document_service.py`
   - Add `tests/services/test_document_service.py`
   - Add PDF ingestion guide

4. **`chore/docker-compose-dev`**
   - Add `docker-compose.yml` for local dev
   - Include llama-server, bridge, vector DB
   - Add startup guide

---

## 🎯 I. THREE TASKS FOR RIGHT NOW

### Task 1: Disk Space (15 minutes)

```powershell
# Inspect largest files
Get-ChildItem -Path C:\ -Recurse -ErrorAction SilentlyContinue |
  Where-Object { -not $_.PSIsContainer } |
  Sort-Object Length -Descending |
  Select-Object -First 30 FullName,@{Name='MB';Expression={[math]::Round($_.Length/1MB,2)}}

# Move large files to external drive
# (inspect output above and move appropriately)
```

### Task 2: Bridge Server (30 minutes)

```powershell
# Create bridge server file (copy code from section B above)
New-Item -Path "src/astra/bridge/bridge_server.py" -ItemType File -Force

# Create test file
New-Item -Path "tests/bridge/test_bridge_server.py" -ItemType File -Force

# Run bridge server
$env:BRIDGE_API_TOKEN = "astra-secret-2025"
python -m uvicorn src.astra.bridge.bridge_server:app --host 127.0.0.1 --port 8888
```

### Task 3: PDF Ingestion (30 minutes)

```powershell
# Install dependencies
pip install pymupdf

# Create document service (copy code from section C above)
New-Item -Path "src/astra/services/document_service.py" -ItemType File -Force

# Test with sample PDF
python src/astra/services/document_service.py "path/to/sample.pdf"

# Verify index created
Get-Content "data/document_index.jsonl" -Head 5
```

---

## 🎉 SUCCESS CRITERIA

After completing all tasks:

- ✅ 2GB+ disk space freed
- ✅ Bridge server running on port 8888 with 3 adapters
- ✅ PDF successfully ingested into document index
- ✅ All tests passing with >93.9% coverage
- ✅ PRs ready to merge

**Estimated Total Time:** 2-3 hours

---

**Next:** Review completed tasks, merge PRs, move to Phase 1.5 (monitoring + infrastructure)
