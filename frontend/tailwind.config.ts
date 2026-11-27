import type { Config } from 'tailwindcss';
import { fontFamily } from 'tailwindcss/defaultTheme';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: '',
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },
    extend: {
      // ─── TADA Brand Color System ─────────────────────────────
      colors: {
        // Primary Navy / Dark Brand
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',    // Primary Indigo
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        // Accent — Electric Teal
        accent: {
          50:  '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',    // Accent light
          500: '#06b6d4',    // Primary Cyan
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        // Signal colors
        signal: {
          risk:        '#ef4444',  // Red
          opportunity: '#22c55e',  // Green
          trend:       '#3b82f6',  // Blue
          threat:      '#f97316',  // Orange
          emerging:    '#a855f7',  // Purple
        },
        // Urgency
        urgency: {
          critical: '#dc2626',
          high:     '#ea580c',
          medium:   '#ca8a04',
          low:      '#16a34a',
        },
        // Dark surface palette
        surface: {
          DEFAULT: '#0f1117',
          elevated: '#161b22',
          border:   '#21262d',
          muted:    '#30363d',
          subtle:   '#1c2128',
        },
        // Semantic tokens (shadcn/ui compatible)
        border:      'hsl(var(--border))',
        input:       'hsl(var(--input))',
        ring:        'hsl(var(--ring))',
        background:  'hsl(var(--background))',
        foreground:  'hsl(var(--foreground))',
        primary: {
          DEFAULT:    'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT:    'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT:    'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT:    'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        popover: {
          DEFAULT:    'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT:    'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },

      // ─── Typography ──────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', ...fontFamily.sans],
        mono: ['JetBrains Mono', ...fontFamily.mono],
      },

      // ─── Border Radius ───────────────────────────────────────
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },

      // ─── Keyframes ───────────────────────────────────────────
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to:   { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to:   { height: '0' },
        },
        'slide-in-from-right': {
          '0%':   { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.5' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },

      // ─── Animations ──────────────────────────────────────────
      animation: {
        'accordion-down':      'accordion-down 0.2s ease-out',
        'accordion-up':        'accordion-up 0.2s ease-out',
        'slide-in-from-right': 'slide-in-from-right 0.3s ease-out',
        'fade-in':             'fade-in 0.4s ease-out',
        'shimmer':             'shimmer 2s linear infinite',
      },

      // ─── Background Gradients ────────────────────────────────
      backgroundImage: {
        'gradient-tada':      'linear-gradient(135deg, #1e1b4b 0%, #083344 100%)',
        'gradient-card':      'linear-gradient(145deg, #161b22 0%, #1c2128 100%)',
        'gradient-signal':    'linear-gradient(90deg, #6366f1 0%, #06b6d4 100%)',
      },

      // ─── Box Shadows ─────────────────────────────────────────
      boxShadow: {
        'card':     '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.6)',
        'elevated': '0 4px 16px rgba(0,0,0,0.5)',
        'glow-brand': '0 0 20px rgba(99,102,241,0.3)',
        'glow-accent': '0 0 20px rgba(6,182,212,0.3)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
