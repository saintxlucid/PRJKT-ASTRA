# 🔍 ASTRA UI Deep Scan Report

**Generated:** January 2025  
**Scope:** Repository-wide UI audit and consolidation assessment  
**Status:** Phase 3 Complete (93%) → Consolidation Required Before Phase 4

---

## 📊 Executive Summary

### Critical Findings
- **96 UI files** discovered across **5 distinct codebases**
- **3 parallel implementations** of Pantheon UI exist simultaneously
- **4 legacy realms** (Lumen, Seraph, Obelisk, Aetherglass) not present in current version
- **Multiple duplicates**: App.tsx (3x), shell components (2x), configs (3x)
- **Current production** (astra-os/apps/pantheon) is **93% complete** with zero errors
- **Legacy codebase** (pantheon_ui) has **4 unique realms** requiring evaluation

### Recommended Action
**CONSOLIDATE NOW** - Unify all UI code into single canonical version before adding observability layer (Phase 4).

---

## 🗺️ Codebase Topology

### 1. **CANONICAL (Current Production)** ✅
**Location:** `astra-os/apps/pantheon/`  
**Status:** Active development, zero TypeScript errors, fully migrated  
**Tech Stack:**
- React 18.2.0 + TypeScript 5.3.0
- TanStack Router 1.134.15 (8 lazy-loaded routes)
- TanStack Query 5.90.7 (server state management)
- Zustand 5.0.8 (UI state)
- Radix UI + Framer Motion 12.23.24
- Tailwind CSS 3.4.0 with 300+ design tokens
- Vite 5.0.0 (900ms build time)

**File Count:** 14 core UI files

**Key Files:**
- `src/App.tsx` - Grid layout shell (Halo/Spine/Pulse/Oracle)
- `src/routes.tsx` - TanStack Router config (8 routes)
- `src/store/ui.ts` - Zustand store (170 lines, keyboard shortcuts)
- `src/services/client.ts` - TanStack Query + API client (300+ lines)
- `src/tokens/theme.ts` - Design tokens (300+ tokens, Obsidian theme)
- `src/components/` - Shell components (Halo, Spine, Pulse, Oracle, ConsentCard)
- `src/components/ui/` - UI primitives (Button, Input, Dialog, Tooltip)
- `src/realms/` - 5 realms (AEON, AetherLoom, DreamGrove, SigilGate, Weaver) ✅ ALL MIGRATED
- `src/views/` - Settings, Logs

**Vite Config:** `astra-os/apps/pantheon/vite.config.ts` (React plugin, path aliases)  
**Tailwind Config:** `astra-os/apps/pantheon/tailwind.config.js` (integrated with tokens)  
**Package.json:** 24 dependencies, 0 vulnerabilities

**Migration Status:**
- Phase 1 (Infrastructure): ✅ Complete
- Phase 2 (Components): ✅ Complete  
- Phase 3 (Realms): ✅ Complete (DreamGrove, Weaver, SigilGate)
- Phase 4 (Observability): ⏳ Pending consolidation

---

### 2. **LEGACY (Parallel Implementation)** ⚠️ DEPRECATED
**Location:** `pantheon_ui/`  
**Status:** Older parallel implementation, NO TanStack Router, missing modern features  
**Tech Stack:**
- React 18.2.0 + TypeScript 5.2.2
- Zustand 4.4.7 (older version)
- TanStack Query 5.14.2 (older version)
- NO TanStack Router (manual routing via RealmView component)
- Lucide React icons
- Tailwind CSS 3.3.6
- Vite 5.0.8

**File Count:** 11 UI files

**Key Files:**
- `src/App.tsx` - OLD VERSION (no TanStack Router)
- `src/main.tsx` - OLD entry point
- `src/store/pantheon-store.ts` - Simpler Zustand store (33 lines vs 170)
- `src/components/RealmView.tsx` - Manual routing switch statement
- `src/components/` - Shell components (Halo, Spine, Pulse, Oracle) - OLDER VERSIONS
- `src/realms/` - **7 realms:**
  - aeon/AeonDeck.tsx (similar to current)
  - aether-loom/AetherLoom.tsx (older version)
  - dream-grove/DreamGrove.tsx (pre-migration)
  - **lumen/LumenChat.tsx** ⚠️ NOT IN CURRENT (373 lines - Multi-agent chat interface)
  - **seraph/SeraphVoice.tsx** ⚠️ NOT IN CURRENT (487 lines - Voice interaction system)
  - **obelisk/Obelisk.tsx** ⚠️ NOT IN CURRENT (403 lines - Note management system)
  - **aetherglass/Aetherglass.tsx** ⚠️ NOT IN CURRENT (258 lines - Browser interface)

