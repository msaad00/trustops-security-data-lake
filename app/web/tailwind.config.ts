import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        line: "var(--color-line)",
        panel: "var(--color-panel)",
        rail: "var(--color-rail)",
        railLine: "var(--color-rail-line)",
        surface: "var(--color-surface)",
        surfaceMuted: "var(--color-surface-muted)",
        brand: {
          DEFAULT: "#4f7cff",
          cyan: "#30c7d2",
          green: "#16b364",
          red: "#d92d20",
          orange: "#f79009",
          purple: "#7a35ff",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 18px 45px rgba(15,23,42,.08)",
        hero: "0 24px 65px rgba(2,6,23,.22)",
      },
    },
  },
  plugins: [],
};

export default config;
