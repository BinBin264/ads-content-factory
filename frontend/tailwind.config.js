/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 14px 34px rgba(15, 23, 42, 0.08)",
      },
      backgroundImage: {
        "accent-line": "linear-gradient(90deg, #14b8a6, #f59e0b, #ef4444)",
        "app-shell":
          "linear-gradient(135deg, rgba(20,184,166,0.14), rgba(245,158,11,0.09) 42%, rgba(239,68,68,0.08)), linear-gradient(180deg, #f8fafc, #eef3f8)",
      },
    },
  },
  plugins: [],
};
