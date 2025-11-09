# UI Changelog (Consolidation)

## Added

- Neural sim worker + store + ambient overlay; Pulse integration with mic drive.
- Tokens-driven Tailwind config; added backdropBlur.xs; legacy alias mappings.
- Sigil Gate realm: journal fetch, rollback reason, plan digest.

## Changed

- Replaced inline grid styles with CSS utility classes.
- Deprecated `apps/pantheon/src/core/theme.ts` in favor of `src/tokens/theme.ts`.
- Marked root and pantheon_ui tailwind configs as deprecated.

## Docs

- Added: UI_STATE_MAP.md, UI_GAPS_TODO.md, UI_PRIMITIVES_AUDIT.md.

## Pending

- Primitive components harmonization if any semantic classes missing.
- Cython perf harness expansion beyond cosine (xxh3, stream scan).