**Vite Config:** `pantheon_ui/vite.config.ts`  
**Tailwind Config:** `pantheon_ui/tailwind.config.js`  
**Package.json:** 13 dependencies (older versions)

**Missing Features vs Current:**
- ❌ No TanStack Router (manual routing)
- ❌ No modern state management patterns
- ❌ No ConsentCard integration
- ❌ No lazy-loaded routes
- ❌ No trace ID injection
- ❌ No design token system (300+ tokens)
- ❌ Older Zustand API

**Unique Features (Not in Current):**
- ✅ Lumen Chat (multi-agent chat interface with agent selection)
- ✅ Seraph Voice (voice interaction with audio visualization)
- ✅ Obelisk (note management system with tags/links)
- ✅ Aetherglass (browser interface with tabs/bookmarks)

**API Client:**
- Uses `@/lib/api/client` (not found in current)
- Different endpoint structure
- Different type definitions

**Decision Required:**
- Evaluate 4 unique realms for migration vs deprecation
- If migrating: Need to update to TanStack Router pattern
- If deprecating: Document rationale and alternatives

---

### 3. **ROOT UI COMPONENTS (Orphaned)** 🟡 SCATTERED
**Location:** `src/` (repository root)  
**Status:** Multiple isolated UI systems, not integrated with Pantheon

#### 3a. Plugin UI System
**Location:** `src/ui/components/`  
**Files:**
- `PluginUIController.tsx` - Plugin lifecycle UI management
- `PluginNotifications.tsx` - Toast/notification system
- `PermissionRequestDialog.tsx` - Permission consent UI

**Purpose:** UI layer for plugin system  
**Integration:** NOT connected to Pantheon shell  
**Decision Required:** Integrate into canonical Pantheon or keep separate?

#### 3b. Shadcn-Style Primitives
**Location:** `src/components/ui/`  
**Files:**
- `select.tsx` - Dropdown select component
- `card.tsx` - Card container component
- `badge.tsx` - Badge/pill component

**Conflict:** DUPLICATES canonical `astra-os/apps/pantheon/src/components/ui/`  
**API Differences:** May use different patterns vs Radix-based canonical versions  
**Decision Required:** Audit for API compatibility, deprecate or unify

#### 3c. Evolution Components
**Location:** `src/astra/evolution/components/`  
**Files:**
- `CognitiveLayer.tsx` - Brain visualization
- `EvolutionVisuals.jsx` - Evolution progress display
- `HeatmapVisualizer.jsx` - Data heatmap
- `MetamorphosisChamber.jsx` - Evolution chamber UI
- `TelemetryDashboard.jsx` - Metrics dashboard
- `VoiceConfirmation.jsx` - Voice interaction UI

**Purpose:** Specialized visualization components for evolution system  
**Status:** NOT accessible from Pantheon realms  
**Decision Required:** 
- Create "Evolution" realm in Pantheon?
- Keep as library components?
- Integrate into existing realms?

#### 3d. Web UI Components
**Location:** `web/ui/components/`  
**Files:**
- `EmotionalRadar.tsx` - Emotional state visualization

**Status:** Single isolated component  
**Decision Required:** Integrate into Pantheon or deprecate

---

### 4. **INTERMEDIATE (Superseded)** 🔴 DEPRECATED
**Location:** `astra-os/src/`  
**Files:**
- `App.tsx` - Pre-migration application shell
- `main.tsx` - Old entry point

**Status:** SUPERSEDED by `astra-os/apps/pantheon/`  
**Action:** DELETE after verification

---

### 5. **BUILD ARTIFACTS** 📦
**Locations:**
- `astra-os/vite.config.ts` (root level)
- `console/vite.config.js` (separate console app)
- Multiple `tailwind.config.js` files (3 distinct)
- Multiple `package.json` files

**Action:** Consolidate build configurations

---

