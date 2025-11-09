# ASTRA OS — Acceptance Test Guide

## Test Execution Checklist

Run through these tests to verify the walking skeleton meets all acceptance criteria.

---

## 🎨 Day 1-3: Pantheon Shell

### Halo (Top Bar)
- [ ] Clock displays and updates every second
- [ ] Scope pill shows "read-only" with TTL countdown
- [ ] TTL counts down from 5:00 to 0:00
- [ ] Quick action buttons render (Oracle, Settings)
- [ ] ASTRA logo visible and styled correctly

**Performance:**
- [ ] Initial render < 1200ms (check DevTools Performance tab)

---

### Spine (Left Navigation)
- [ ] All 5 realms visible with sigils: ∞ ⌘ ✠ ◈ ⚡
- [ ] Clicking realm navigates to correct page
- [ ] Active realm highlighted with blue background
- [ ] Instruments section shows Oracle + Pulse
- [ ] System section shows Settings + Logs
- [ ] Hover states work smoothly

**Hotkeys:**
- [ ] `Alt+1` → ÆON Deck
- [ ] `Alt+2` → Aether Loom
- [ ] `Alt+3` → Sigil Gate
- [ ] `Alt+4` → Dream Grove
- [ ] `Alt+5` → Weaver

---

### Oracle (Command Palette)
- [ ] `Ctrl+K` opens Oracle modal
- [ ] `Escape` closes Oracle
- [ ] Search filters commands (try "open")
- [ ] Arrow keys navigate results
- [ ] Enter executes selected command
- [ ] Commands navigate to correct realms
- [ ] Shortcuts displayed (Alt+1, etc.)

**Performance:**
- [ ] Open/close transition < 200ms
- [ ] Search updates instantly (< 50ms)

---

### Pulse (Right Metrics)
- [ ] CPU, Memory, Req/s, Latency tiles visible
- [ ] Metrics update every 2 seconds
- [ ] Values change (simulated)
- [ ] Status colors work (green/yellow)
- [ ] SLO section shows 3 metrics
- [ ] SLO values displayed with units

---

## 🔒 Day 4-6: Sigil Gate

### Consent Modal
- [ ] "Sigil Gate ✠" heading visible
- [ ] Plan summary displays
- [ ] Diff preview shows 10 operations
- [ ] Each diff has colored badge (DELETE in red)
- [ ] File paths displayed correctly
- [ ] Scroll works for long lists

---

### Approval Flow
- [ ] Click "Seal Scope & Approve"
- [ ] Button shows "Processing..." briefly
- [ ] Green success message appears
- [ ] Journal entries display at bottom
- [ ] Approval logged with timestamp

**Verification:**
- [ ] Console logs: `Sealing plan:` with digest
- [ ] Console logs: `✓ Plan sealed and logged to journal`

---

### Rejection & Rollback
- [ ] Click "Reject" → red error message
- [ ] Click "Rollback Last" when sealed → success
- [ ] Rollback disabled when no approval
- [ ] Buttons disable during loading

---

### Journal Display
- [ ] Recent entries section visible
- [ ] Entries show timestamp, seal ID, digest
- [ ] Font is monospace
- [ ] Background color distinguishes entries

**Backend (if running):**
```powershell
cd services\sigil_gate
node --loader ts-node/esm -e "import journal from './journal.js'; console.log(journal.getRecentSeals())"
```
- [ ] Database created at `services/sigil_gate/journal.sqlite`
- [ ] Seals table has immutability triggers

---

## 📚 Day 7-9: Aether Loom

### Sources Panel
- [ ] Sources section visible (left side)
- [ ] 2 default PDF sources listed
- [ ] "+ Add Source" button works
- [ ] Prompt appears for source name
- [ ] New source added to list
- [ ] Hover highlights sources

---

### Reader
- [ ] Simulated PDF content visible
- [ ] Page indicator shows "Page 1 of 50"
- [ ] Highlighted text visible (yellow background)
- [ ] Input field for quotes present
- [ ] "Capture Cite" button enabled

