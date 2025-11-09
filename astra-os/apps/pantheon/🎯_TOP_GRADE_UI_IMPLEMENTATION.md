# 🎯 Top-Grade WebUI Implementation Plan

**Date**: 2025-11-08  
**Status**: Phase 1 - Architecture Audit Complete  
**Target**: Transform Pantheon into production-grade UI with airtight UX, performance, a11y, observability

---

## 📊 Architecture Audit Results

### ✅ Current Foundation (Strong)
- **React 18.2** - Modern concurrent features available
- **Vite 5.0** - Fast dev server, good defaults
- **TypeScript 5.3** - Type safety in place
- **Tailwind CSS 3.4** - Utility-first styling configured
- **5 Core Realms** - AEON, Aether Loom, Sigil Gate, Dream Grove, Weaver
- **4 Layout Components** - Halo, Spine, Oracle, Pulse
- **3 Backend Services** - All running (Memory 7007, Sigil 7701, Supervisor 7703)

### ⚠️ Critical Gaps (Blueprint Requirements)

| Category | Current State | Blueprint Requirement | Priority |
|----------|---------------|----------------------|----------|
| **Routing** | Manual state (`currentPath`) | TanStack Router (typed, lazy) | 🔴 Critical |
| **State** | Component state only | Zustand + TanStack Query | 🔴 Critical |
| **Performance** | No code-splitting, no budgets | 170KB gzip, realm chunks, TTI <1.2s | 🔴 Critical |
| **Design System** | Basic Tailwind, no tokens | Design tokens, Radix primitives | 🟡 High |
| **Forms** | No validation | React Hook Form + Zod | 🟡 High |
| **Data Layer** | Raw `fetch()` calls | TanStack Query (cache, retry, suspense) | 🔴 Critical |
| **i18n** | Hardcoded EN only | i18next, EN/AR RTL support | 🟢 Medium |
| **Testing** | No tests | Vitest, Testing Library, Playwright | 🟡 High |
| **Accessibility** | Basic (no audit) | WCAG 2.1 AA, keyboard nav, ARIA | 🟡 High |
| **Observability** | None | Web vitals, trace IDs, error boundaries | 🔴 Critical |
| **Security** | Basic fetch | ConsentCard, CSP, gated ops | 🟡 High |
| **Animation** | CSS transitions | Framer Motion, 60 FPS, spring physics | 🟢 Medium |

### 📦 Dependency Gaps

**Phase 1 - Core Infrastructure**
```json
{
  "@tanstack/react-router": "^1.79.0",
  "@tanstack/react-query": "^5.59.0",
  "zustand": "^5.0.0",
  "zod": "^3.23.0",
  "react-hook-form": "^7.53.0",
  "@hookform/resolvers": "^3.9.0",
  "framer-motion": "^11.11.0"
}
```

**Phase 2 - UI Primitives**
```json
{
  "@radix-ui/react-dialog": "^1.1.2",
  "@radix-ui/react-dropdown-menu": "^2.1.2",
  "@radix-ui/react-tabs": "^1.1.1",
  "@radix-ui/react-tooltip": "^1.1.3",
  "@radix-ui/react-switch": "^1.1.1",
  "@radix-ui/react-select": "^2.1.2",
  "clsx": "^2.1.1",
  "tailwind-merge": "^2.5.4"
}
```

**Phase 3 - Testing & i18n**
```json
{
  "vitest": "^2.1.4",
  "@vitest/ui": "^2.1.4",
  "@testing-library/react": "^16.0.1",
  "@testing-library/user-event": "^14.5.2",
  "playwright": "^1.48.2",
  "i18next": "^23.16.4",
  "react-i18next": "^15.1.0",
  "jsdom": "^25.0.1"
}
```

---

## 🎯 Implementation Roadmap

### **Week 1: Core Infrastructure** (Nov 8-15)

#### Day 1-2: Dependencies & Tokens
- [ ] Install Phase 1 dependencies (Router, Query, Zustand, Forms)
- [ ] Create `tokens/theme.ts` with Obsidian design tokens
- [ ] Update `tailwind.config.js` to consume tokens
- [ ] Create `store/ui.ts` (Zustand) for layout state
- [ ] Add global keyboard shortcuts (Alt+P, Alt+S, Cmd+K)

