/**
 * DEPRECATED: Legacy pantheon_ui Tailwind config.
 * Use `astra-os/apps/pantheon/tailwind.config.js` for new development.
 * This file retained only to avoid breaking old build scripts.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          DEFAULT: '#0A0A0B',
          panel: '#101113',
          elevated: '#121416',
        },
        limestone: {
          DEFAULT: '#C9B37E',
          light: '#E8D9B8',
          dark: '#9B8761',
        },
        lucid: {
          teal: '#77DDE8',
          violet: '#A787FF',
          mint: '#5EF6D0',
        },
        status: {
          success: '#36C790',
          warning: '#EFB65B',
          danger: '#E94B35',
          info: '#5AAAEF',
        },
        text: {
          primary: '#EDEFF3',
          secondary: '#B8BDC7',
          muted: '#7D8491',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Söhne Mono', 'monospace'],
        serif: ['Freight Text', 'Georgia', 'serif'],
      },
      animation: {
        'spring-in': 'spring-in 120ms cubic-bezier(0.34, 1.56, 0.64, 1)',
        'spring-out': 'spring-out 100ms cubic-bezier(0.32, 0, 0.67, 0)',
        'breathe': 'breathe 3s ease-in-out infinite',
        'pulse-333': 'pulse-333 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'spring-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'spring-out': {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.95)' },
        },
        'breathe': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.01)' },
        },
        'pulse-333': {
          '0%, 100%': { opacity: '1' },
          '33%': { opacity: '0.7' },
          '66%': { opacity: '0.85' },
        },
      },
    },
  },
  plugins: [],
}
