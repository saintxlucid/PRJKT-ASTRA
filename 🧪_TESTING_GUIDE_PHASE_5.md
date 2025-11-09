# 🧪 ASTRA Phase 5 - Live Testing Guide

**Date:** November 4, 2025  
**Status:** Phase 5 at 75% - 3 Realms Fully Integrated  
**Servers:** Both running and accessible

---

## 🚀 Server Status

### Backend (FastAPI)
- **URL:** http://localhost:8000
- **Status:** ✅ Running
- **Process:** Separate PowerShell window
- **Port Test:** TcpTestSucceeded = True
- **API Docs:** http://localhost:8000/docs (Swagger UI)

### Frontend (Vite + React)
- **URL:** http://localhost:3333
- **Status:** ✅ Running
- **Browser:** Simple Browser opened in VS Code

---

## 🎯 Test Scenarios - Ready to Execute

### Test 1: ÆON Deck - Real-Time Agent Monitoring

**Steps:**
1. Open http://localhost:3333 in browser
2. Default view is ÆON Deck
3. **Look for:** "● Live" indicator in header (green = connected)
4. **Observe:** 4 agent cards with progress bars
5. **Wait 5 seconds:** Watch progress bars update automatically
6. **Verify:** Agent names, status, current tasks updating

**Expected Behavior:**
- WebSocket connects immediately
- "● Live" appears in green
- Agents: Cognitive Core, Memory Weaver, Research Specialist, Code Architect
- Progress bars animate every 5 seconds
- Memory Weaver progress increases (78% → 83% → 88%...)
- Research Specialist progress increases (45% → 50% → 55%...)

**Backend Logs to Watch:**
```
INFO: WebSocket connection accepted
INFO: Sending agent updates every 5 seconds
```

---

### Test 2: Lumen Chat - Real Backend Responses

**Steps:**
1. Click "Lumen" in left sidebar (chat icon)
2. **Verify:** 4 agent selector buttons at top
3. Select "Cognitive Core" (should highlight)
4. Type message: "Hello ASTRA!"
5. Press Enter or click Send
6. **Observe:** Loading indicator (animated dots)
7. **Wait:** Response appears (~500ms)

**Expected Response:**
```
Assistant: Cognitive Core: Hello ASTRA! [Your message received]
Tokens: ~15
Timestamp: Current time
```

**Try Different Agents:**
- "Memory Weaver" - Message about memory consolidation
- "Research Specialist" - Message about research query
- "Code Architect" - Message about code generation

**Backend Logs to Watch:**
```
INFO: POST /api/chat - 200 OK
INFO: Agent: cognitive-core
INFO: Tokens: ~15
```

---

### Test 3: Obelisk - Full CRUD Note Operations

#### Part A: Load Notes (GET)
**Steps:**
1. Click "Obelisk" in left sidebar (book icon)
2. **Observe:** Loading spinner
3. **After 1-2 seconds:** Note list appears (or "No notes yet")

**Expected:**
- Empty state: "No notes yet. Create your first one!"
- Or: Demo notes if backend has data

#### Part B: Create Note (POST)
**Steps:**
1. Click "+ New Note" button (top right of sidebar, blue icon)
2. **Observe:** New note appears: "Untitled Note"
3. **Verify:** Note is selected, editor opens
4. Backend should log:
   ```
   INFO: POST /api/notes - 200 OK
   ```

#### Part C: Edit & Save Note (PUT)
**Steps:**
1. In title field: Type "My First ASTRA Note"
2. In editor: Type:
   ```markdown
   # Hello World
   
   This is my first note in ASTRA OS!
   
   ## Features I Love
   - Real-time updates
   - Backend persistence
   - Markdown support
   ```
3. Click "Save" button (top right, teal)
4. **Observe:** Button changes to "Saving..." then back to "Save"
5. **Verify:** No error banner appears

**Backend Logs:**
```
INFO: PUT /api/notes/note-XXXXX - 200 OK
```

