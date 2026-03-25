/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#10131a",
        panel: "#f4efe4",
        accent: "#ff6b35",
        signal: "#1c7c54",
        warn: "#b63a2b",
        muted: "#58606e"
      },
      boxShadow: {
        panel: "0 18px 45px rgba(16, 19, 26, 0.12)"
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        body: ["Segoe UI", "sans-serif"]
      }
    }
  },
  plugins: []
};
