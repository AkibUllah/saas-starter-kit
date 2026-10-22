import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7ff",
          100: "#d9ecff",
          200: "#bcdfff",
          300: "#8ecbff",
          400: "#59adff",
          500: "#328bfc",
          600: "#1c6bf1",
          700: "#1555de",
          800: "#1845b4",
          900: "#193e8d",
          950: "#142756",
        },
      },
    },
  },
  plugins: [],
};

export default config;
