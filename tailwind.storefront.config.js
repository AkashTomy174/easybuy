module.exports = {
  darkMode: "class",
  content: [
    "./templates/core/**/*.html",
    "./templates/user/**/*.html",
    "./templates/seller/**/*.html",
    "./templates/includes/**/*.html",
    "./chatbot/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#4a7c43",
        "primary-dark": "#2d5a27",
        "primary-light": "#6b9e5f",
        "accent-terracotta": "#ff7f50",
        "accent-coral": "#ff6b6b",
        "accent-gold": "#f59e0b",
        "accent-blue": "#0ea5e9",
        "accent-emerald": "#10b981",
        "background-light": "#fdfaf6",
        "background-dark": "#1a1c19",
        "surface-dark": "#232622",
        "surface-light": "#ffffff",
        "soft-gray": "#f3f4f1",
        "sidebar-dark": "#0f172a"
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"]
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
        full: "9999px"
      },
      boxShadow: {
        card: "0 4px 20px -2px rgba(0, 0, 0, 0.06)",
        "card-hover": "0 20px 40px -12px rgba(0, 0, 0, 0.12)",
        button: "0 4px 14px -3px rgba(74, 124, 67, 0.3)",
        gold: "0 4px 14px -3px rgba(245, 158, 11, 0.3)",
        coral: "0 4px 14px -3px rgba(255, 107, 107, 0.3)"
      }
    }
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")]
};
