# ASTRA OS Workspace Optimization Guide

## 🎯 Quick Cleanup (Saves 3-8 GB)

### Remove Node Modules
```powershell
# Root level
Remove-Item -Recurse -Force "node_modules"

# App level
Remove-Item -Recurse -Force "apps\pantheon\node_modules"

# Service level
Remove-Item -Recurse -Force "services\sigil_gate\node_modules"
Remove-Item -Recurse -Force "services\supervisor\node_modules"
```

### Clean Build Artifacts
```powershell
# Vite build outputs
Remove-Item -Recurse -Force "dist", "build", ".next", ".vite"

# TypeScript build info
Remove-Item -Recurse -Force "*.tsbuildinfo"

# Python cache
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### Remove Python Virtual Environment
```powershell
# If you have a .venv directory
Remove-Item -Recurse -Force ".venv"
```

---

## 📦 Lean Installation (For Code Review Only)

### Skip Heavy Dependencies

**If you only need to read/review code:**
```powershell
# Install frontend without optional deps
cd apps\pantheon
npm install --omit=optional

# Skip Python ML models entirely
# Comment out sentence-transformers in services/memory/requirements.txt
```

**For development without memory service:**
```powershell
# Install only UI + consent services
cd apps\pantheon
npm install

cd ..\..\services\sigil_gate
npm install
```

---

## 🚀 Optimal Setup (Production)

### Use pnpm Instead of npm
Saves ~40% disk space via hardlinks:
```powershell
npm install -g pnpm
cd apps\pantheon
pnpm install  # Much faster, smaller footprint
```

### Python with No Cache
```powershell
cd services\memory
pip install --no-cache-dir -r requirements.txt
```

### Docker Alternative
Run heavy services in containers to avoid local bloat:
```yaml
# docker-compose.yml
services:
  memory:
    image: python:3.11-slim
    volumes:
      - ./services/memory:/app
    command: uvicorn embed_server:app --host 0.0.0.0 --port 7007
```

---

## 📊 Workspace Size Breakdown

| Component | Size (Typical) | Removable? |
|-----------|----------------|------------|
| `node_modules/` (root) | 800 MB - 1.5 GB | ✅ Yes (reinstall with `npm install`) |
| `apps/pantheon/node_modules/` | 400-600 MB | ✅ Yes |
| `services/*/node_modules/` | 100-200 MB each | ✅ Yes |
| Python `.venv/` | 500 MB - 1 GB | ✅ Yes (with sentence-transformers) |
| Build artifacts (`dist/`) | 50-200 MB | ✅ Yes (rebuild with `npm run build`) |
| Source code | ~5-10 MB | ❌ No |
| Documentation | ~2 MB | ❌ No |

**Total Removable:** ~3-8 GB depending on installation

---

## 🧹 Automated Cleanup Script

Create `cleanup.ps1`:
```powershell
#!/usr/bin/env pwsh
# cleanup.ps1 - ASTRA OS Workspace Cleanup

Write-Host "🧹 ASTRA OS Workspace Cleanup" -ForegroundColor Cyan

# Remove node_modules
Write-Host "`n📦 Removing node_modules..." -ForegroundColor Yellow
Get-ChildItem -Recurse -Filter "node_modules" | Remove-Item -Recurse -Force
Write-Host "✓ node_modules removed" -ForegroundColor Green

# Remove build artifacts
Write-Host "`n🏗️ Removing build artifacts..." -ForegroundColor Yellow
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist, build, .next, .vite, out
Write-Host "✓ Build artifacts removed" -ForegroundColor Green

# Remove Python cache
Write-Host "`n🐍 Removing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
Write-Host "✓ Python cache removed" -ForegroundColor Green

# Remove .venv (optional - prompts user)
$removeVenv = Read-Host "`n❓ Remove Python virtual environment (.venv)? [y/N]"
if ($removeVenv -eq 'y' -or $removeVenv -eq 'Y') {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .venv
    Write-Host "✓ Python venv removed" -ForegroundColor Green
}

Write-Host "`n✅ Cleanup complete!" -ForegroundColor Green
Write-Host "Run 'npm install' and 'pip install -r requirements.txt' to restore dependencies`n"
```

Run with:
```powershell
.\cleanup.ps1
```

---

## 🔧 Maintain Lean Workspace

### Add to .gitignore
Already done! Key entries:
- `node_modules/`
- `**/__pycache__/`
- `.venv/`
- `*.sqlite`, `*.faiss`
- `dist/`, `build/`

### Regular Maintenance
```powershell
# Weekly cleanup of build artifacts
npm run clean  # if you add this script to package.json

# Monthly full cleanup
.\cleanup.ps1
```

### Monitor Size
```powershell
# Check current workspace size
Get-ChildItem -Recurse | Measure-Object -Property Length -Sum | Select-Object @{Name="Size(GB)";Expression={$_.Sum / 1GB}}
```

---

## 🎯 Recommended Workflow

### For Code Review
1. Clone repo
2. Skip `npm install` entirely
3. Read code in VS Code
4. Use GitHub Copilot for analysis

### For Development
1. Clone repo
2. `npm install` only in directories you're actively working on
3. Start services as needed (not all at once)
4. Use `.ps1` scripts to launch specific subsystems

### For Testing
1. Full install once: `npm run setup` (if script exists)
2. Keep dependencies installed
3. Clean build artifacts regularly: `npm run clean`

---

## 📈 Expected Results

| Action | Before | After | Savings |
|--------|--------|-------|---------|
| Initial clone | 10-15 GB | 10 MB | ~99% |
| After lean install | 10-15 GB | 2-3 GB | ~75% |
| After full install | 10-15 GB | 4-6 GB | ~55% |
| With Docker | 10-15 GB | 500 MB + images | ~95% local |

---

## ⚠️ Important Notes

1. **Don't commit**:
   - `node_modules/` (already in .gitignore)
   - `.venv/` or `venv/`
   - `*.sqlite`, `*.faiss` (ephemeral data)

2. **Do commit**:
   - `package.json`, `package-lock.json`
   - `requirements.txt`
   - All source code

3. **After cleanup**, reinstall with:
   ```powershell
   npm install  # Node dependencies
   pip install -r services\memory\requirements.txt  # Python deps
   ```

---

**Questions?** Check `README.md` or `INSTALL.md` for setup instructions.
