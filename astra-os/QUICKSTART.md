# 🚀 ASTRA OS — Quick Start Guide

## Install & Run (5 minutes)

### 1️⃣ Install Dependencies

```powershell
# Pantheon UI
cd x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-os\apps\pantheon
npm install

# Memory Service
cd ..\..\services\memory
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2️⃣ Start Services

```powershell
cd x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-os
.\start.ps1
```

### 3️⃣ Access

- **Pantheon UI:** http://localhost:3000
- **Memory API:** http://127.0.0.1:7007

---

## 🎯 What to Try First

### Command Palette (Oracle)
Press `Ctrl+K` → Type "open" → See all realms  
Press `Alt+1` through `Alt+5` for direct navigation

### Sigil Gate (Consent Flow)
1. Navigate to Sigil Gate (`Alt+3`)
2. Review 10-file deletion plan
3. Click "Seal Scope & Approve"
4. Check journal entries at bottom

### Dream Grove (Memory)
1. Navigate to Dream Grove (`Alt+4`)
2. Click "+ Add Memory"
3. Enter: "Test semantic search capabilities"
4. Type query: "semantic"
5. Click "Search" — see results with latency

### Aether Loom (Research)
1. Navigate to Aether Loom (`Alt+2`)
2. Type quote in input: "Important finding"
3. Click "Capture Cite"
4. See cite appear in right panel
5. Click "+ Claim" → Add claim text
6. Watch coverage % update

### Weaver (Jobs)
1. Navigate to Weaver (`Alt+5`)
2. Click "+ Create Job" → Name it
3. Watch progress bar animate
4. Monitor SLO tiles (top)
5. Try "Pause" then "Resume"

---

## 🔑 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Open Oracle (command palette) |
| `Alt+1` | ÆON Deck |
| `Alt+2` | Aether Loom |
| `Alt+3` | Sigil Gate |
| `Alt+4` | Dream Grove |
| `Alt+5` | Weaver |
| `Escape` | Close Oracle |
| `↑` `↓` | Navigate Oracle results |
| `Enter` | Execute command |

---

## 📊 Performance Targets

| Feature | Target | How to Verify |
|---------|--------|---------------|
| Pantheon render | <1200ms | DevTools Performance tab |
| Oracle open | <200ms | Feels instant |
| Memory search | <120ms p95 | Check `latency_ms` in response |
| Cite capture | ≤2 clicks | Count: input + button |

---

## 🧪 Test Memory API

```powershell
# Health check
curl http://127.0.0.1:7007/health

# Add memory
curl -X POST http://127.0.0.1:7007/memory/add `
  -H "Content-Type: application/json" `
  -d '{"text": "Test memory fragment"}'

# Search
curl -X POST http://127.0.0.1:7007/memory/search `
  -H "Content-Type: application/json" `
  -d '{"query": "test", "top_k": 5}'

# Stats
curl http://127.0.0.1:7007/memory/stats
```

---

## 🐛 Troubleshooting

### Port already in use
```powershell
# Find process
netstat -ano | findstr :3000
netstat -ano | findstr :7007

# Kill process
taskkill /PID <PID> /F
```

### Python venv activation fails
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Module not found
```powershell
# Reinstall
cd services\memory
.\.venv\Scripts\Activate.ps1
pip install --upgrade -r requirements.txt
```

### Node-gyp errors (better-sqlite3)
```powershell
npm install --global windows-build-tools
cd services\sigil_gate
npm rebuild better-sqlite3
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `apps/pantheon/src/App.tsx` | Main router |
| `apps/pantheon/src/core/routes.ts` | Realm definitions |
| `apps/pantheon/src/core/commands.ts` | Oracle actions |
| `services/sigil_gate/journal.ts` | Consent log |
| `services/memory/embed_server.py` | Memory API |
| `start.ps1` | Launch script |
| `README.md` | Full documentation |
| `ACCEPTANCE_TESTS.md` | Test checklist |

---

## 🎨 UI Structure

```
┌─────────────── Halo ───────────────┐
│ ASTRA OS │ Time │ Scope │ Actions  │
├──────┬─────────────────────┬────────┤
│      │                     │        │
│      │                     │        │
│Spine │      Realm          │ Pulse  │
│ Nav  │      Content        │Metrics │
│      │                     │        │
│      │                     │        │
└──────┴─────────────────────┴────────┘
```

---

## 🌟 Cool Features to Demo

1. **Scope TTL Countdown** — Watch green pill count down in Halo
2. **Oracle Fuzzy Search** — Type partial command, see filtering
3. **Live Metrics** — Pulse tiles update every 2s
4. **Decay Visualization** — Memory items show colored decay bars
5. **Job Heartbeat** — Watch "Xms ago" increment in Weaver
6. **SLO Color Coding** — Thresholds trigger yellow/red states
7. **Immutable Journal** — Try updating seals table (fails)

---

## 📖 Documentation

- **README.md** — Full guide with architecture
- **INSTALL.md** — Detailed setup instructions
- **ACCEPTANCE_TESTS.md** — 400-line test checklist
- **COMPLETION_REPORT.md** — What was built
- **This file** — Quick reference

---

## 🚀 Next Steps After Setup

1. ✅ Run acceptance tests (`ACCEPTANCE_TESTS.md`)
2. ✅ Explore all 5 realms
3. ✅ Test memory persistence (stop/restart service)
4. ✅ Try all keyboard shortcuts
5. ✅ Check DevTools console (should be clean)
6. ✅ Measure performance (DevTools Performance tab)
7. ✅ Read `COMPLETION_REPORT.md` for architecture

---

## ⚡ One-Liner Setup (After Dependencies)

```powershell
cd x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-os; .\start.ps1
```

---

**That's it! You now have a working ASTRA vertical slice. Explore and enjoy! 🌌**
