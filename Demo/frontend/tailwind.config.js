/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          light: '#1e40af',
          DEFAULT: '#002855', // Deep navy matching the Emploeralk logo color
          dark: '#001833',
          accent: '#007acc'
        }
      }
    },
  },
  plugins: [],
}

