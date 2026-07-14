/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 14px 34px rgba(15, 23, 42, 0.08)",
      },
      backgroundImage: {
        "accent-line": "linear-gradient(90deg, #2563ff, #4d3cf3, #e92e94, #ff9f43)",
        "app-shell":
          "linear-gradient(180deg, #f8f9fe, #f2f4fa)",
      },
    },
  },
  plugins: [],
};