#### Part D: Create Second Note
**Steps:**
1. Click "+ New Note" again
2. Title: "ASTRA Architecture"
3. Content:
   ```markdown
   # ASTRA Components
   
   1. Pantheon UI (React)
   2. Sigil Gate (Rust)
   3. Dream Grove (Python)
   4. Backend API (FastAPI)
   ```
4. Add tags: Type "architecture", "technical" in tag field
5. Click "Save"

#### Part E: Switch Between Notes
**Steps:**
1. Click first note in sidebar
2. **Verify:** Content loads immediately
3. Click second note
4. **Verify:** Content switches
5. **Observe:** Modified timestamps update

#### Part F: Delete Note (DELETE)
**Steps:**
1. Select a note
2. Click trash icon (next to Save button)
3. **Dialog appears:** "Delete 'Note Title'?"
4. Click OK/Yes
5. **Observe:** Note disappears from sidebar
6. **Verify:** Next note auto-selects

**Backend Logs:**
```
INFO: DELETE /api/notes/note-XXXXX - 200 OK
```

---

## 🔍 Visual Indicators to Look For

### Connection Status
- **ÆON Deck:** "● Live" (green) = WebSocket connected
- **ÆON Deck:** "○ Disconnected" (red) = WebSocket down

### Loading States
- **Obelisk:** Spinner + "Loading notes..." = Fetching from backend
- **Lumen Chat:** Animated dots = Waiting for response
- **Obelisk:** "Saving..." = PUT request in progress

### Error Handling
- **Red banner** appears if API call fails
- **Error message** shows what went wrong
- **Example:** "Failed to save note: Network error"

### Real-Time Updates
- **ÆON Deck:** Progress bars smoothly animate
- **Agent status** changes: idle → active → busy
- **Token counter** (Lumen) increments after each message

---

## 📊 Backend API Testing (Manual)

### Option A: Swagger UI
1. Open: http://localhost:8000/docs
2. Interactive API documentation
3. Try endpoints directly in browser
4. See request/response schemas

### Option B: Health Check
```
http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "agents": 4,
  "active_connections": 1,
  "timestamp": "2025-11-04T12:00:00Z"
}
```

### Option C: List Agents
```
http://localhost:8000/api/agents
```

**Expected Response:**
```json
[
  {
    "id": "cognitive-core",
    "name": "Cognitive Core",
    "status": "online",
    "current_task": "Ready for instructions",
    "progress": 0,
    "last_active": "2025-11-04T12:00:00Z"
  },
  ...
]
```

---

## 🐛 Troubleshooting

### Issue: "○ Disconnected" in ÆON Deck
**Solution:**
1. Check backend terminal - is it running?
2. Verify port 8000: `Test-NetConnection -ComputerName localhost -Port 8000`
3. Restart backend if needed

### Issue: "Failed to load notes" in Obelisk
**Solution:**
1. Open browser console (F12)
2. Check Network tab for 500/404 errors
3. Verify backend logs for errors
4. Check API endpoint: http://localhost:8000/api/notes

### Issue: Chat not responding
**Solution:**
1. Check backend logs for POST /api/chat
2. Verify agent_id is valid
3. Try different agent selector
4. Refresh page if WebSocket died

### Issue: Save button stays "Saving..."
**Solution:**
1. Check Network tab - did PUT succeed?
2. Look for error banner (red alert)
3. Verify note has valid ID
4. Check backend logs for 400/500 errors

---

## ✅ Success Criteria Checklist

After testing, verify:

- [ ] ÆON Deck shows "● Live" status
- [ ] Agent progress bars update every 5 seconds
- [ ] At least 2 agents show progress > 0%
- [ ] Lumen Chat sends message successfully
- [ ] Backend responds with agent name in message
- [ ] Token counter shows non-zero value
- [ ] Obelisk loads without errors
- [ ] Can create new note via UI
- [ ] Can edit note title and content
- [ ] Save button works (no error banner)
- [ ] Can switch between multiple notes
- [ ] Can delete note with confirmation
- [ ] No console errors (F12 → Console tab)
- [ ] Backend logs show successful API calls

