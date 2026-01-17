/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#FFF8E8',
        sand: '#F7EED3',
        sage: '#AAB396',
        espresso: '#674636',
        ink: '#3F2A20'
      },
      boxShadow: {
        paper: '0 6px 20px rgba(103, 70, 54, 0.18)',
        lift: '0 10px 30px rgba(103, 70, 54, 0.22)'
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.5rem'
      },
      fontFamily: {
        sans: ['"Manrope"', 'ui-sans-serif', 'system-ui'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular']
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' }
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' }
        }
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        shimmer: 'shimmer 1.2s ease-in-out infinite'
      }
    }
  },
  plugins: []
}
