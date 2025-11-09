/**
 * Deprecated theme module.
 * Use canonical design tokens in `../tokens/theme.ts`.
 * This file now re-exports the canonical theme for backwards compatibility.
 */
export { theme } from '../tokens/theme';
export type { Theme } from '../tokens/theme';

// Backwards compatibility helpers (old field names -> tokens)
export const legacyThemeAdapter = {
  colors: {
    dark: '#0A0A0B',
    darkPanel: '#101113',
    accent: '#A787FF',
    accentHover: '#A787FF',
    emerald: '#36C790',
    rose: '#E94B35',
    textPrimary: '#EDEFF3',
    textSecondary: '#B8BDC7',
    textTertiary: '#7D8491',
    border: 'rgba(255,255,255,0.1)',
  },
  transitions: {
    fast: '120ms cubic-bezier(0.4, 0, 0.2, 1)',
    normal: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
  },
  spacing: {
    haloHeight: '56px',
    spineWidth: '260px',
    pulseWidth: '360px',
  },
};

export default legacyThemeAdapter;
