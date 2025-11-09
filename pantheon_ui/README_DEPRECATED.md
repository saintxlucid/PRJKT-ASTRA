# pantheon_ui — DEPRECATED

**Status:** This directory is deprecated. Use `astra-os/apps/pantheon` for all new development.

## Migration Complete

All canonical UI components, realms, and tokens have been migrated to:

```text
astra-os/apps/pantheon/
```

This legacy UI is retained only to:

- Avoid breaking old CI/build scripts that may reference it.
- Provide a historical reference for the unique realms (Lumen, Seraph, Obelisk, Aetherglass) that were prototyped here.

## What to do

- **New features:** Add them to `astra-os/apps/pantheon`.
- **Bug fixes:** Apply them to `astra-os/apps/pantheon`.
- **Build/run:** Use `astra-os/apps/pantheon/package.json` scripts.

## Safe to delete?

Yes, once you confirm:

1. No CI jobs reference `pantheon_ui/package.json` scripts.
2. The realms you need (DreamGrove, Weaver, SigilGate) are present in `astra-os/apps/pantheon/src/realms/`.

If you need Lumen/Seraph/Obelisk/Aetherglass, migrate them to the canonical structure first.

---

**See also:**

- `DEPRECATED.md` (already in this directory)
- `UI_DEPRECATIONS.md` (project root)
- `UI_MIGRATION_PLAN.md` (project root)
