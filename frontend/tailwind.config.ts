import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#ffffff",
      bg: "#e2e5dc",
      primary: "#6d8669",
      accent: "#ada482",
      text: "#000000",
      discovered: "#9aa0a0",
      applied: "#7b93ad",
      oa: "#b3936a",
      interview: "#8a7bab",
      ghosted: "#a89a8c",
      rejected: "#b06a5f",
    },
    extend: {},
  },
  plugins: [],
};

export default config;