#### Day 3-4: Routing & Data Layer
- [ ] Create `routes.ts` with TanStack Router
- [ ] Configure lazy loading for all 5 realms
- [ ] Create `services/client.ts` (QueryClient + api helper)
- [ ] Add trace ID generation
- [ ] Wrap App with `QueryClientProvider`

#### Day 5: App Shell Refactor
- [ ] Update `App.tsx` with grid layout (56px/260px/1fr/360px)
- [ ] Migrate routing to `RouterProvider`
- [ ] Add `Suspense` boundaries per realm
- [ ] Test keyboard shortcuts (Alt+P/S, Cmd+K)

#### Day 6-7: Vite Performance Config
- [ ] Configure `manualChunks` for realm code-splitting
- [ ] Set up vendor chunk strategy
- [ ] Add rollupOptions for tree-shaking
- [ ] Create performance budget checks
- [ ] Test bundle size (<170KB gzip first route)

---

### **Week 2: UI System & Components** (Nov 16-22)

#### Day 8-9: Design Tokens Integration
- [ ] Implement theme.colors in all components
- [ ] Add motion tokens (spring physics)
- [ ] Test dark/light theme toggle
- [ ] Verify CSS variables in DevTools

#### Day 10-11: Radix Primitives
- [ ] Install Phase 2 dependencies (Radix UI)
- [ ] Create `components/ui/Button.tsx`
- [ ] Create `components/ui/Input.tsx`
- [ ] Create `components/ui/Dialog.tsx`
- [ ] Create `components/ui/Tooltip.tsx`
- [ ] Create `components/ui/Select.tsx`
- [ ] Ensure keyboard nav + ARIA for all

#### Day 12-13: Consent System
- [ ] Create `components/ConsentCard.tsx`
- [ ] Add diff preview (create/write/delete/move)
- [ ] Add scope badge display
- [ ] Integrate Framer Motion animations
- [ ] Connect to Sigil Gate API

#### Day 14: Component Testing
- [ ] Install Phase 3 dependencies (Vitest, Testing Library)
- [ ] Configure `vitest.config.ts`
- [ ] Write tests for Button, Input, Dialog
- [ ] Test keyboard interactions
- [ ] Test ARIA attributes

---

### **Week 3: Data Migration & Observability** (Nov 23-29)

#### Day 15-16: Realm Migration to TanStack Query
- [ ] Migrate `DreamGrove.tsx` to `useQuery`/`useMutation`
- [ ] Migrate `Weaver.tsx` to TanStack Query
- [ ] Migrate `SigilGate.tsx` to TanStack Query
- [ ] Add optimistic updates where safe
- [ ] Add error boundaries per realm

#### Day 17-18: Observability Foundation
- [ ] Add web vitals tracking (LCP, TTI, CLS)
- [ ] Display trace ID in Halo
- [ ] Create error boundary component with retry
- [ ] Add Pulse metric tiles (vitals + API latency)
- [ ] Test error states in all realms

#### Day 19-20: i18n Setup
- [ ] Configure i18next with EN/AR
- [ ] Add language toggle to Halo
- [ ] Implement RTL layout (logical props)
- [ ] Mirror icons for RTL mode
- [ ] Test font scaling 90-130%

#### Day 21: E2E Testing
- [ ] Configure Playwright
- [ ] Write smoke tests (home, consent, realms)
- [ ] Test keyboard navigation flow
- [ ] Test dark/light theme switch
- [ ] Test RTL mode

---

### **Week 4: Polish & Launch** (Nov 30 - Dec 6)

#### Day 22-23: Performance Optimization
- [ ] Audit bundle size per route
- [ ] Add virtualization to lists/charts
- [ ] Optimize animation frames (60 FPS)
- [ ] Implement on-hover prefetch for nav
- [ ] Run Lighthouse audits (target: 95+ score)

#### Day 24-25: Security Hardening
- [ ] Add CSP meta tags (strict mode)
- [ ] Sandbox iframes (Aetherglass viewers)
- [ ] Gate clipboard/file operations
- [ ] Add visual scope pill to Halo
- [ ] Audit all destructive ops use ConsentCard

#### Day 26-27: Accessibility Audit
- [ ] Run axe DevTools on all realms
- [ ] Document keyboard map
- [ ] Add skip links
- [ ] Test screen reader (NVDA/VoiceOver)
- [ ] Verify color contrast ≥4.5:1

