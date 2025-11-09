# ⚡ ASTRA OS - Quick Reference (Phase 1)

## 🎯 Current Status
**System Readiness**: 60% (was 50%)  
**Phase 1**: ✅ COMPLETE (7/14 tasks)  
**Next Phase**: UI Primitives & Components

---

## 🚀 Quick Start

### Run Development Server
```powershell
cd apps\pantheon
npm run dev
# Opens: http://localhost:3000
```

### Test All Routes
- http://localhost:3000/aeon (default)
- http://localhost:3000/loom
- http://localhost:3000/sigil
- http://localhost:3000/grove
- http://localhost:3000/weaver
- http://localhost:3000/settings
- http://localhost:3000/logs

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Cmd+K` | Toggle Oracle (command palette) |
| `Alt+P` | Toggle Pulse sidebar |
| `Alt+S` | Toggle Spine sidebar |
| `Alt+T` | Toggle theme |
| `Esc` | Close Oracle |

---

## 📂 New File Locations

```
src/
├── tokens/theme.ts          ← Design system
├── store/ui.ts              ← Global state
├── services/client.ts       ← API + Query client
├── routes.tsx               ← Router config
├── views/
│   ├── Settings.tsx
│   └── Logs.tsx
```

---

## 🎨 Theme Tokens (Quick Access)

### Colors
```typescript
import { theme } from './tokens/theme';

theme.colors.bg              // #0A0A0B
theme.colors.accent.gold     // #C9B37E
theme.colors.status.success  // #36C790
```

### Tailwind Classes
```tsx
<div className="bg-astra-panel text-accent-teal rounded-2xl shadow-soft">
```

---

## 🔌 API Helpers

### Memory Service
```typescript
import { memoryAPI } from './services/client';

await memoryAPI.search('quantum', 5);
await memoryAPI.add('New memory fragment');
```

### Sigil Gate
```typescript
import { sigilAPI } from './services/client';

await sigilAPI.seal('operator', plan, 600);
await sigilAPI.verify(plan);
```

### Supervisor
```typescript
import { supervisorAPI } from './services/client';

await supervisorAPI.createJob('task', { data: 'value' });
await supervisorAPI.listJobs();
```

---

## 🏗️ UI Store (Zustand)

```typescript
import { useUI } from './store/ui';

function Component() {
  const { showPulse, togglePulse, theme, setTheme } = useUI();
  
  return (
    <button onClick={togglePulse}>
      Toggle Pulse (currently: {showPulse ? 'shown' : 'hidden'})
    </button>
  );
}
```

---

## 🧭 Navigation

### Using Router
```typescript
import { Link } from '@tanstack/react-router';

<Link to="/aeon">Go to AEON</Link>
```

### Programmatic
```typescript
import { useUI } from './store/ui';

const { setCurrentPath } = useUI();
setCurrentPath('/grove');
```

---

## 📊 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| First load | <170KB | ⏳ Pending Vite config |
| TTI | <1.2s | ⏳ Pending measurement |
| Route change | <200ms | ✅ Lazy loading |
| FPS | 60 | ✅ CSS transitions |

---

## 🔄 Next Actions

### Immediate (Next Session)
1. Install Radix UI primitives
2. Update Vite config (code-splitting)
3. Build Button + Input components
4. Migrate DreamGrove to TanStack Query

### This Week
5. Create ConsentCard
6. Add error boundaries
7. Install testing tools
8. Web vitals tracking

---

## 📋 Checklists

### Phase 1 Verification
- [x] Routes load without errors
- [x] State persists (localStorage)
- [x] Keyboard shortcuts work
- [x] Design tokens integrated
- [x] API helpers functional
- [x] Lazy loading configured

### Phase 2 Readiness
- [ ] Radix UI installed
- [ ] Vite performance config
- [ ] Primitive components created
- [ ] First realm migrated to Query
- [ ] Error boundaries added
- [ ] Testing infrastructure

---

## 🛠️ Useful Commands

```powershell
# Install new dependencies
npm install <package>

# Check bundle size
npm run build
# Check dist/ folder sizes

# Run tests (when configured)
npm run test

# Type check
npx tsc --noEmit

# Lint
npm run lint
```

---

## 📞 Key Concepts

### Trace IDs
- Auto-generated per API call
- Visible in Halo (when active)
- Injected as `x-trace-id` header
- Cleared after 1s

### Lazy Loading
- Realms load on route access
- `Suspense` shows loading spinner
- Preload on hover (100ms delay)

### State Persistence
- localStorage key: `astra-ui-store`
- Persisted: layout, theme, preferences
- Not persisted: oracleOpen, transient state

---

## 🚨 Troubleshooting

### App won't start
```powershell
# Reinstall dependencies
cd apps\pantheon
rm -rf node_modules
npm install
```

### State not persisting
- Check browser localStorage
- Key: `astra-ui-store`
- Clear if corrupted

### Routes not working
- Verify `routes.tsx` has no syntax errors
- Check `RouterProvider` in `index.tsx`
- Look for console errors

---

**Last Updated**: 2025-11-08  
**Version**: Phase 1 Complete  
**Documentation**: See `📊_PHASE_1_SUMMARY.md`
