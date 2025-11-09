# UI Deprecations

Date: 2025-11-08

Canonical web UI:
- `astra-os/apps/pantheon/`

Deprecated/Legacy entrypoints:
- `pantheon_ui/` (legacy Pantheon UI, separate Vite app)
- `astra-os/src/App.tsx` (standalone dashboard; not part of canonical web shell)

Policy:
- No new features should land in deprecated paths.
- Keep for reference during the migration window, then remove.

Planned timeline:
- Week 1: Quarantine and document (this change)
- Week 2: Port any still-relevant visuals/widgets
- Week 3: Remove `pantheon_ui/` and any unused primitives once parity is confirmed

Acceptance to remove:
- Canonical app renders Halo/Spine/Pulse/Oracle
- Realms: AEON, DreamGrove, AetherLoom, SigilGate, Weaver present
- No external scripts reference `pantheon_ui` or `astra-os/src/App.tsx`