#### Day 28: Documentation & Storybook
- [ ] Set up Storybook
- [ ] Document all UI primitives
- [ ] Create component playground
- [ ] Write architecture guide
- [ ] Create performance guide

---

## 📏 Quality Gates (Must Pass Before Ship)

### Performance
- [ ] First route < 170KB gzip JS
- [ ] TTI ≤ 1.2s on 3G
- [ ] p95 route change < 200ms
- [ ] No hydration warnings
- [ ] All Suspense fallbacks styled
- [ ] Lighthouse score ≥ 95

### Accessibility
- [ ] Keyboard coverage 100%
- [ ] Focus visible on all interactive elements
- [ ] Focus traps correct in modals
- [ ] ARIA labels present and correct
- [ ] RTL mirror verified (AR)
- [ ] Screen reader tested

### Reliability
- [ ] ErrorBoundary per realm + retry
- [ ] Query cache scoped by realm key
- [ ] Network offline banner
- [ ] Queued actions for safe ops
- [ ] No unhandled promise rejections

### Security
- [ ] ConsentCard used for destructive ops
- [ ] CSP strict, no inline scripts
- [ ] File/clipboard gated by gestures
- [ ] Scope pill shows active privileges
- [ ] No sensitive data in URLs

### Observability
- [ ] Web vitals in Pulse
- [ ] Trace ID in Halo + all fetches
- [ ] User-visible diagnostics
- [ ] Error cause + action CTA
- [ ] Performance marks logged

---

## 🎨 Design Token Preview

```typescript
// tokens/theme.ts
export const theme = {
  colors: {
    bg: "#0A0A0B",
    panel: "#101113",
    elevated: "#121416",
    text: "#EDEFF3",
    muted: "#7D8491",
    secondary: "#B8BDC7",
    accent: {
      gold: "#C9B37E",
      teal: "#77DDE8",
      violet: "#A787FF"
    },
    status: {
      success: "#36C790",
      warn: "#EFB65B",
      danger: "#E94B35",
      info: "#5AAAEF"
    }
  },
  motion: {
    in: 0.12,
    out: 0.10,
    spring: { mass: 0.9, stiffness: 220, damping: 28 }
  },
  radius: { xl: "1rem", "2xl": "1.25rem" },
  shadow: { soft: "0 6px 24px rgba(0,0,0,.25)" }
};
```

---

## 🚀 Quick Start Commands

```powershell
# Install all dependencies
cd apps\pantheon
npm install @tanstack/react-router @tanstack/react-query zustand framer-motion zod react-hook-form @hookform/resolvers
npm install -D vitest @vitest/ui @testing-library/react playwright

# Run dev server (after migration)
npm run dev

# Run tests
npm run test

# Run E2E tests
npx playwright test

# Build with bundle analysis
npm run build -- --mode production

# Preview production build
npm run preview
```

---

## 📊 Progress Tracker

**Overall Progress**: 0% (14/14 tasks remaining)

### Phase 1: Core Infrastructure (0/7)
- [ ] Dependencies installed
- [ ] Design tokens created
- [ ] UI store configured
- [ ] TanStack Router setup
- [ ] TanStack Query setup
- [ ] App shell refactored
- [ ] Vite performance config

### Phase 2: UI System (0/4)
- [ ] Radix primitives created
- [ ] ConsentCard implemented
- [ ] Component tests written
- [ ] Storybook configured

### Phase 3: Data & Observability (0/3)
- [ ] Realms migrated to Query
- [ ] Observability foundation
- [ ] i18n & RTL support

### Phase 4: Polish (0/0)
- All quality gates will be added here

---

## 📝 Notes

**Current System Status**: 95% operational (3 services running)  
**UI Current State**: Functional but needs architectural upgrade  
**Priority**: Follow blueprint strictly for production-grade quality  

**Key Decisions**:
1. ✅ Keep React 18 + Vite (strong foundation)
2. ✅ Add TanStack suite (Router + Query) for type-safe data flow
3. ✅ Use Zustand over Context API (better performance)
4. ✅ Adopt Radix UI for accessibility guarantees
5. ✅ Implement ConsentCard for all destructive operations
6. ✅ Enforce 170KB first-route budget

**Risk Mitigation**:
- Migrate incrementally (realm by realm)
- Keep existing components functional during transition
- Test each phase before moving to next
- Document breaking changes for rollback

---

**Next Action**: Start Phase 1 - Install core dependencies and create design tokens
