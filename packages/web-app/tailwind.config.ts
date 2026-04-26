import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        mental: {
          50: "#eff6ff",
          500: "#3b82f6",
          700: "#1d4ed8",
        },
        intent: {
          50: "#fef2f2",
          500: "#ef4444",
          700: "#b91c1c",
        },
      },
    },
  },
  plugins: [],
};

export default config;
