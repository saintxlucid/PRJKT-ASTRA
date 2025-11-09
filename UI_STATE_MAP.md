# UI State Map (Pantheon)

High-level map of app shells, stores, and cross-cutting services.

- Shell
  - `apps/pantheon/src/App.tsx` — Canonical layout. Injects `NeuralAmbient`.
  - Router: TanStack; main routes under `src/realms/*`.
- Stores
  - `store/sim.ts` — Neural sim lifecycle/metrics.
  - `store/ui.ts` — Spine/pulse sizing and collapse toggles.
- Services
  - `services/client.ts` — Data layer: memory, sigil, supervisor APIs.
  - `services/audio/micDrive.ts` — Mic RMS → neural drive.
- Components
  - `components/Pulse.tsx` — Metrics panel + mic toggle.
  - `components/NeuralAmbient.tsx` — Ambient overlay.

Notes

- Legacy `pantheon_ui` is deprecated and re-exporting canonical App.
- Tailwind config is tokens-driven in `apps/pantheon/tailwind.config.js`.
