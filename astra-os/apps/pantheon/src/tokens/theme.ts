/**
 * ASTRA OS Design Tokens
 * Top-grade design system foundation
 * - Obsidian dark theme (default)
 * - Precision motion system (spring physics)
 * - Semantic color scales
 * - Elevation & shadow system
 */

export const theme = {
  colors: {
    // Background layers
    bg: "#0A0A0B",        // Base canvas
    panel: "#101113",     // Raised surfaces
    elevated: "#121416",  // Elevated panels (modals, tooltips)
    overlay: "rgba(0, 0, 0, 0.7)", // Modal backdrop

    // Text hierarchy
    text: "#EDEFF3",      // Primary text
    muted: "#7D8491",     // Secondary text
    secondary: "#B8BDC7", // Tertiary text
    disabled: "#4A4D56",  // Disabled state

    // Accent palette
    accent: {
      gold: "#C9B37E",    // Primary brand (consent, seals)
      teal: "#77DDE8",    // Secondary (insights, metrics)
      violet: "#A787FF",  // Tertiary (magic, AI)
      amber: "#F5C563",   // Highlight (citations, focus)
    },

    // Status colors
    status: {
      success: "#36C790",
      warn: "#EFB65B",
      danger: "#E94B35",
      info: "#5AAAEF",
    },

    // Interactive states
    hover: "rgba(255, 255, 255, 0.08)",
    active: "rgba(255, 255, 255, 0.12)",
    focus: "#5AAAEF", // Focus ring color

    // Borders
    border: {
      default: "rgba(255, 255, 255, 0.1)",
      hover: "rgba(255, 255, 255, 0.2)",
      focus: "rgba(90, 170, 239, 0.5)",
    },
  },

  // Motion system - spring physics for natural animations
  motion: {
    // Duration (seconds)
    instant: 0.08,
    fast: 0.12,
    base: 0.20,
    slow: 0.30,
    slower: 0.45,

    // Easing curves
    easing: {
      in: "cubic-bezier(0.4, 0, 1, 1)",
      out: "cubic-bezier(0, 0, 0.2, 1)",
      inOut: "cubic-bezier(0.4, 0, 0.2, 1)",
    },

    // Spring physics (for Framer Motion)
    spring: {
      mass: 0.9,
      stiffness: 220,
      damping: 28,
    },

    // Presets for common animations
    presets: {
      fadeIn: {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: { duration: 0.12 },
      },
      slideUp: {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        transition: { type: "spring", mass: 0.9, stiffness: 220, damping: 28 },
      },
      slideDown: {
        initial: { opacity: 0, y: -8 },
        animate: { opacity: 1, y: 0 },
        transition: { type: "spring", mass: 0.9, stiffness: 220, damping: 28 },
      },
      scale: {
        initial: { opacity: 0, scale: 0.96 },
        animate: { opacity: 1, scale: 1 },
        transition: { type: "spring", mass: 0.9, stiffness: 220, damping: 28 },
      },
    },
  },

  // Border radius scale
  radius: {
    sm: "0.25rem",   // 4px
    base: "0.5rem",  // 8px
    md: "0.75rem",   // 12px
    lg: "1rem",      // 16px
    xl: "1.25rem",   // 20px
    "2xl": "1.5rem", // 24px
    full: "9999px",  // Fully rounded
  },

  // Shadow system (elevation)
  shadow: {
    none: "none",
    sm: "0 1px 2px rgba(0, 0, 0, 0.05)",
    base: "0 2px 8px rgba(0, 0, 0, 0.12)",
    md: "0 4px 12px rgba(0, 0, 0, 0.15)",
    lg: "0 8px 24px rgba(0, 0, 0, 0.2)",
    xl: "0 16px 48px rgba(0, 0, 0, 0.25)",
    soft: "0 6px 24px rgba(0, 0, 0, 0.25)", // Soft glow
    inner: "inset 0 2px 4px rgba(0, 0, 0, 0.1)",
  },

  // Spacing scale (matches Tailwind defaults)
  spacing: {
    0: "0",
    1: "0.25rem",  // 4px
    2: "0.5rem",   // 8px
    3: "0.75rem",  // 12px
    4: "1rem",     // 16px
    5: "1.25rem",  // 20px
    6: "1.5rem",   // 24px
    8: "2rem",     // 32px
    10: "2.5rem",  // 40px
    12: "3rem",    // 48px
    16: "4rem",    // 64px
    20: "5rem",    // 80px
    24: "6rem",    // 96px
  },

  // Typography scale
  typography: {
    fontFamily: {
      sans: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
      mono: '"JetBrains Mono", "Fira Code", Consolas, monospace',
    },
    fontSize: {
      xs: "0.75rem",    // 12px
      sm: "0.875rem",   // 14px
      base: "1rem",     // 16px
      lg: "1.125rem",   // 18px
      xl: "1.25rem",    // 20px
      "2xl": "1.5rem",  // 24px
      "3xl": "1.875rem",// 30px
      "4xl": "2.25rem", // 36px
    },
    fontWeight: {
      normal: "400",
      medium: "500",
      semibold: "600",
      bold: "700",
    },
    lineHeight: {
      tight: "1.25",
      normal: "1.5",
      relaxed: "1.75",
    },
  },

  // Z-index scale
  zIndex: {
    base: 0,
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modal: 1040,
    popover: 1050,
    tooltip: 1060,
  },

  // Layout dimensions
  layout: {
    halo: {
      height: "56px",
    },
    spine: {
      widthExpanded: "260px",
      widthCollapsed: "72px",
      transition: "width 0.20s cubic-bezier(0.4, 0, 0.2, 1)",
    },
    pulse: {
      width: "360px",
      transition: "width 0.20s cubic-bezier(0.4, 0, 0.2, 1)",
    },
  },

  // Breakpoints (for responsive design)
  breakpoints: {
    sm: "640px",
    md: "768px",
    lg: "1024px",
    xl: "1280px",
    "2xl": "1536px",
  },
} as const;

