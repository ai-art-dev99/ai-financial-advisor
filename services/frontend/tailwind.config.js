/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'DM Serif Display'", "serif"],
        body: ["'DM Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        obsidian: {
          950: "#070709",
          900: "#0d0d12",
          800: "#14141c",
          700: "#1c1c28",
          600: "#252535",
          500: "#3a3a50",
          400: "#5a5a78",
          300: "#8a8aaa",
          200: "#b0b0cc",
          100: "#d8d8ec",
        },
        gold: {
          500: "#c9a84c",
          400: "#dfc06e",
          300: "#f0d89a",
        },
      },
    },
  },
  plugins: [],
}