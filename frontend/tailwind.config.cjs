/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      keyframes: {
        'dot-bounce': {
          '0%, 80%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '40%':            { transform: 'translateY(-5px)', opacity: '1' },
        },
        'blink': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0' },
        },
      },
      animation: {
        'dot-bounce': 'dot-bounce 1.3s ease-in-out infinite',
        'blink':      'blink 0.9s step-end infinite',
      },
    },
  },
  plugins: [],
}
