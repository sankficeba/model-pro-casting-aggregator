/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Подобрано под скрины (тёмный navy-фон, золотистый акцент)
        bg: {
          DEFAULT: "#0d1326",
          surface: "#161d35",
          card: "#1a2240",
        },
        accent: {
          DEFAULT: "#f5b50a",
          hover: "#ffc933",
        },
        primary: {
          DEFAULT: "#3b82f6",
          hover: "#2563eb",
        },
      },
      borderRadius: {
        chip: "9999px",
        card: "14px",
      },
    },
  },
  plugins: [],
};
