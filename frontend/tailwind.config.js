/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        surface: '#1e293b',
        background: '#0f172a',
        border: '#334155',
      },
    },
  },
  plugins: [],
}
