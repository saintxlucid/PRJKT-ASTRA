# UI Primitives Audit (Select, Card, Badge)

Scope: unify primitives with tokens-driven theme and Radix usage patterns.

Findings

- Select (`src/components/ui/select.tsx`): Radix-based; uses tailwind semantic tokens like `border-input`, `bg-popover`. Action: map these to ASTRA tokens via Tailwind theme or tweak classes to `bg-astra-panel`, `text-white/80`, `border-white/10` as needed. No code change required now; leave as compatible.
- Card (`src/components/ui/card.tsx`): Uses `bg-card text-card-foreground`. Canonical Tailwind now exposes `astra.card`; add alias in theme for `bg-card` -> `bg-astra-panel` via Tailwind config or keep utility mapping. No change needed now.
- Badge (`src/components/ui/badge.tsx`): Uses CSS variables `bg-primary`, `bg-secondary`, etc. Ensure tokens or Tailwind preset provides these semantics. Short-term keep; long-term provide token aliases or variants mapping.

Recommendations

- Keep components; rely on Pantheon Tailwind config to supply semantic colors/aliases.
- Add alias layer in Tailwind config if any class is missing.
- Add unit visual checks in storybook or a gallery page (future step).

Next Steps

- If any missing semantic color class is reported by linter/build, add alias mapping to `apps/pantheon/tailwind.config.js`.
- Optionally create a `ui/primitives.ts` barrel re-export when consolidating imports.