---

## 📸 Expected UI Screenshots

### ÆON Deck
```
┌─────────────────────────────────────────┐
│ ÆON Deck ∞              [● Live]        │
│ Monday, November 4, 2025  12:00:00 PM   │
├─────────────────────────────────────────┤
│ Flow State: DEEP                        │
│ Level: 67% ████████░░                   │
│ Duration: 42 minutes                    │
├─────────────────────────────────────────┤
│ ┌─────────┐ ┌──────────┐ ┌───────────┐ │
│ │Cognitive│ │  Memory  │ │ Research  │ │
│ │  Core   │ │  Weaver  │ │Specialist │ │
│ │ 0%  ░░░ │ │ 78% ████ │ │ 45%  ███░ │ │
│ └─────────┘ └──────────┘ └───────────┘ │
└─────────────────────────────────────────┘
```

### Lumen Chat
```
┌─────────────────────────────────────────┐
│ [Cognitive] [Memory] [Research] [Code]  │
├─────────────────────────────────────────┤
│ User: Hello ASTRA!                      │
│                                         │
│ Assistant: Cognitive Core: Hello ASTRA! │
│ [Your message received]                 │
│ ⚡ Tokens: 15                           │
├─────────────────────────────────────────┤
│ Type your message...         [Send]     │
└─────────────────────────────────────────┘
```

### Obelisk
```
┌──────────┬─────────────────────────────┐
│          │ My First ASTRA Note    [🗑] │
│ Notes    │ [Download] [Save]           │
│ [Search] ├─────────────────────────────┤
│          │ # Hello World               │
│ + New    │                             │
│          │ This is my first note...    │
│ ┌──────┐ │                             │
│ │First │ │ ## Features I Love          │
│ │Note  │ │ - Real-time updates         │
│ │📄    │ │ - Backend persistence       │
│ └──────┘ │ - Markdown support          │
│ ┌──────┐ │                             │
│ │Arch  │ │                             │
│ │📄    │ │                             │
│ └──────┘ │                             │
└──────────┴─────────────────────────────┘
```

---

## 🎉 Demonstration Script

**For a quick demo (5 minutes):**

1. **Open ÆON Deck** (0:30)
   - Point out "● Live" status
   - Watch one agent progress update
   - Note: "This is real WebSocket data updating every 5 seconds"

2. **Switch to Lumen Chat** (1:30)
   - Select "Cognitive Core"
   - Send: "What can you help me with?"
   - Show response with token count
   - Note: "Backend processes each message through FastAPI"

3. **Navigate to Obelisk** (3:00)
   - Click "+ New Note"
   - Title: "Live Demo"
   - Content: "# ASTRA is working!\n\nAll 3 realms integrated."
   - Click "Save"
   - Note: "Note is now persisted in backend"
   - Create second note
   - Switch between notes
   - Delete first note
   - Note: "Full CRUD operations working"

**Total demo time: 5 minutes**

---

## 📝 Testing Notes

**What's Integrated (Working):**
- ✅ Real-time WebSocket updates (ÆON Deck)
- ✅ Chat API with agent routing (Lumen)
- ✅ Notes CRUD operations (Obelisk)
- ✅ Loading states and spinners
- ✅ Error handling and messages
- ✅ Connection status indicators

**What's Mock Data (Not Integrated):**
- ⏳ Voice transcription (Seraph Voice)
- ⏳ Voice synthesis (Seraph Voice)
- ⏳ Research sources (Aether Loom)
- ⏳ Browser history (Aetherglass)

**Known Limitations:**
- Backend uses in-memory storage (data lost on restart)
- Chat responses are echoes (no LLM yet)
- Voice endpoints are placeholders
- No authentication/users

---

**Ready to test!** Open http://localhost:3333 and follow the scenarios above. 🚀

**Phase 5 Status:** 75% Complete - 3 of 6 realms fully functional with backend integration!
