import { theme } from './src/tokens/theme';

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ASTRA OS Design System Colors
        'astra': {
          'bg': theme.colors.bg,
          // Card maps to panel for canonical usage
          'card': theme.colors.panel,
          'panel': theme.colors.panel,
          'elevated': theme.colors.elevated,
          'overlay': theme.colors.overlay,
          // Legacy mappings retained for compatibility
          'border': theme.colors.border.default,
          'hover': theme.colors.hover,
        },
        'text': {
          DEFAULT: theme.colors.text,
          'muted': theme.colors.muted,
          'secondary': theme.colors.secondary,
          'disabled': theme.colors.disabled,
        },
        'accent': {
          'gold': theme.colors.accent.gold,
          'teal': theme.colors.accent.teal,
          'violet': theme.colors.accent.violet,
          'amber': theme.colors.accent.amber,
        },
        'status': {
          'success': theme.colors.status.success,
          'warn': theme.colors.status.warn,
          'danger': theme.colors.status.danger,
          'info': theme.colors.status.info,
        },
        // Legacy aliases (for backwards compatibility)
        'astra-dark': theme.colors.bg,
        'astra-accent': theme.colors.accent.violet,
        'astra-emerald': theme.colors.status.success,
        'astra-rose': theme.colors.status.danger,
      },
      borderRadius: {
        'sm': theme.radius.sm,
        'base': theme.radius.base,
        'md': theme.radius.md,
        'lg': theme.radius.lg,
        'xl': theme.radius.xl,
        '2xl': theme.radius['2xl'],
        'full': theme.radius.full,
      },
      boxShadow: {
        'sm': theme.shadow.sm,
        'base': theme.shadow.base,
        'md': theme.shadow.md,
        'lg': theme.shadow.lg,
        'xl': theme.shadow.xl,
        'soft': theme.shadow.soft,
        'inner': theme.shadow.inner,
      },
      fontFamily: {
        'sans': theme.typography.fontFamily.sans.split(', '),
        'mono': theme.typography.fontFamily.mono.split(', '),
      },
      transitionDuration: {
        'instant': `${theme.motion.instant * 1000}ms`,
        'fast': `${theme.motion.fast * 1000}ms`,
        'base': `${theme.motion.base * 1000}ms`,
        'slow': `${theme.motion.slow * 1000}ms`,
        'slower': `${theme.motion.slower * 1000}ms`,
      },
      transitionTimingFunction: {
        'in': theme.motion.easing.in,
        'out': theme.motion.easing.out,
        'in-out': theme.motion.easing.inOut,
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