## 📈 File Statistics

### Total UI Files by Location
```
astra-os/apps/pantheon/src/    14 files ✅ CANONICAL
pantheon_ui/src/                11 files ⚠️ LEGACY
src/ui/components/               3 files 🟡 PLUGIN UI
src/components/ui/               3 files 🟡 DUPLICATES
src/astra/evolution/components/  6 files 🟡 ORPHANED
web/ui/components/               1 file  🟡 ISOLATED
astra-os/src/                    2 files 🔴 DEPRECATED
---
TOTAL:                          40 files (96 including duplicates from search)
```

### Component Duplication Matrix
| Component | Canonical | Legacy | Root | Status |
|-----------|-----------|--------|------|--------|
| App.tsx | astra-os/apps/pantheon | pantheon_ui, astra-os/src | - | 3 versions ⚠️ |
| Halo | astra-os/apps/pantheon | pantheon_ui | - | 2 versions 🟡 |
| Spine | astra-os/apps/pantheon | pantheon_ui | - | 2 versions 🟡 |
| Pulse | astra-os/apps/pantheon | pantheon_ui | - | 2 versions 🟡 |
| Oracle | astra-os/apps/pantheon | pantheon_ui | - | 2 versions 🟡 |
| Button | astra-os/apps/pantheon | - | - | 1 version ✅ |
| Input | astra-os/apps/pantheon | - | - | 1 version ✅ |
| Dialog | astra-os/apps/pantheon | - | - | 1 version ✅ |
| Tooltip | astra-os/apps/pantheon | - | - | 1 version ✅ |
| select | - | - | src/components/ui | Conflicts? 🟡 |
| card | - | - | src/components/ui | Conflicts? 🟡 |
| badge | - | - | src/components/ui | Conflicts? 🟡 |

### Realm Coverage Matrix
| Realm | Canonical | Legacy | Lines | Backend API | Status |
|-------|-----------|--------|-------|-------------|--------|
| AEON | ✅ | ✅ | ~200 | Static UI | Migrated ✅ |
| AetherLoom | ✅ | ✅ | ~150 | LocalStorage | Migrated ✅ |
| DreamGrove | ✅ | ✅ | ~400 | Memory Service | Migrated ✅ |
| SigilGate | ✅ | ❌ | ~500 | Consent Service | Migrated ✅ |
| Weaver | ✅ | ❌ | ~300 | Supervisor Service | Migrated ✅ |
| Lumen | ❌ | ✅ | 373 | Chat Service | Missing 🔴 |
| Seraph | ❌ | ✅ | 487 | Voice Service | Missing 🔴 |
| Obelisk | ❌ | ✅ | 403 | Notes Service | Missing 🔴 |
| Aetherglass | ❌ | ✅ | 258 | Browser Service | Missing 🔴 |

**Missing Realms Analysis:**
1. **Lumen (LumenChat)** - 373 lines
   - Multi-agent chat interface
   - Agent selection (Cognitive Core, Memory Weaver, Research Specialist, Code Architect)
   - Streaming responses
   - Token counting
   - Export/copy/delete messages
   - Uses `astraAPI.sendChatMessage()`
   - **Backend Dependency:** Chat service API

2. **Seraph (SeraphVoice)** - 487 lines
   - Voice interaction system
   - Audio input/output visualization
   - Speech recognition
   - Text-to-speech
   - Push-to-talk mode
   - Session history
   - Uses `astraAPI.transcribeAudio()`, `astraAPI.synthesizeSpeech()`
   - **Backend Dependency:** Voice service API (Whisper model?)

3. **Obelisk** - 403 lines
   - Note management system (Obsidian-like)
   - Rich text editor
   - Tagging system
   - Wiki-style linking
   - Search functionality
   - Uses `astraAPI.getNotes()`, `astraAPI.updateNote()`
   - **Backend Dependency:** Notes service API

4. **Aetherglass** - 258 lines
   - Browser interface
   - Tab management
   - Bookmarks
   - Navigation controls
   - Static UI (no backend)
   - **Backend Dependency:** None (pure UI)

**Backend Service Status:**
- Memory Service (7007): ✅ Running (DreamGrove uses)
- Consent Service (7701): ✅ Running (SigilGate uses)
- Supervisor Service (7703): ✅ Running (Weaver uses)
- Chat Service: ❓ Unknown
- Voice Service: ❓ Unknown  
- Notes Service: ❓ Unknown

