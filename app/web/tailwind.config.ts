import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--rgb-ink) / <alpha-value>)",
        muted: "rgb(var(--rgb-muted) / <alpha-value>)",
        line: "rgb(var(--rgb-line) / <alpha-value>)",
        panel: "rgb(var(--rgb-panel) / <alpha-value>)",
        rail: "rgb(var(--rgb-rail) / <alpha-value>)",
        railLine: "rgb(var(--rgb-rail-line) / <alpha-value>)",
        surface: "rgb(var(--rgb-surface) / <alpha-value>)",
        surfaceMuted: "rgb(var(--rgb-surface-muted) / <alpha-value>)",
        brand: {
          DEFAULT: "#4f7cff",
          cyan: "#30c7d2",
          green: "#059669",
          red: "#dc2626",
          orange: "#d97706",
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
        card: "var(--shadow-card)",
        hero: "var(--shadow-hero)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      transitionDuration: {
        fast: "var(--motion-fast)",
        base: "var(--motion-base)",
        slow: "var(--motion-slow)",
      },
    },
  },
  plugins: [],
};

export default config;
