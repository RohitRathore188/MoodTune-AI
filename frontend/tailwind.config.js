/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#08090d",
        card: "rgba(22, 25, 35, 0.65)",
        cardBorder: "rgba(255, 255, 255, 0.08)",
        glassHighlight: "rgba(255, 255, 255, 0.05)",
        mood: {
          energetic: "#f59e0b",
          positive: "#10b981",
          calm: "#06b6d4",
          neutral: "#8b5cf6",
          reflective: "#6366f1",
          low_energy: "#64748b",
          tense: "#f43f5e"
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'spin-slow': 'spin 20s linear infinite',
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        }
      },
      backdropBlur: {
        'xs': '2px',
        '2xl': '32px',
      }
    },
  },
  plugins: [],
}