**Decision Matrix:**
```
                    Backend Exists?  UI Complete?  Priority
Lumen (Chat)        Unknown         Yes           HIGH (core feature)
Seraph (Voice)      Unknown         Yes           MEDIUM (advanced feature)
Obelisk (Notes)     Unknown         Yes           MEDIUM (productivity)
Aetherglass (Browser) N/A           Yes           LOW (static UI)
```

---

## 🏗️ Architecture Analysis

### State Management

#### Canonical (Zustand) ✅ MODERN
**File:** `astra-os/apps/pantheon/src/store/ui.ts` (170 lines)

**State:**
- Layout: `collapseSpine`, `showPulse`, `spineWidth`, `pulseWidth`
- Theme: `theme` (dark/light)
- Oracle: `oracleOpen`
- Navigation: `currentPath`
- Split view: `splitView`, `splitRatio`
- Preferences: `animationsEnabled`, `soundEnabled`, `compactMode`

**Actions:**
- `toggleSpine()`, `togglePulse()`
- `setTheme()`, `toggleTheme()`
- `openOracle()`, `closeOracle()`, `toggleOracle()`
- `setCurrentPath()`
- `toggleSplitView()`, `setSplitRatio()`
- `toggleAnimations()`, `toggleSound()`, `toggleCompactMode()`
- `reset()`

**Features:**
- ✅ Persistence (localStorage: `astra-ui-store`)
- ✅ Keyboard shortcuts (Cmd+K, Alt+P, Alt+S, Alt+T, Esc)
- ✅ Selectors for optimized re-renders
- ✅ Theme document root integration
- ✅ Partialize for selective persistence

#### Legacy (Zustand) ⚠️ SIMPLE
**File:** `pantheon_ui/src/store/pantheon-store.ts` (33 lines)

**State:**
- `currentRealm: ModuleId`
- `oracleOpen: boolean`
- `pulseVisible: boolean`
- `spineCollapsed: boolean`

**Actions:**
- `setCurrentRealm()`
- `setOracleOpen()`
- `setPulseVisible()`
- `setSpineCollapsed()`

**Differences:**
- ❌ No persistence
- ❌ No keyboard shortcuts
- ❌ No theme management
- ❌ No split view
- ❌ No preferences
- ❌ No selectors
- ❌ Simpler API (setters vs toggles)

**Migration Path:**
- Legacy components can use canonical store with minimal changes
- Add `useUI()` import
- Replace `usePantheonStore()` calls

---

### Routing

#### Canonical (TanStack Router) ✅ MODERN
**File:** `astra-os/apps/pantheon/src/routes.tsx`

**Routes:**
```typescript
/ (index)           → AEON
/aeon              → AEON
/loom              → AetherLoom
/sigil             → SigilGate
/grove             → DreamGrove
/weaver            → Weaver
/settings          → Settings
/logs              → Logs
404                → NotFound
```

**Features:**
- ✅ Lazy-loaded components (`React.lazy()`)
- ✅ Preload on hover (100ms delay)
- ✅ Type-safe route helpers
- ✅ Suspense boundaries
- ✅ Metadata per route (icon, color, sigil)

#### Legacy (Manual Routing) ⚠️ DEPRECATED
**File:** `pantheon_ui/src/components/RealmView.tsx`

**Routing:**
```typescript
if (currentRealm === 'aeon') return <AeonDeck />
if (currentRealm === 'lumen') return <LumenChat />
if (currentRealm === 'seraph') return <SeraphVoice />
// ... manual switch statements
```

**Issues:**
- ❌ No lazy loading
- ❌ No preloading
- ❌ No URL routing (all state-based)
- ❌ No browser back/forward
- ❌ No deep linking
- ❌ Not type-safe

**Migration Path:**
- Convert to TanStack Router routes
- Add route definitions in `routes.tsx`
- Update navigation to use `router.navigate()`

---

### Design System

#### Canonical (Design Tokens) ✅ COMPLETE
**File:** `astra-os/apps/pantheon/src/tokens/theme.ts` (300+ tokens)