---

### Cite Capture (2-click flow)
1. [ ] Type text in quote input
2. [ ] Click "Capture Cite"
3. [ ] New cite appears in right panel
4. [ ] Cite shows: doc name, page, text, timestamp
5. [ ] Multiple cites stack vertically

**Performance:**
- [ ] Cite capture < 100ms (instant)
- [ ] 2 clicks total: input focus + capture

---

### Claims Workspace
- [ ] "Claims & Cites" heading visible
- [ ] Coverage % badge shows (0% initially)
- [ ] "+ Claim" button works
- [ ] Prompt for claim text
- [ ] New claims appear
- [ ] Coverage updates when claims added

**Acceptance:**
- [ ] Add 3 cites → Coverage shows 0%
- [ ] Add 2 claims → Coverage shows 0%
- [ ] Link cite to claim → Coverage updates to 50%

---

## 🧠 Day 10-12: Dream Grove

### Memory Service Health Check
```powershell
cd services\memory
.\.venv\Scripts\Activate.ps1
python embed_server.py
```

Wait for startup, then:
```powershell
curl http://127.0.0.1:7007/health
```

**Expected:**
```json
{
  "status": "healthy",
  "model": "all-MiniLM-L6-v2",
  "index_size": 0,
  "embedding_dim": 384
}
```

- [ ] Service starts without errors
- [ ] Model loads (~500MB first time)
- [ ] Health endpoint returns 200

---

### UI — Stats Dashboard
- [ ] 4 stat tiles visible
- [ ] Index Size shows count
- [ ] Avg Decay calculates
- [ ] Query Latency shows ms
- [ ] Low Value count displayed

---

### Add Memory
- [ ] Click "+ Add Memory"
- [ ] Prompt for text
- [ ] Enter: "Test memory about semantic search"
- [ ] Memory appears in list
- [ ] Index size increments

**Backend Verification:**
```powershell
curl -X POST http://127.0.0.1:7007/memory/add `
  -H "Content-Type: application/json" `
  -d '{"text": "Sample memory for testing"}'
```

- [ ] Returns `{"id": 0, "latency_ms": ..., "index_size": 1}`

---

### Search Memories
- [ ] Type query: "semantic"
- [ ] Click "Search" or press Enter
- [ ] Results appear below (if matches)
- [ ] Each result shows: text, score, decay bar
- [ ] Latency displayed

**Performance Target:**
- [ ] Search completes < 120ms (check latency_ms)

**Backend Search:**
```powershell
curl -X POST http://127.0.0.1:7007/memory/search `
  -H "Content-Type: application/json" `
  -d '{"query": "semantic", "top_k": 5}'
```

- [ ] Returns results array
- [ ] Latency < 120ms

---

### Decay & Purge
- [ ] Wait or manually age memories
- [ ] Decay bars show colored gradient
- [ ] "Low Value" count > 0
- [ ] Click "Purge Low Value"
- [ ] Confirmation or instant purge
- [ ] Index size decreases
- [ ] Console logs purge operation

---

### Persistence
- [ ] Stop memory service (Ctrl+C)
- [ ] Check files created:
  - [ ] `services/memory/index.faiss`
  - [ ] `services/memory/memories.json`
- [ ] Restart service
- [ ] Console: `✓ Loaded X memories from disk`
- [ ] UI shows restored memories

---

## ⚡ Day 13-14: Weaver

### Job Creation
- [ ] Click "+ Create Job"
- [ ] Prompt for job name
- [ ] Enter: "Test background task"
- [ ] Job appears in table
- [ ] Status shows "RUNNING"
- [ ] Progress bar animates

---

### SLO Dashboard
- [ ] 4 SLO tiles visible:
  - [ ] Verify p95 (ms)
  - [ ] Consent p95 (ms)
  - [ ] Denial Count
  - [ ] Job Success Rate (%)
- [ ] Values update every 2s
- [ ] Colors change with thresholds (green/yellow/red)

---

