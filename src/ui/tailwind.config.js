/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./App.tsx",
  ],
  theme: {
    extend: {
      // Neutral enterprise-safe colors per UX Behavior (#12)
      colors: {
        // No security-themed colors per Copy Rules (#13)
      },
    },
  },
  plugins: [],
}