// Type exports for TypeScript
export type Theme = typeof theme;
export type ThemeColors = typeof theme.colors;
export type ThemeMotion = typeof theme.motion;
export type ThemeRadius = typeof theme.radius;
export type ThemeShadow = typeof theme.shadow;

// CSS variable generator (for Tailwind integration)
export function generateCSSVariables() {
  return `
:root {
  /* Colors */
  --color-bg: ${theme.colors.bg};
  --color-panel: ${theme.colors.panel};
  --color-elevated: ${theme.colors.elevated};
  --color-overlay: ${theme.colors.overlay};
  
  --color-text: ${theme.colors.text};
  --color-muted: ${theme.colors.muted};
  --color-secondary: ${theme.colors.secondary};
  --color-disabled: ${theme.colors.disabled};
  
  --color-accent-gold: ${theme.colors.accent.gold};
  --color-accent-teal: ${theme.colors.accent.teal};
  --color-accent-violet: ${theme.colors.accent.violet};
  --color-accent-amber: ${theme.colors.accent.amber};
  
  --color-success: ${theme.colors.status.success};
  --color-warn: ${theme.colors.status.warn};
  --color-danger: ${theme.colors.status.danger};
  --color-info: ${theme.colors.status.info};
  
  --color-hover: ${theme.colors.hover};
  --color-active: ${theme.colors.active};
  --color-focus: ${theme.colors.focus};
  
  --color-border: ${theme.colors.border.default};
  --color-border-hover: ${theme.colors.border.hover};
  --color-border-focus: ${theme.colors.border.focus};
  
  /* Motion */
  --motion-instant: ${theme.motion.instant}s;
  --motion-fast: ${theme.motion.fast}s;
  --motion-base: ${theme.motion.base}s;
  --motion-slow: ${theme.motion.slow}s;
  --motion-slower: ${theme.motion.slower}s;
  
  --motion-ease-in: ${theme.motion.easing.in};
  --motion-ease-out: ${theme.motion.easing.out};
  --motion-ease-in-out: ${theme.motion.easing.inOut};
  
  /* Radius */
  --radius-sm: ${theme.radius.sm};
  --radius-base: ${theme.radius.base};
  --radius-md: ${theme.radius.md};
  --radius-lg: ${theme.radius.lg};
  --radius-xl: ${theme.radius.xl};
  --radius-2xl: ${theme.radius["2xl"]};
  
  /* Shadow */
  --shadow-sm: ${theme.shadow.sm};
  --shadow-base: ${theme.shadow.base};
  --shadow-md: ${theme.shadow.md};
  --shadow-lg: ${theme.shadow.lg};
  --shadow-xl: ${theme.shadow.xl};
  --shadow-soft: ${theme.shadow.soft};
  
  /* Layout */
  --layout-halo-height: ${theme.layout.halo.height};
  --layout-spine-width-expanded: ${theme.layout.spine.widthExpanded};
  --layout-spine-width-collapsed: ${theme.layout.spine.widthCollapsed};
  --layout-pulse-width: ${theme.layout.pulse.width};
}
`.trim();
}

// Light theme overrides (optional - for future use)
export const lightTheme = {
  colors: {
    bg: "#FAFBFC",
    panel: "#FFFFFF",
    elevated: "#F5F7FA",
    overlay: "rgba(0, 0, 0, 0.5)",
    text: "#1A1D23",
    muted: "#6B7280",
    secondary: "#4B5563",
    disabled: "#D1D5DB",
    // Keep accent colors same
    accent: theme.colors.accent,
    status: theme.colors.status,
    hover: "rgba(0, 0, 0, 0.04)",
    active: "rgba(0, 0, 0, 0.08)",
    focus: theme.colors.focus,
    border: {
      default: "rgba(0, 0, 0, 0.1)",
      hover: "rgba(0, 0, 0, 0.2)",
      focus: "rgba(90, 170, 239, 0.5)",
    },
  },
} as const;

export default theme;