### Heartbeat System
- [ ] Job shows "Heartbeat: Xs ago"
- [ ] Heartbeat age increments
- [ ] After 30s → "STALE" badge appears
- [ ] Progress increases over time

---

### Job Controls
**Running Job:**
- [ ] "Pause" button visible
- [ ] Click Pause → status changes to "PAUSED"
- [ ] Progress stops increasing
- [ ] Heartbeat stops updating

**Paused Job:**
- [ ] "Resume" button visible
- [ ] Click Resume → status "RUNNING"
- [ ] Progress resumes
- [ ] Heartbeat resets

**Kill Switch:**
- [ ] Running job has "Kill" button
- [ ] Click Kill → status "FAILED"
- [ ] Job turns red
- [ ] Controls disabled

---

### Simulate Mode
- [ ] Click "Simulate Mode"
- [ ] Button highlights yellow
- [ ] Info banner appears: "🎭 Simulate mode active"
- [ ] Click again to toggle off

---

## 📊 Overall Integration Tests

### Cross-Realm Navigation
- [ ] Navigate: AEON → Loom → Sigil → Grove → Weaver
- [ ] Each realm loads correctly
- [ ] No console errors
- [ ] Spine highlights active realm
- [ ] URL updates (if using router)

---

### Performance Validation

**Pantheon Interaction:**
- [ ] Open DevTools → Performance
- [ ] Record 10-second session
- [ ] Navigate all 5 realms
- [ ] Open Oracle 3 times
- [ ] Check flame graph: p95 < 1200ms for interactions

**Memory Query:**
```powershell
# Run 100 searches, measure p95
for($i=0; $i -lt 100; $i++) {
  curl -X POST http://127.0.0.1:7007/memory/search `
    -H "Content-Type: application/json" `
    -d '{"query": "test", "top_k": 5}'
}
```
- [ ] Calculate p95 from `latency_ms` field
- [ ] p95 < 120ms

---

### Console Error Check
- [ ] Open DevTools Console (F12)
- [ ] Navigate all realms
- [ ] Interact with all features
- [ ] Confirm: **0 errors**
- [ ] Warnings acceptable (React dev mode)

---

### Startup Script
```powershell
cd astra-os
.\start.ps1
```

- [ ] Memory service terminal opens
- [ ] Pantheon UI terminal opens
- [ ] Both services start without errors
- [ ] URLs displayed correctly

---

## 🎯 Acceptance Criteria Summary

| Feature | Target | Status |
|---------|--------|--------|
| Pantheon render | <1200ms | ☐ |
| Oracle open | <200ms | ☐ |
| Hotkeys | All working | ☐ |
| Consent flow | Approve + seal | ☐ |
| Journal | Immutable log | ☐ |
| Cite capture | ≤2 clicks | ☐ |
| Memory search | <120ms p95 | ☐ |
| Decay purge | Working | ☐ |
| Job heartbeat | 30s timeout | ☐ |
| SLO tiles | Color coded | ☐ |

---

## 🐛 Known Limitations (MVP)

These are acceptable for walking skeleton:

- [ ] Memory search: Mock filtering (needs full FAISS integration in UI)
- [ ] Sigil Gate: Stub rollback (doesn't restore files yet)
- [ ] Aether Loom: No actual PDF parsing
- [ ] FTS5 search: Not implemented
- [ ] Metrics: Simulated values (no real system probes)
- [ ] Weaver simulate: UI flag only (no actual simulation)

---

## ✅ Final Verification

Before marking complete:

1. [ ] All 5 realms accessible and functional
2. [ ] Oracle command palette works
3. [ ] Memory service running and persistent
4. [ ] Consent flow approves and logs
5. [ ] Performance targets met (1200ms, 120ms)
6. [ ] No critical console errors
7. [ ] Startup script works
8. [ ] README.md updated with instructions

---

**Test Duration:** ~30 minutes  
**Pass Criteria:** 90% of checkboxes ticked  
**Blocker Criteria:** Any feature completely broken

If all tests pass: **Walking skeleton SHIPPED ✅**
