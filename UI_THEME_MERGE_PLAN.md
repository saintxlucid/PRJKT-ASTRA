# UI Theme Merge Plan

Goal: Unify legacy theme/css variables into the canonical token system.

Canonical tokens:
- `astra-os/apps/pantheon/src/tokens/theme.ts` (CSS variables set via ThemeProvider)
- `astra-os/apps/pantheon/src/index.css` (base variables like --layout-*)

Legacy sources to diff:
- `pantheon_ui/src/index.css`

Proposed mapping strategy:
1) Layout variables
   - `--layout-halo-height`, `--layout-spine-width-*`, `--layout-pulse-width` → map 1:1 to `theme.layout.*` variables (already present in `tokens/theme.ts`).
2) Palette & surfaces
   - Legacy `bg-obsidian`, `text-text-muted`, `bg-astra-panel` → map to canonical palette in `tokens/theme.ts` (surface.bg, surface.panel, text.muted).
3) Status colors
   - `status-success/warn/danger` classes → map to canonical status tokens; re-export via utility classes in `index.css` if needed.
4) Components
   - Button, Dialog, Input under `apps/pantheon/src/components/ui/` are canonical. Remove duplicate styles in legacy paths or alias them.

Steps:
- Extract legacy CSS variable definitions from `pantheon_ui/src/index.css`
- Create a mapping table old→new tokens
- Update any references during realm migrations to use canonical tokens/components
- Delete legacy token definitions once no references remain

Notes:
- Keep visual parity first; then consider tightening tokens or removing rarely used vars.
