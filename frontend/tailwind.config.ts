import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        fortune: {
          50: "#fef7ee",
          100: "#fdedd3",
          200: "#fad7a5",
          300: "#f6bb6d",
          400: "#f19533",
          500: "#ee7a10",
          600: "#df6008",
          700: "#b9490a",
          800: "#933a10",
          900: "#773210",
        },
      },
    },
  },
  plugins: [],
};

export default config;