**Token Categories:**
- **Colors:** Obsidian palette (bg, surface, border, text, accent, status)
  - Background: `#0A0A0B` (near-black)
  - Accent Gold: `#C9B37E`
  - Lucid Teal: `#10B981`
  - Lucid Violet: `#8B5CF6`
- **Typography:** Font families (Inter, Söhne, Mono)
- **Spacing:** 0-96px scale
- **Radius:** sm (2px) → 2xl (16px)
- **Shadows:** Soft glow effects
- **Motion:** Spring physics (mass: 0.9, stiffness: 220, damping: 28)
- **Z-index:** Layering system

**Integration:**
- ✅ Tailwind config extends tokens
- ✅ CSS variables generated
- ✅ Type-safe token access

#### Legacy (No Formal Tokens) ⚠️ AD-HOC
**Files:** Inline styles in components, Tailwind utility classes

**Issues:**
- ❌ No centralized token system
- ❌ Magic values scattered across components
- ❌ Inconsistent color usage
- ❌ No motion system

**Migration Path:**
- Import canonical theme tokens
- Replace inline colors with token references
- Update Tailwind config to use tokens

---

### API Layer

#### Canonical (TanStack Query) ✅ MODERN
**File:** `astra-os/apps/pantheon/src/services/client.ts` (300+ lines)

**QueryClient Config:**
```typescript
staleTime: 30_000ms
gcTime: 5_000ms
retry: 2
refetchOnWindowFocus: false
```

**API Helper:**
```typescript
api<T>(endpoint, options): Promise<T>
- Trace ID injection
- 30s timeout
- Error handling
- Type-safe responses
```

**Service APIs:**
- `memoryAPI`: `search()`, `add()`, `health()`
- `sigilAPI`: `seal()`, `verify()`, `journalDelete()`, `rollback()`, `health()`
- `supervisorAPI`: `createJob()`, `listJobs()`, `heartbeat()`, `health()`

**Query Keys:**
```typescript
memoryKeys: ['memory', 'search'], ['memory', 'health']
sigilKeys: ['sigil', 'verify'], ['sigil', 'journal']
supervisorKeys: ['supervisor', 'jobs'], ['supervisor', 'job', id]
```

#### Legacy (Unknown API) ⚠️ DIFFERENT
**File:** `pantheon_ui/src/lib/api/client` (NOT FOUND)

**References:**
```typescript
astraAPI.sendChatMessage()       // Lumen
astraAPI.transcribeAudio()       // Seraph
astraAPI.synthesizeSpeech()      // Seraph
astraAPI.getNotes()              // Obelisk
astraAPI.updateNote()            // Obelisk
```

**Issue:** API client not found in legacy codebase  
**Decision Required:** 
- Does backend support these endpoints?
- Need to create API client in canonical version
- Or deprecate realms if backend doesn't exist

---

## 🚨 Critical Issues

### 1. Multiple Entry Points 🔴 CRITICAL
**Problem:** 3 distinct `App.tsx` files exist

**Locations:**
1. `pantheon_ui/src/App.tsx` - Legacy implementation
2. `astra-os/src/App.tsx` - Intermediate version
3. `astra-os/apps/pantheon/src/App.tsx` - **CANONICAL**

**Impact:**
- Confusion: Which is the "real" app?
- Maintenance: Changes to one don't propagate
- Build: Multiple entry points may conflict

**Resolution:**
```
KEEP:   astra-os/apps/pantheon/src/App.tsx (CANONICAL)
DELETE: pantheon_ui/src/App.tsx (after realm evaluation)
DELETE: astra-os/src/App.tsx (superseded)
```

---

### 2. Shell Component Duplication 🟡 HIGH
**Problem:** Halo, Spine, Pulse, Oracle exist in 2 locations

**Canonical:** `astra-os/apps/pantheon/src/components/`
- Uses Zustand store
- Integrated keyboard shortcuts
- Modern motion system
- Full feature set

**Legacy:** `pantheon_ui/src/components/`
- Uses simpler store
- Manual event handling
- Basic animations
- Limited features

**Resolution:**
```
KEEP:   astra-os/apps/pantheon/src/components/ (CANONICAL)
DELETE: pantheon_ui/src/components/ (after migration)
ADD:    Redirect shims for one release
```

---

### 3. Missing Legacy Realms 🟡 HIGH
**Problem:** 4 realms exist in legacy but not current

