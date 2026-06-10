/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        laap: {
          gold: '#D4A843',
          dark: '#1A1A2E',
          deeper: '#16213E',
          accent: '#0F3460',
          teal: '#53C8D0',
          purple: '#7C3AED',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
