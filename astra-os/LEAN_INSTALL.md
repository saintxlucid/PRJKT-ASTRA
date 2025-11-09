# ASTRA OS Dependency Guide

## 📦 Dependency Matrix

### Core Requirements (Always Needed)

| Package | Location | Purpose | Size |
|---------|----------|---------|------|
| `react` | apps/pantheon | UI framework | ~100KB |
| `vite` | apps/pantheon | Build tool | ~10MB |
| `tailwindcss` | apps/pantheon | Styling | ~5MB |
| `typescript` | Multiple | Type safety | ~20MB |

### Service Dependencies (Conditional)

#### Sigil Gate (Consent Journal)
```json
{
  "express": "^4.18.0",
  "cors": "^2.8.5",
  "better-sqlite3": "^9.0.0"
}
```
**Only needed if**: Running consent UI with file operation tracking  
**Size**: ~15MB total

#### Memory Service (Dream Grove)
```txt
fastapi==0.104.0
uvicorn[standard]==0.24.0
sentence-transformers==2.2.2  # ⚠️ HEAVY: ~500MB
faiss-cpu==1.7.4
numpy==1.24.0
pydantic==2.0.0
```
**Only needed if**: Running semantic memory search  
**Size**: ~600-800MB with ML models

#### Supervisor Service (Weaver)
```json
{
  "express": "^4.18.0",
  "cors": "^2.8.5"
}
```
**Only needed if**: Running job orchestration UI  
**Size**: ~8MB

---

## 🎯 Installation Strategies

### Strategy 1: UI Only (Code Review)
**Use case**: Reading code, reviewing PRs, documentation work  
**Install**:
```powershell
cd apps\pantheon
npm install --production
```
**Skip**: All services, Python dependencies  
**Size**: ~400MB

---

### Strategy 2: UI + Consent (Light Dev)
**Use case**: Working on UI and consent flow without memory  
**Install**:
```powershell
# Pantheon UI
cd apps\pantheon
npm install

# Sigil Gate service
cd ..\..\services\sigil_gate
npm install
```
**Skip**: Python memory service  
**Size**: ~500-600MB

---

### Strategy 3: Full Stack (Production)
**Use case**: Complete development including ML features  
**Install**:
```powershell
# All Node services
cd apps\pantheon
npm install

cd ..\..\services\sigil_gate
npm install

cd ..\supervisor
npm install

# Python memory service
cd ..\memory
pip install -r requirements.txt
```
**Skip**: Nothing  
**Size**: ~2-3GB (includes ML models)

---

### Strategy 4: Containerized Services
**Use case**: Avoid local ML model bloat  
**Install**:
```powershell
# UI only locally
cd apps\pantheon
npm install

# Services in Docker
docker-compose up memory sigil_gate supervisor
```
**Skip**: Local Python environment, service node_modules  
**Size**: ~500MB local + Docker images

---

## 🚫 Optional/Skippable Dependencies

### Can Skip If...

#### 1. **sentence-transformers** (~500MB)
- Not using semantic search
- Not testing Dream Grove memory features
- Using mock data for UI development

**How to skip**:
```powershell
# Comment out in services/memory/requirements.txt
# sentence-transformers==2.2.2
```

#### 2. **electron** + **electron-builder** (~300MB)
- Not building desktop app
- Only working on web interface
- CI/CD handles builds

**How to skip**:
```json
// In package.json, move to devDependencies or remove
// "electron": "^27.0.0"
```

#### 3. **framer-motion** (~5MB)
- Animations not critical for testing
- Can use CSS transitions instead

**How to skip**: Install with `--omit=optional`

---

## 🔬 Development Profiles

### Profile: Frontend Developer
**Needs**: UI components, styling, routing  
**Install**:
```powershell
cd apps\pantheon
npm install --only=dev
```
**Mock backends**: Use service workers or JSON files

---

### Profile: Backend Developer
**Needs**: Services, APIs, database  
**Install**:
```powershell
cd services\sigil_gate
npm install

cd ..\memory
pip install -r requirements.txt
```
**Skip**: Pantheon UI build

---

### Profile: Full-Stack Developer
**Needs**: Everything  
**Install**:
```powershell
npm run setup  # If root setup script exists
# OR
cd apps\pantheon && npm install && cd ..\..
cd services\sigil_gate && npm install && cd ..\..
cd services\memory && pip install -r requirements.txt
```

---

## 📊 Dependency Tree Visualization

```
astra-os/
├── apps/pantheon/
│   ├── react, react-dom          [~500KB] ✅ Required
│   ├── vite                       [~10MB] ✅ Required
│   ├── tailwindcss                [~5MB] ✅ Required
│   ├── framer-motion              [~5MB] ⚠️ Optional
│   └── node_modules/              [~400-600MB total]
│
├── services/sigil_gate/
│   ├── express                    [~1MB] ✅ Required (if using)
│   ├── better-sqlite3             [~8MB] ✅ Required (if using)
│   └── node_modules/              [~15MB total]
│
├── services/supervisor/
│   ├── express                    [~1MB] ✅ Required (if using)
│   └── node_modules/              [~8MB total]
│
└── services/memory/
    ├── fastapi                    [~5MB] ✅ Required (if using)
    ├── sentence-transformers      [~500MB] ⚠️ Optional (heavy!)
    ├── faiss-cpu                  [~50MB] ✅ Required (if using)
    └── .venv/                     [~600-800MB total]
```

---

## 🧪 Testing Without Full Install

### Mock Memory Service
Create `services/memory/mock_server.py`:
```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/memory/add")
async def add_memory(request: dict):
    return {"id": 1, "index_size": 1, "latency_ms": 5}

@app.post("/memory/search")
async def search(request: dict):
    return {
        "results": [],
        "latency_ms": 10
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7007)
```

Run with:
```powershell
# No dependencies needed!
python -m pip install fastapi uvicorn  # Only 10MB
python services\memory\mock_server.py
```

---

## 💡 Pro Tips

1. **Use pnpm**: Saves ~40% disk space via hardlinks
   ```powershell
   npm i -g pnpm
   pnpm install  # Instead of npm install
   ```

2. **Workspace installs**: Only install what you're working on
   ```powershell
   # Not needed if you're only changing services
   # cd apps\pantheon && npm install
   ```

3. **Docker for heavy deps**: Run ML services in containers
   ```yaml
   # docker-compose.yml
   services:
     memory:
       image: python:3.11-slim
       volumes: ["./services/memory:/app"]
   ```

4. **Lazy loading**: Install deps when you actually need them
   ```powershell
   # Start UI first, add services later
   cd apps\pantheon && npm install && npm run dev
   # Later: cd services/memory && pip install -r requirements.txt
   ```

---

## 🎓 Quick Reference

| Task | Minimal Install | Command |
|------|----------------|---------|
| Read code | None | Just open in VS Code |
| Run UI | Pantheon only | `cd apps/pantheon && npm install` |
| Test consent | + Sigil Gate | `cd services/sigil_gate && npm install` |
| Test memory | + Python deps | `pip install -r services/memory/requirements.txt` |
| Full dev | Everything | Run all install commands above |

---

**Next Steps**: See `OPTIMIZATION.md` for cleanup and `README.md` for full setup.
