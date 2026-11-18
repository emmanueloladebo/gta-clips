/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        vice: {
          pink: "#ff2a85",
          orange: "#ff7b00",
          cyan: "#00f0ff",
          purple: "#7928ca",
          dark: "#080a0f",
          card: "#0f121b",
          border: "rgba(255, 255, 255, 0.08)",
          hover: "rgba(255, 255, 255, 0.04)"
        }
      }
    },
  },
  plugins: [],
}
