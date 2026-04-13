/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        /* ── Navy blue — primary actions, buttons, active states ── */
        brand: {
          50:  '#EDF3FF',
          100: '#D4E4FF',
          200: '#A8C5FF',
          300: '#6E9FFF',
          400: '#3B72E0',
          500: '#1E50C0',
          600: '#1B3F8F',   /* primary navy */
          700: '#152B6A',
          800: '#0E1E4A',
          900: '#080F28',
          950: '#040818',
        },
        /* ── Mustard gold — accent highlights, indicators ── */
        accent: {
          50:  '#FFFBEB',
          100: '#FFF3C4',
          200: '#FFE285',
          300: '#FFD04D',
          400: '#F5BC1A',
          500: '#D4A017',   /* mustard primary */
          600: '#B07C0C',
          700: '#8A5E07',
          800: '#654303',
          900: '#402A02',
          950: '#221500',
        },
        /* ── Navy dark — dark-mode background layers ── */
        navy: {
          950: '#060E20',   /* page bg */
          900: '#0A1829',   /* sidebar */
          800: '#0E2038',   /* card */
          700: '#132A4A',   /* hover / subtle border */
          600: '#1A3560',   /* border */
          500: '#234880',   /* muted text bg */
        },
      },
      animation: {
        'fade-in':    'fadeIn 0.25s ease-in-out',
        'slide-up':   'slideUp 0.25s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(8px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