**Realms:**
1. **Lumen (Chat)** - 373 lines
2. **Seraph (Voice)** - 487 lines
3. **Obelisk (Notes)** - 403 lines
4. **Aetherglass (Browser)** - 258 lines

**Total Code:** 1,521 lines

**Backend Dependency Analysis:**
```typescript
Lumen requires:
  - astraAPI.sendChatMessage() → Unknown backend

Seraph requires:
  - astraAPI.transcribeAudio() → Whisper service?
  - astraAPI.synthesizeSpeech() → TTS service?

Obelisk requires:
  - astraAPI.getNotes() → Notes service?
  - astraAPI.updateNote() → Notes service?

Aetherglass:
  - Pure UI (no backend) → Can migrate immediately
```

**Decision Tree:**
```
For each realm:
  1. Does backend service exist?
     YES → Migrate to canonical (add route, update to TanStack patterns)
     NO  → Evaluate options:
       a) Implement backend service (HIGH EFFORT)
       b) Use mock data (MEDIUM EFFORT)
       c) Deprecate realm (LOW EFFORT)
  
  2. Is feature core to ASTRA?
     YES → Prioritize implementation
     NO  → Can defer to future phase
```

**Recommendation:**
```
LUMEN (Chat):       HIGH PRIORITY - Core AI interaction
SERAPH (Voice):     MEDIUM - Advanced interaction mode
OBELISK (Notes):    MEDIUM - Productivity feature
AETHERGLASS (Browser): LOW - Can defer (pure UI, easy migration)
```

---

### 4. Orphaned Plugin UI 🟡 MEDIUM
**Problem:** `src/ui/components/` exists as separate UI system

**Files:**
- PluginUIController.tsx
- PluginNotifications.tsx
- PermissionRequestDialog.tsx

**Issue:**
- NOT integrated with Pantheon shell
- Different styling/patterns
- Separate toast system (vs ConsentCard)

**Decision:**
1. Are plugins still a core feature?
2. Should plugin UI use Pantheon shell?
3. Can PermissionRequestDialog be unified with ConsentCard?

**Options:**
```
A) INTEGRATE: 
   - Add plugin UI to Pantheon Pulse sidebar
   - Use ConsentCard for permissions
   - Unify notification system

B) KEEP SEPARATE:
   - Plugins run as overlays
   - Independent styling
   - Separate lifecycle

C) DEPRECATE:
   - Remove plugin system
   - Delete UI components
```

---

### 5. Evolution Components Isolation 🟢 LOW
**Problem:** `src/astra/evolution/components/` not accessible in UI

**Files:**
- CognitiveLayer.tsx
- EvolutionVisuals.jsx
- HeatmapVisualizer.jsx
- MetamorphosisChamber.jsx
- TelemetryDashboard.jsx
- VoiceConfirmation.jsx

**Options:**
```
A) CREATE REALM:
   - Add "Evolution" realm to Pantheon
   - Route: /evolution
   - Display telemetry dashboards

B) INTEGRATE INTO EXISTING:
   - Add to AEON (agent overview)
   - Add to DreamGrove (memory visuals)
   - Split across relevant realms

C) KEEP AS LIBRARY:
   - Used programmatically
   - Not user-facing
   - No Pantheon integration needed
```

---

### 6. Component API Inconsistency 🟡 MEDIUM
**Problem:** `src/components/ui/` (select, card, badge) may conflict with canonical

**Canonical:** `astra-os/apps/pantheon/src/components/ui/`
- Radix UI primitives
- `cn()` utility (clsx + tailwind-merge)
- Consistent prop patterns

**Root:** `src/components/ui/`
- Unknown implementation
- May use different API
- May have different styling

**Resolution:**
1. Read root components
2. Compare APIs
3. If compatible → Alias to canonical
4. If incompatible → Audit usage, migrate consumers

---

### 7. Theme File Duplication 🟡 MEDIUM
**Problem:** `theme.ts` appears in multiple locations

**Files:**
- `astra-os/apps/pantheon/src/tokens/theme.ts` - CANONICAL (300+ tokens)
- `astra-os/apps/pantheon/src/core/theme.ts` - Duplicate or different?

**Action:**
1. Read both files
2. If identical → Delete duplicate
3. If different → Reconcile differences

