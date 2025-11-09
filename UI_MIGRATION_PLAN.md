# ⚡ ASTRA UI — Unification Roadmap

**STATUS:** Discovery Complete → Planning Phase  
**PRIORITY:** P0 (Required before Phase 4 Observability)  
**EFFORT:** 3-5 days (depending on realm migration decisions)  
**COMPLETION:** 7/10 deliverables created

---

## 📊 Current State

### ✅ Working (93% Complete)
- **Canonical Codebase:** `astra-os/apps/pantheon` - Zero errors, fully migrated
- **Phase 1-3:** Infrastructure, components, 5 realm migrations complete
- **Performance:** 900ms build, code-splitting active
- **Tech Stack:** React 18 + TanStack (Router/Query) + Zustand + Radix UI

### ⚠️ Issues Discovered
- **96 UI files** across 5 distinct codebases
- **3 parallel implementations** (pantheon_ui, astra-os/src, astra-os/apps/pantheon)
- **4 missing realms** (Lumen, Seraph, Obelisk, Aetherglass) - 1,521 lines total
- **12 duplicate files** (App.tsx 3x, shell components 2x each)
- **10 orphaned components** (Plugin UI, Evolution UI, Web UI)
- **3 Tailwind configs**, 2+ theme files, multiple package.json files

---

## 🎯 Consolidation Goals

### Primary Objectives
1. **Single Canonical Codebase** - All UI in `astra-os/apps/pantheon`
2. **Zero Duplicates** - Delete/deprecate all redundant files
3. **Complete Feature Set** - Migrate or document missing realms
4. **Clean Dependencies** - Unified build configs, no orphaned code
5. **Ready for Phase 4** - Observability layer can proceed

### Success Criteria
- [ ] UI_COMPONENT_MAP.json shows 0 unresolved duplicates
- [ ] TypeScript compilation: 0 errors
- [ ] `pnpm dev` runs without issues
- [ ] All routes render correctly
- [ ] Backend integrations functional
- [ ] Performance budget maintained (170KB target)

---

## 📋 Deliverables Status

### ✅ Completed (3/10)
1. **UI_DEEP_SCAN_REPORT.md** - Comprehensive findings (58KB, 850+ lines)
2. **UI_COMPONENT_MAP.json** - Component inventory with metadata
3. **UI_ROUTES_MAP.json** - Route mapping and migration patterns

