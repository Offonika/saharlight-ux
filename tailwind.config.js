// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      /* цветовые токены ─ уже добавлены */
      colors: {
        card:       'var(--card)',
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        primary:    'var(--primary)',
        border:     'var(--border)',
        accent:     'var(--accent)',
        muted:      'var(--muted)',
      },

      /* утилита border-border */
      borderColor: { border: 'var(--border)' },

      /* тени */
      boxShadow: {
        'shadow-soft':   '0 1px 4px rgba(0,0,0,.04)',
        'shadow-medium': '0 2px 8px rgba(0,0,0,.06)',
      },

      /* ▶ шрифты */
      fontFamily: {
        inter: ['Inter', 'ui-sans-serif', 'sans-serif'], // ← font-inter
      },
    },
  },
  plugins: [],
}
