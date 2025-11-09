# Week-3 Days 21-24: Operator Console MVP - Quick Reference

**Date**: 2025-11-02  
**Status**: COMPLETE ✅

---

## Quick Start (15 minutes)

### 1. Install Frontend Dependencies (5 min)
```powershell
cd console
npm install
```

### 2. Start Backend (2 min)
```powershell
cd ..
python launch_server.py
# Expected: http://localhost:8000
```

### 3. Start Frontend (2 min)
```powershell
cd console
npm run dev
# Expected: http://localhost:3000
```

### 4. Test Console (3 min)
Open browser: `http://localhost:3000`

### 5. Run Tests (3 min)
```powershell
python tests/week3/test_operator_console.py
# Expected: 7/7 PASSED (100%)
```

---

## Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Plan Preview Service | `src/services/plan_preview_service.py` | Generate visual plan graphs with risk scoring |
| Consent Service | `src/services/consent_service.py` | Track user consent decisions |
| Console API | `src/api/console_routes.py` | 9 FastAPI endpoints (`/console/*`) |
| Svelte App | `console/src/App.svelte` | Main UI with 4 tabs |

---

## API Endpoints

```bash
# Plan Preview
POST /console/plan/preview
GET  /console/plan/{plan_id}

# Consent
POST /console/consent
GET  /console/consent/{plan_id}/{action_id}
GET  /console/consent/history

# Memory (pending integration)
GET  /console/memory/browse

# Events (pending integration)
GET  /console/events
GET  /console/events/replay

# Health
GET  /console/health
```

---

## Usage Examples

### Create Plan Preview
```bash
curl -X POST http://localhost:8000/console/plan/preview \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan_001",
    "title": "Update Config",
    "description": "Modify nginx configuration",
    "actions": [
      {
        "type": "write",
        "description": "Write config file",
        "resources": {"file": "/etc/nginx/nginx.conf"},
        "dependencies": []
      }
    ]
  }'
```

### Record Consent
```bash
curl -X POST http://localhost:8000/console/consent \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan_001",
    "action_id": "plan_001_action_0",
    "decision": "approved",
    "reason": "Necessary for deployment",
    "user": "operator"
  }'
```

### Check Consent
```bash
curl http://localhost:8000/console/consent/plan_001/plan_001_action_0
```

---

## Risk Levels

| Risk | Color | Triggers |
|------|-------|----------|
| LOW | 🟢 Green | Read from non-sensitive paths |
| MEDIUM | 🟡 Amber | Write to non-critical locations |
| HIGH | 🔴 Red | Write to `/etc`, execute commands |
| CRITICAL | 🔴 Dark Red | Dangerous commands (`rm`, `format`) |

---

## Success Criteria

- [x] Plan preview generates visual graphs
- [x] Risk scoring accurate (low/medium/high/critical)
- [x] Consent recording persistent (JSONL)
- [x] Consent history retrievable
- [x] API endpoints operational (9 routes)
- [x] Frontend UI functional (4 tabs)
- [x] Local-first (no cloud services)

---

## Troubleshooting

### Frontend won't start
```powershell
cd console
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend routes not loading
Check `launch_server.py` output for:
```
✅ Operator Console routes loaded (/console/*)
```

If missing, ensure `src/api/console_routes.py` exists.

### API calls fail
1. Verify backend running: `http://localhost:8000/console/health`
2. Check Vite proxy in `console/vite.config.js`
3. Ensure port 3000 and 8000 available

---

## Next Steps

**Week-3 Days 25-28**: Memory Consolidation (Episodic → Semantic "Dreaming")

Say **"Proceed"** when ready.
