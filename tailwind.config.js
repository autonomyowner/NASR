/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'hive-cyan': '#06b6d4', // cyan-500
        'hive-cyan-light': '#22d3ee', // cyan-400 for highlights
        'hive-slate': '#0f172a',
        // Keep yellow tokens for semantic warnings
        'hive-yellow': '#eab308', // yellow-500
        'hive-yellow-light': '#facc15', // yellow-400 for highlights
        // New aqua palette
        'aqua-bg': '#D3E3E0', // Background primary
        'aqua-section': '#74B3A5', // Background secondary/section
        'aqua-text': '#4A6C5C', // Text primary
        'aqua-text-secondary': '#5B9179', // Text secondary
        'aqua-accent': '#6EA294', // Accent primary (CTAs)
        'aqua-accent-hover': '#689587', // Accent hover/active
        'coral': '#FF6F61', // Optional contrast accent
        'golden': '#F2C94C', // Optional contrast accent
      },
      backgroundImage: {
        'gradient-hive': 'linear-gradient(to bottom right, #0f172a, #eab308, #0f172a)',
      }
    },
  },
  plugins: [],
} 