### 🔄 In Progress (7/10)
4. **UI_MIGRATION_PLAN.md** (THIS FILE) - Step-by-step consolidation
5. **UI_STATE_MAP.md** - State management inventory
6. **UI_THEME_MERGE_PLAN.md** - Token unification strategy
7. **UI_DEPRECATIONS.md** - Files to remove with rationale
8. **UI_GAPS_TODO.md** - Remaining work and open questions
9. **UI_CHANGELOG_MERGE.md** - Human-readable summary
10. **patches/** - Atomic migration patches

---

## 🚀 Migration Plan

### Phase 1: Critical Cleanup (Day 1 - 4 hours)

#### 1.1 Delete Deprecated Entry Points ✅ SAFE
**Impact:** Zero risk (files superseded)

```bash
# Verify canonical is working
cd astra-os/apps/pantheon
pnpm dev  # Should start on http://localhost:3000

# Delete superseded versions
rm astra-os/src/App.tsx
rm astra-os/src/main.tsx

# Verify no imports reference deleted files
git grep "from.*astra-os/src/App"
git grep "import.*astra-os/src/main"
```

**Validation:**
- [ ] Dev server still starts
- [ ] No import errors
- [ ] Git shows clean deletion

---

#### 1.2 Audit Root UI Components 🔍 INVESTIGATION
**Impact:** Unknown until read

```bash
# Read potentially conflicting components
# Compare APIs with canonical versions

Files to audit:
- src/components/ui/select.tsx  (may conflict with Radix Select)
- src/components/ui/card.tsx    (useful addition?)
- src/components/ui/badge.tsx   (useful addition?)
```

**Decision Matrix:**
```
IF API compatible with canonical:
  → Alias imports to canonical location
  
IF useful addition (card, badge):
  → Copy to canonical src/components/ui/
  → Delete root version
  → Update imports

IF incompatible/unused:
  → Check usage with git grep
  → Deprecate if no consumers
```

**Actions:**
- [ ] Read each file
- [ ] Compare with canonical patterns
- [ ] Check for consumers: `git grep "from.*components/ui/(select|card|badge)"`
- [ ] Decide: Integrate, Alias, or Deprecate

---

#### 1.3 Verify Theme Files 📐 VERIFICATION
**Impact:** Low (likely duplicate)

```bash
# Check if duplicate
diff astra-os/apps/pantheon/src/tokens/theme.ts \
     astra-os/apps/pantheon/src/core/theme.ts

# IF identical:
rm astra-os/apps/pantheon/src/core/theme.ts
git grep "from.*core/theme"  # Update imports if any

# IF different:
# Merge differences into tokens/theme.ts
# Delete core/theme.ts
```

**Actions:**
- [ ] Read both theme files
- [ ] If identical: Delete duplicate
- [ ] If different: Merge unique tokens
- [ ] Update any imports

---

### Phase 2: Backend Service Discovery (Day 1 - 2 hours)

#### 2.1 Check Running Services 🔌 CRITICAL
**Impact:** Determines realm migration strategy

```bash
# Test known services (should return 200)
curl http://localhost:7007/health  # Memory (DreamGrove) ✅
curl http://localhost:7701/health  # Sigil (SigilGate) ✅
curl http://localhost:7703/health  # Supervisor (Weaver) ✅

# Test unknown services (legacy realms)
curl http://localhost:8000/health  # Main ASTRA API?
curl http://localhost:7xxx/health  # Chat service (Lumen)?
curl http://localhost:7xxx/health  # Voice service (Seraph)?
curl http://localhost:7xxx/health  # Notes service (Obelisk)?

# Check Python services directory
ls astra-os/services/
# Expected: memory/, sigil_gate/, supervisor/, (chat/voice/notes?)

# Search for service definitions
git grep "class.*ChatService"
git grep "class.*VoiceService"
git grep "class.*NotesService"
```

**Decision Tree:**
```
FOR EACH LEGACY REALM:
  
  IF backend service exists:
    PRIORITY = HIGH (Lumen) or MEDIUM (Seraph, Obelisk)
    ACTION = Migrate to canonical with TanStack patterns
    EFFORT = 2-5 days depending on complexity
  
  ELSE IF can use localStorage:
    PRIORITY = MEDIUM (Obelisk notes)
    ACTION = Migrate with localStorage instead
    EFFORT = 1-2 days
  
  ELSE IF pure UI:
    PRIORITY = LOW (Aetherglass browser)
    ACTION = Easy migration, no backend needed
    EFFORT = 1 day
  
  ELSE:
    ACTION = Document in UI_GAPS_TODO.md for future consideration
    EFFORT = 0 (deferred)
```

**Actions:**
- [ ] Run curl health checks
- [ ] Search for backend service code
- [ ] Document findings in table
- [ ] Prioritize realms for migration

---

### Phase 3: Realm Migration (Day 2-3 - Variable)

**ONLY PROCEED WITH REALMS WHERE BACKEND EXISTS OR IS NOT NEEDED**

#### 3.1 Lumen (Chat) Migration 💬 IF BACKEND EXISTS
**Priority:** HIGH  
**Complexity:** MEDIUM  
**Effort:** 2-3 days  
**Lines:** 373

**Prerequisites:**
- [ ] Chat backend service running (port 7xxx)
- [ ] API endpoints: POST /chat/send, GET /agents/list, GET /chat/history

**Steps:**
1. Create route in `astra-os/apps/pantheon/src/routes.tsx`:
```typescript
{
  path: '/lumen',
  component: lazy(() => import('./realms/Lumen')),
  // ... metadata
}
```

2. Create realm file `astra-os/apps/pantheon/src/realms/Lumen.tsx`:
```typescript
// Copy from pantheon_ui/src/realms/lumen/LumenChat.tsx
// Update imports to canonical versions
// Replace astraAPI with canonical client
// Add TanStack Query hooks
// Use Zustand UI store
// Apply design tokens
```

3. Add API methods to `astra-os/apps/pantheon/src/services/client.ts`:
```typescript
export const lumenAPI = {
  sendMessage: (message: string, agent: string) => 
    api<ChatResponse>('/chat/send', { method: 'POST', body: { message, agent } }),
  
  listAgents: () => 
    api<Agent[]>('/agents/list'),
  
  getHistory: (limit?: number) =>
    api<Message[]>('/chat/history', { params: { limit } }),
  
  health: () =>
    api<HealthResponse>('/chat/health'),
};

export const lumenKeys = {
  all: ['lumen'] as const,
  history: () => [...lumenKeys.all, 'history'] as const,
  agents: () => [...lumenKeys.all, 'agents'] as const,
};
```

4. Add to Spine navigation `astra-os/apps/pantheon/src/components/Spine.tsx`:
```typescript
const realms = [
  // ... existing realms
  { path: '/lumen', icon: '💬', label: 'Lumen', sigil: '◈' },
];
```

5. Test:
- [ ] Route renders: http://localhost:3000/lumen
- [ ] Backend connects
- [ ] Agents load
- [ ] Messages send/receive
- [ ] TypeScript compiles
- [ ] Keyboard shortcuts work

---

#### 3.2 Seraph (Voice) Migration 🎤 IF BACKEND EXISTS
**Priority:** MEDIUM  
**Complexity:** HIGH  
**Effort:** 4-5 days  
**Lines:** 487

**Prerequisites:**
- [ ] Voice backend service (Whisper? port 7xxx)
- [ ] API endpoints: POST /voice/transcribe, POST /voice/synthesize

**Considerations:**
- WebRTC audio handling
- MediaRecorder API
- Audio visualization (canvas)
- Text-to-speech integration
- Push-to-talk vs continuous
- Session management

**Decision:**
```
IF backend exists AND voice is v1.0 priority:
  → Migrate (4-5 days effort)
ELSE:
  → Defer to v1.1, document in UI_GAPS_TODO.md
```

---

#### 3.3 Obelisk (Notes) Migration 📝 BACKEND OR LOCALSTORAGE
**Priority:** MEDIUM  
**Complexity:** MEDIUM  
**Effort:** 3-4 days (backend) OR 1-2 days (localStorage)  
**Lines:** 403

**Two Options:**

**Option A: Backend Integration (IF service exists)**
```typescript
export const obeliskAPI = {
  listNotes: () => api<Note[]>('/notes'),
  getNote: (id: string) => api<Note>(`/notes/${id}`),
  createNote: (note: CreateNotePayload) => 
    api<Note>('/notes', { method: 'POST', body: note }),
  updateNote: (id: string, updates: UpdateNotePayload) =>
    api<Note>(`/notes/${id}`, { method: 'PUT', body: updates }),
  deleteNote: (id: string) =>
    api<void>(`/notes/${id}`, { method: 'DELETE' }),
  searchNotes: (query: string) =>
    api<Note[]>('/notes/search', { params: { q: query } }),
};
```

**Option B: LocalStorage (IF no backend)**
```typescript
// Use localStorage similar to AetherLoom pattern
const notesStore = {
  getAll: () => JSON.parse(localStorage.getItem('astra-notes') || '[]'),
  get: (id: string) => notesStore.getAll().find(n => n.id === id),
  save: (note: Note) => {
    const notes = notesStore.getAll();
    const index = notes.findIndex(n => n.id === note.id);
    if (index >= 0) notes[index] = note;
    else notes.push(note);
    localStorage.setItem('astra-notes', JSON.stringify(notes));
  },
  delete: (id: string) => {
    const notes = notesStore.getAll().filter(n => n.id !== id);
    localStorage.setItem('astra-notes', JSON.stringify(notes));
  },
};
```

**Recommendation:** Start with LocalStorage (1-2 days), add backend later if needed.

---

#### 3.4 Aetherglass (Browser) Migration 🌐 PURE UI
**Priority:** LOW  
**Complexity:** LOW  
**Effort:** 1 day  
**Lines:** 258

**Easiest migration** (no backend, pure UI):
1. Copy component
2. Update to canonical patterns
3. Add route
4. Done

**Decision:**
```
IF browser UI is needed for demos/docs:
  → Migrate (1 day, easy)
ELSE:
  → Defer to later (not critical for v1.0)
```

---

### Phase 4: Orphaned Components (Day 3 - 2 hours)

#### 4.1 Plugin UI System 🔌 DECISION REQUIRED
**Files:** PluginUIController, PluginNotifications, PermissionRequestDialog  
**Location:** `src/ui/components/`

**Questions:**
1. Are plugins core to ASTRA v1.0?
2. Is plugin UI actively used?
3. Should plugins use Pantheon shell?

**Options:**

**A) INTEGRATE INTO PANTHEON**
- Add plugin status to Pulse sidebar
- Unify PermissionRequestDialog with ConsentCard
- Use canonical notification patterns
- **Effort:** 2-3 days

**B) KEEP SEPARATE**
- Plugins run as overlays (not in Pantheon)
- Independent styling
- Separate lifecycle management
- **Effort:** 0 (status quo)

**C) DEPRECATE**
- Remove plugin system entirely
- Delete UI components
- Update docs
- **Effort:** 1 day (cleanup)

**Recommendation:** Investigate plugin usage first, then decide.

```bash
# Check plugin usage
git grep "PluginUIController"
git grep "PluginNotifications"
git grep "PermissionRequestDialog"

# Check if any plugins registered
ls plugins/ || ls src/plugins/
```

---

#### 4.2 Evolution Components 🧠 DECISION REQUIRED
**Files:** CognitiveLayer, EvolutionVisuals, HeatmapVisualizer, MetamorphosisChamber, TelemetryDashboard, VoiceConfirmation  
**Location:** `src/astra/evolution/components/`

**Options:**

**A) CREATE /evolution REALM**
- Add new route `/evolution`
- Import components
- Display telemetry dashboards
- **Useful for Phase 4 observability**
- **Effort:** 1-2 days

**B) INTEGRATE INTO EXISTING REALMS**
- TelemetryDashboard → AEON (agent overview)
- HeatmapVisualizer → DreamGrove (memory patterns)
- CognitiveLayer → Pulse sidebar
- **Effort:** 2-3 days (distributed integration)

**C) KEEP AS LIBRARY**
- Not user-facing UI
- Used programmatically
- No Pantheon integration
- **Effort:** 0 (status quo)

**Recommendation:** Option A (create realm) - aligns with Phase 4 observability goals.

---

#### 4.3 Web UI Components 🌐 INTEGRATION
**File:** EmotionalRadar  
**Location:** `web/ui/components/`

**Options:**
1. Add to Pulse sidebar (emotional state widget)
2. Add to AEON realm (agent emotional state)
3. Deprecate if unused

**Action:**
```bash
# Check usage
git grep "EmotionalRadar"

# IF used:
cp web/ui/components/EmotionalRadar.tsx \
   astra-os/apps/pantheon/src/components/EmotionalRadar.tsx
# Add to Pulse or AEON

# IF unused:
# Delete and document deprecation
```

---

### Phase 5: Build Config Consolidation (Day 4 - 2 hours)

#### 5.1 Tailwind Configs 🎨
**Issue:** 3 Tailwind configurations

**Files:**
- `astra-os/apps/pantheon/tailwind.config.js` ✅ CANONICAL
- `astra-os/tailwind.config.js` (root level - for other apps?)
- `pantheon_ui/tailwind.config.js` ⚠️ DEPRECATED

**Actions:**
```bash
# Verify root config purpose
cat astra-os/tailwind.config.js
# IF used by other apps (gui, metrics, etc.):
#   KEEP (shared config)
# ELSE:
#   DELETE (unused)

# Delete legacy config
rm pantheon_ui/tailwind.config.js

# Update any imports
git grep "tailwind.config" pantheon_ui/
```

---

#### 5.2 Package.json Consolidation 📦
**Issue:** Multiple package.json files for UI

**Files:**
- `astra-os/apps/pantheon/package.json` ✅ CANONICAL
- `pantheon_ui/package.json` ⚠️ DEPRECATED
- `consent_ui/package.json` (separate app?)
- `console/package.json` (separate app)

**Actions:**
```bash
# Verify which are separate apps vs duplicates
# Keep: Separate apps with distinct purposes
# Delete: Duplicates after migration

# After pantheon_ui migration complete:
rm -rf pantheon_ui/
```

---

### Phase 6: Legacy Codebase Deprecation (Day 4 - 1 hour)

#### 6.1 Pantheon UI Deprecation 🗑️
**Location:** `pantheon_ui/`  
**Status:** After realm migration decisions

**If ALL legacy realms migrated or deferred:**
```bash
# Add deprecation notice (keep for one release)
cat > pantheon_ui/README.md << 'EOF'
# ⚠️ DEPRECATED

This codebase has been superseded by `astra-os/apps/pantheon`.

## Migration Path
- All components → `astra-os/apps/pantheon/src/components/`
- All realms → `astra-os/apps/pantheon/src/realms/`
- Routing → TanStack Router in `astra-os/apps/pantheon/src/routes.tsx`

## Removal
This directory will be deleted in v1.1.

For questions, see: UI_DEPRECATIONS.md
EOF

# Optionally: Move to archive/
mv pantheon_ui archive/pantheon_ui_legacy
```

**If SOME legacy realms still needed:**
```bash
# Keep pantheon_ui for now
# Add notice: "Contains Lumen/Seraph/Obelisk - awaiting backend"
# Document in UI_GAPS_TODO.md
```

---

### Phase 7: Validation & Testing (Day 5 - 4 hours)

#### 7.1 TypeScript Compilation ✅
```bash
cd astra-os/apps/pantheon
pnpm run build
# Expected: 0 errors, ~900ms build time
```

**Success Criteria:**
- [ ] 0 TypeScript errors
- [ ] 0 unused imports
- [ ] All routes resolve

---

#### 7.2 Development Server 🔥
```bash
cd astra-os/apps/pantheon
pnpm dev
# Expected: Starts on http://localhost:3000
```

**Manual Tests:**
- [ ] Navigate to each route (/, /aeon, /loom, /grove, /sigil, /weaver, /settings, /logs)
- [ ] Verify each realm renders
- [ ] Test backend integrations (DreamGrove search, SigilGate seal, Weaver jobs)
- [ ] Test keyboard shortcuts (Cmd+K, Alt+P, Alt+S, Alt+T)
- [ ] Test theme toggle
- [ ] Test Spine collapse
- [ ] Test Pulse visibility
- [ ] Test responsive layout

---

#### 7.3 Backend Integration ⚡
```bash
# Start all services
cd astra-os/services/memory && python server.py &  # 7007
cd astra-os/services/sigil_gate && npm start &    # 7701
cd astra-os/services/supervisor && npm start &    # 7703

# Test from UI
# DreamGrove: Search memories
# SigilGate: Seal operation (ConsentCard flow)
# Weaver: Create job, view jobs
```

**Success Criteria:**
- [ ] Memory search works
- [ ] Sigil seal/verify works
- [ ] Supervisor job creation works
- [ ] No CORS errors
- [ ] No 404 errors
- [ ] Trace IDs in requests

---

#### 7.4 Performance Budget 📊
```bash
# Build production bundle
pnpm build

# Check bundle sizes
ls -lh astra-os/apps/pantheon/dist/assets/*.js

# Target: First route ≤ 170KB gzip
# Current: ~500KB (needs optimization)
```

**If over budget:**
- Analyze bundle with `npx vite-bundle-visualizer`
- Lazy load heavy dependencies
- Tree-shake unused imports
- Consider dynamic imports

---

#### 7.5 Playwright Tests 🎭 (Optional)
```bash
# Run smoke tests
cd astra-os/apps/pantheon
pnpm test:e2e

# Key flows:
# - Navigation between realms
# - SigilGate consent flow
# - DreamGrove memory search
# - Keyboard shortcuts
```

---

### Phase 8: Documentation (Day 5 - 2 hours)

#### 8.1 Update Architecture Docs 📚
```markdown
# Update ARCHITECTURE.md

## UI Structure (v1.0)
- **Location:** `astra-os/apps/pantheon`
- **Stack:** React 18 + TanStack Router/Query + Zustand
- **Realms:** AEON, AetherLoom, DreamGrove, SigilGate, Weaver [+ migrated]
- **Deprecated:** `pantheon_ui/` (see UI_DEPRECATIONS.md)
```

---

#### 8.2 Create Migration Guide 📝
```markdown
# UI_MIGRATION_GUIDE.md

## For Developers

### Importing Components
❌ OLD: `import { Button } from 'pantheon_ui/components/ui'`
✅ NEW: `import { Button } from '@/components/ui/Button'`

### Routing
❌ OLD: `setCurrentRealm('grove')`
✅ NEW: `router.navigate({ to: '/grove' })`

### State Management
❌ OLD: `const { spineCollapsed } = usePantheonStore()`
✅ NEW: `const { collapseSpine } = useUI()`

### API Calls
❌ OLD: `await astraAPI.searchMemory(query)`
✅ NEW: `const { data } = useQuery({ queryKey: memoryKeys.search(query), queryFn: () => memoryAPI.search(query) })`
```

---

#### 8.3 Finalize Deprecation Docs ⚠️
**File:** `UI_DEPRECATIONS.md`

Content:
- List of deprecated files with rationale
- Replacement paths for each
- Breaking changes (if any)
- Timeline for removal (v1.1)
- Contact for questions

---

#### 8.4 Document Gaps 📋
**File:** `UI_GAPS_TODO.md`

Content:
- Missing legacy realms (if not migrated)
- Plugin UI integration (if deferred)
- Evolution components (if not integrated)
- Performance optimization backlog
- i18n/l10n prep
- RTL support
- Additional tests needed

---

### Phase 9: Create Patch Series (Day 5 - 2 hours)

#### 9.1 Generate Atomic Patches 🔧
```bash
# Each patch should be:
# - Atomic (one logical change)
# - Testable (can be applied and verified independently)
# - Reversible (can be rolled back)

mkdir -p patches

# Patch 1: Delete deprecated entry points
git diff > patches/0001-delete-deprecated-app-tsx.patch

# Patch 2: Consolidate UI primitives
git diff > patches/0002-consolidate-ui-primitives.patch

# Patch 3: Integrate Lumen realm (if migrated)
git diff > patches/0003-migrate-lumen-realm.patch

# Patch 4: Consolidate Tailwind configs
git diff > patches/0004-consolidate-tailwind-configs.patch

# Patch 5: Deprecate pantheon_ui
git diff > patches/0005-deprecate-pantheon-ui.patch

# Patch 6: Final cleanup
git diff > patches/0006-final-cleanup.patch
```

---

#### 9.2 Document Patch Application 📖
```markdown
# patches/README.md

## Applying Patches

### All at once:
```bash
for patch in patches/*.patch; do
  git apply --check $patch  # Dry run
  git apply $patch
done
```

### One by one:
```bash
git apply patches/0001-delete-deprecated-app-tsx.patch
pnpm dev  # Verify
git add -A && git commit -m "Apply patch 0001"
```

### Rollback:
```bash
git apply --reverse patches/0006-final-cleanup.patch
```
```

---

### Phase 10: Final Validation (Day 5 - 1 hour)

#### 10.1 Complete Checklist ✅
```markdown
- [ ] UI_COMPONENT_MAP.json shows 0 unresolved duplicates
- [ ] TypeScript compilation: 0 errors
- [ ] pnpm dev runs without issues
- [ ] All active routes render correctly
- [ ] Backend integrations functional (Memory, Sigil, Supervisor)
- [ ] Keyboard shortcuts work (Cmd+K, Alt+P/S/T)
- [ ] Theme toggle functional
- [ ] Deprecated files documented
- [ ] Migration guide created
- [ ] All 10 deliverables complete
```

---

#### 10.2 Generate Changelog 📄
**File:** `UI_CHANGELOG_MERGE.md`

```markdown
# UI Consolidation Changelog

## Summary
Unified ASTRA UI into single canonical codebase (`astra-os/apps/pantheon`).

## Changes
- ✅ Removed 2 deprecated entry points (astra-os/src/App.tsx, main.tsx)
- ✅ Deleted 5 duplicate shell components (Halo, Spine, Pulse, Oracle x2)
- ✅ Consolidated Tailwind configs (3 → 1)
- ✅ [IF MIGRATED] Added Lumen/Seraph/Obelisk realms with TanStack patterns
- ✅ [IF INTEGRATED] Integrated evolution components into /evolution realm
- ✅ Deprecated pantheon_ui/ codebase (see UI_DEPRECATIONS.md)

## Benefits
- Single source of truth for UI code
- Consistent patterns (TanStack, Zustand, design tokens)
- Easier maintenance
- Better performance (code-splitting)
- Type-safe routing
- Zero duplicate dependencies

## Breaking Changes
- pantheon_ui imports no longer work (see UI_MIGRATION_GUIDE.md)
- Manual routing replaced by TanStack Router
- Old Zustand store replaced by new API

## Migration Path
See UI_MIGRATION_GUIDE.md for detailed migration steps.

## Rollback
All changes available as atomic patches in patches/ directory.
```

---

## 📅 Timeline

### Minimum Viable Consolidation (3 days)
**Scope:** Critical cleanup only, defer realm migrations

- **Day 1 (4h):** Phase 1 (delete deprecated), Phase 2 (check backends)
- **Day 2 (6h):** Phase 4 (orphaned components), Phase 5 (build configs)
- **Day 3 (6h):** Phase 6-10 (deprecation, validation, docs, patches)

**Result:** Clean canonical codebase, missing realms documented

---

### Full Migration (5 days)
**Scope:** All critical realms migrated

- **Day 1 (6h):** Phase 1-2 (cleanup + backend discovery)
- **Day 2 (8h):** Phase 3.1 (Lumen migration) OR Phase 3.3 (Obelisk localStorage)
- **Day 3 (8h):** Phase 3.4 (Aetherglass) + Phase 4 (evolution realm)
- **Day 4 (6h):** Phase 5-6 (build configs + deprecation)
- **Day 5 (8h):** Phase 7-10 (validation + docs + patches + changelog)

**Result:** Complete consolidation, all features preserved

---

## 🎯 Recommendations

### Prioritize (Do Now)
1. ✅ **Phase 1.1** - Delete deprecated entry points (SAFE, immediate cleanup)
2. ✅ **Phase 2.1** - Check backend services (blocks realm decisions)
3. ✅ **Phase 3.3** - Migrate Obelisk with localStorage (MEDIUM complexity, HIGH value)
4. ✅ **Phase 3.4** - Migrate Aetherglass (LOW complexity, easy win)
5. ✅ **Phase 4.2A** - Create /evolution realm (useful for Phase 4 observability)

### Defer (Later)
1. **Phase 3.1** - Lumen (IF no backend, defer to v1.1)
2. **Phase 3.2** - Seraph (HIGH complexity, defer unless critical)
3. **Phase 4.1** - Plugin UI (investigate first, then decide)

### Skip (Not Needed)
- Unused orphaned components (delete if no consumers)
- Conflicting root components (deprecate if incompatible)

---

## 🚨 Risk Mitigation

### Risks
1. **Backend services missing** → Realm migration blocked
2. **Plugin UI actively used** → Integration effort increased
3. **Performance regression** → Bundle size grows

### Mitigations
1. **Document missing backends** in UI_GAPS_TODO.md for future phases
2. **Audit plugin usage first** with `git grep` before decisions
3. **Monitor bundle sizes** during migration, optimize if needed

---

## ✅ Next Immediate Actions

### Today
1. [ ] Run backend health checks (Phase 2.1)
2. [ ] Read root UI components (Phase 1.2)
3. [ ] Verify theme files (Phase 1.3)
4. [ ] Make realm migration decisions based on backend availability

### Tomorrow
1. [ ] Delete deprecated entry points (Phase 1.1)
2. [ ] Start easiest realm migration (Aetherglass or Obelisk)
3. [ ] Create /evolution realm if useful for observability

### This Week
1. [ ] Complete all chosen realm migrations
2. [ ] Consolidate build configs
3. [ ] Run full validation suite
4. [ ] Complete all 10 deliverables
5. [ ] Ready for Phase 4 (Observability)

---

**STATUS:** Planning Complete → Awaiting Backend Check Results  
**BLOCKERS:** None (can start Phase 1 immediately)  
**NEXT:** Execute Phase 1.1 (delete deprecated) + Phase 2.1 (check backends)

---

*Generated by ASTRA UI Deep Scan*  
*Saint Lucid Edition 333*
