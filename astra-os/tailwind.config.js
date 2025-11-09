/**
 * DEPRECATED: Root Tailwind config
 * Pantheon app uses tokens-driven config at `apps/pantheon/tailwind.config.js`.
 * Keep this only if other packages still reference it.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        astra: {
          bg: "#0b0b12",
          card: "rgba(255, 255, 255, 0.05)",
          border: "rgba(255, 255, 255, 0.1)",
          hover: "rgba(255, 255, 255, 0.15)",
        }
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