---

### 8. Tailwind Config Sprawl 🟡 MEDIUM
**Problem:** 3 Tailwind configurations

**Files:**
1. `astra-os/apps/pantheon/tailwind.config.js` - CANONICAL (integrated with tokens)
2. `astra-os/tailwind.config.js` - Root level
3. `pantheon_ui/tailwind.config.js` - Legacy

**Action:**
```
KEEP:   astra-os/apps/pantheon/tailwind.config.js (CANONICAL)
CHECK:  astra-os/tailwind.config.js (may be for other apps)
DELETE: pantheon_ui/tailwind.config.js (after migration)
```

---

## ✅ Strengths (What's Working Well)

### Canonical Codebase Excellence
1. **Zero Errors:** TypeScript compilation clean
2. **Modern Stack:** Latest React, TanStack, Zustand
3. **Performance:** 900ms build, code-splitting active
4. **Type Safety:** Full TypeScript, query type inference
5. **Design System:** 300+ tokens, spring physics
6. **Accessibility:** Radix UI, ARIA patterns, WCAG 2.1 AA
7. **DX:** Hot reload, selectors, keyboard shortcuts
8. **Testing Ready:** Vitest configured, Playwright setup

### Migration Success
- 3/3 realms migrated (DreamGrove, Weaver, SigilGate)
- ConsentCard implementation (150+ lines)
- TanStack Query patterns established
- Zero backend integration errors

---

## 🎯 Recommendations

### Priority 1: IMMEDIATE (This Sprint)

#### 1. Evaluate Legacy Realms (Lumen, Seraph, Obelisk, Aetherglass)
**Action:**
```bash
1. Check backend service status:
   curl http://localhost:7xxx/health (for each service)

2. For each realm:
   IF backend exists:
     - Add to canonical routes.tsx
     - Create realm component in astra-os/apps/pantheon/src/realms/
     - Update to TanStack Query patterns
     - Add to Spine navigation
   ELSE:
     - Document deprecation rationale
     - Add to UI_GAPS_TODO.md for future consideration
```

#### 2. Consolidate Entry Points
**Action:**
```bash
# Verify canonical is working
cd astra-os/apps/pantheon
pnpm dev  # Confirm zero errors

# Delete deprecated versions
rm -rf astra-os/src/App.tsx
rm -rf astra-os/src/main.tsx

# Add deprecation notice to legacy (temporary)
echo "// DEPRECATED: Use astra-os/apps/pantheon" > pantheon_ui/src/App.tsx
```

#### 3. Audit Root UI Components
**Action:**
```typescript
// Read and compare
src/components/ui/select.tsx  vs  astra-os/apps/pantheon/src/components/ui/*
src/components/ui/card.tsx    vs  (doesn't exist, add to canonical?)
src/components/ui/badge.tsx   vs  (doesn't exist, add to canonical?)

// Decision:
IF APIs compatible:
  → Alias imports to canonical
ELSE:
  → Migrate consumers to canonical API
  → Deprecate root versions
```

---

### Priority 2: MEDIUM (Next Sprint)

#### 4. Plugin UI Integration
**Decision Process:**
```
1. Interview stakeholders:
   - Are plugins core to ASTRA v1.0?
   - Who uses plugin UI?
   - Can we defer to v1.1?

2. IF keeping plugins:
   - Design integration with Pantheon
   - Unify notification systems
   - Consider Pulse sidebar for plugin status

3. IF deferring:
   - Document in ROADMAP.md
   - Keep code as-is (no integration)
```

#### 5. Evolution Components
**Options:**
1. Create `/evolution` realm (preferred)
2. Integrate into existing realms
3. Keep as library (status quo)

#### 6. Consolidate Build Configs
**Action:**
```bash
# Verify root vite.config.ts purpose
# Is it for other apps in astra-os/apps/*?

# Consolidate Tailwind configs
# Keep only necessary configs for each app

# Update import paths if needed
```

---

### Priority 3: LOW (Future)

#### 7. i18n/l10n Preparation
**Current Status:** Not implemented  
**Action:** 
- Add react-i18next
- Extract strings
- Prepare for internationalization

#### 8. RTL Support
**Current Status:** LTR only  
**Action:**
- Test with `dir="rtl"`
- Fix layout issues
- Update Tailwind for RTL variants

