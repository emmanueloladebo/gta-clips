/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        vice: {
          pink: "#ff2a85",
          orange: "#ff7b00",
          cyan: "#00f0ff",
          purple: "#7928ca",
          dark: "#0b0e14",
          card: "#121722",
          border: "#1e2638",
          hover: "#182030"
        }
      }
    },
  },
  plugins: [],
}
