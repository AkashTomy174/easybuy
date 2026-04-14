module.exports = {
  darkMode: "class",
  content: [
    "./templates/seller/sellerregistration_new.html",
    "./templates/seller/seller_registration_success.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2d5a27",
        "primary-dark": "#1e3d1a",
        "accent-terracotta": "#c05e46",
        "background-light": "#fdfaf6",
        "background-dark": "#1a1c19",
        "surface-dark": "#232622"
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")]
};