---

## 📋 Migration Checklist

### Phase A: Discovery ✅ COMPLETE
- [x] File search (96 files found)
- [x] Read canonical codebase
- [x] Read legacy codebase
- [x] Identify duplicates
- [x] Map realms
- [x] Analyze state management
- [x] Analyze routing
- [x] Analyze design tokens
- [x] Identify orphaned components

### Phase B: Evaluation (CURRENT)
- [ ] Check backend services for legacy realms
- [ ] Read root UI components (select, card, badge)
- [ ] Compare theme.ts files
- [ ] Audit plugin UI usage
- [ ] Decide on evolution components
- [ ] Create component dependency graph
- [ ] Generate content hashes for duplicates

### Phase C: Planning
- [ ] Create migration timeline
- [ ] Assign priorities
- [ ] Design realm migration pattern
- [ ] Plan build config consolidation
- [ ] Design deprecation strategy
- [ ] Create rollback plan

### Phase D: Execution
- [ ] Migrate or deprecate legacy realms
- [ ] Delete deprecated entry points
- [ ] Consolidate UI primitives
- [ ] Integrate or isolate plugin UI
- [ ] Address evolution components
- [ ] Consolidate build configs
- [ ] Update imports across codebase

### Phase E: Validation
- [ ] TypeScript compilation (0 errors)
- [ ] Dev server starts (pnpm dev)
- [ ] All routes render
- [ ] Backend integrations work
- [ ] Keyboard shortcuts functional
- [ ] Performance budget met (170KB)
- [ ] Playwright smoke tests pass

### Phase F: Documentation
- [ ] Update ARCHITECTURE.md
- [ ] Document deprecated paths
- [ ] Create migration guide
- [ ] Update developer docs
- [ ] Generate changelog

---

## 📐 Metrics

### Code Quality
```
TypeScript Errors:      0 ✅
Build Time:             900ms ✅
Bundle Size (first):    ~500KB ⚠️ (target: 170KB)
Lighthouse Score:       Not measured
WCAG Compliance:        2.1 AA (via Radix)
Test Coverage:          Not measured
```

### Performance Budget
```
Target:  TTI ≤ 1.2s, JS ≤ 170KB gzip, p95 latency ≤ 120ms
Current: Build 900ms, Bundle ~500KB (needs optimization)
```

### Migration Progress
```
Phases 1-3:   ✅ 93% complete (14/15 tasks)
Phase 4:      ⏳ Pending consolidation
UI Unification: 🔄 In progress
```

---

## 🎁 Deliverables

This report is **1 of 10** consolidation deliverables:

1. ✅ **UI_DEEP_SCAN_REPORT.md** (THIS FILE) - Comprehensive findings
2. ⏳ **UI_COMPONENT_MAP.json** - Normalized component inventory
3. ⏳ **UI_ROUTES_MAP.json** - Route → component mapping
4. ⏳ **UI_STATE_MAP.md** - State management inventory
5. ⏳ **UI_THEME_MERGE_PLAN.md** - Token unification strategy
6. ⏳ **UI_MIGRATION_PLAN.md** - Step-by-step consolidation
7. ⏳ **UI_DEPRECATIONS.md** - Files to remove
8. ⏳ **UI_GAPS_TODO.md** - Remaining work
9. ⏳ **UI_CHANGELOG_MERGE.md** - Human-readable summary
10. ⏳ **patches/** - Atomic migration patches

---

## 🔗 Next Steps

### Immediate Actions (Today)
1. Read this report (you are here)
2. Check backend services for legacy realms
3. Decide on legacy realm migration vs deprecation
4. Create UI_COMPONENT_MAP.json
5. Start UI_MIGRATION_PLAN.md

### Tomorrow
1. Execute migration plan Phase 1
2. Consolidate entry points
3. Update imports
4. Run validation suite

### This Week
1. Complete UI consolidation
2. All duplicates removed
3. Single canonical codebase
4. Ready for Phase 4 (Observability)

---

**Report Status:** Draft v1.0  
**Next Update:** After backend service evaluation  
**Questions?** See UI_GAPS_TODO.md for open issues

---

*Generated by ASTRA UI Deep Scan*  
*Saint Lucid Edition 333*
