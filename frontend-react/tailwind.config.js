// NOTE: Do not upgrade to Tailwind CSS v4.1.7 (or potentially other early v4 versions)
// due to a bug where the CLI tool is not installed correctly (missing 'bin' in package.json).
// Stick with v3.x until this is confirmed fixed in a stable v4 release.

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: false,
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'custom-debug': '#123456',
      }
    },
  },
  plugins: [],
} 