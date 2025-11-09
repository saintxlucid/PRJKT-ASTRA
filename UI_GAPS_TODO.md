# UI Gaps & TODO

Outstanding items after Phase 3 consolidation.

## Gaps

- No unified Storybook or visual regression harness.
- Missing accessibility audit (ARIA roles across Pulse, Dialogs).
- Theme light-mode variables prepared but not wired.
- No performance budget monitoring (FPS / Worker latency).
- Sparse error boundary coverage for realms.

## TODO

- Add `<ErrorBoundary>` wrapper around realm routes.
- Introduce a simple gallery page for primitives.
- Implement light/dark theme toggle reading from tokens.
- Add a11y lint (axe-core) integration in dev.
- Capture neural sim tick latency histogram (web worker).
