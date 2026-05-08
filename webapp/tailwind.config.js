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
      keyframes: {
        "fade-in-out": {
          "0%": { opacity: "0", transform: "translateY(-4px)" },
          "12%, 75%": { opacity: "1", transform: "translateY(0)" },
          "100%": { opacity: "0", transform: "translateY(-4px)" },
        },
        "toast-in": {
          "0%": { opacity: "0", transform: "translateY(-12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in-out": "fade-in-out 3s ease-in-out forwards",
        "toast-in": "toast-in 220ms ease-out forwards",
      },
    },
  },
  plugins: [],
};
