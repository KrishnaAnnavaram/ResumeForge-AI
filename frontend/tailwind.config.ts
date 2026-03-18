import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0a0b0e',
        'bg-surface': '#111318',
        'bg-elevated': '#191d26',
        'bg-border': '#252a38',
        'accent-primary': '#f5a623',
        'accent-secondary': '#3b82f6',
        'accent-success': '#22c55e',
        'accent-warning': '#f59e0b',
        'accent-error': '#ef4444',
        'text-primary': '#f0f2f7',
        'text-secondary': '#8892a4',
        'text-tertiary': '#4f5a6e',
        'text-accent': '#f5a623',
      },
      fontFamily: {
        display: ['DM Serif Display', 'serif'],
        body: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        sm: '0 1px 3px rgba(0,0,0,0.4)',
        md: '0 4px 16px rgba(0,0,0,0.5)',
        lg: '0 16px 48px rgba(0,0,0,0.6)',
        accent: '0 0 24px rgba(245,166,35,0.15)',
      },
      borderRadius: {
        sm: '4px',
        md: '8px',
        lg: '12px',
      },
    },
  },
  plugins: [],
} satisfies Config
