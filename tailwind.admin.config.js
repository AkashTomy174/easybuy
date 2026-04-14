module.exports = {
  darkMode: "class",
  content: ["./templates/admin/**/*.html"],
  theme: {
    extend: {
      colors: {
        primary: "#137fec",
        "sidebar-dark": "#0f172a",
        "surface-dark": "#1e293b"
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")]
};
