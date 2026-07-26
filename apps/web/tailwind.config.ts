import type { Config } from "tailwindcss";

const withAlpha = (v: string) => `rgb(var(${v}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: withAlpha("--bg"),
        surface: withAlpha("--surface"),
        surface2: withAlpha("--surface-2"),
        ink: withAlpha("--text"),
        muted: withAlpha("--muted"),
        faint: withAlpha("--faint"),
        line: withAlpha("--line"),
        accent: withAlpha("--accent"),
        "accent-ink": withAlpha("--accent-ink"),
        ok: withAlpha("--ok"),
        warn: withAlpha("--warn"),
        err: withAlpha("--err"),
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        serif: [
          "ui-serif",
          "Iowan Old Style",
          "Palatino Linotype",
          "Palatino",
          "Georgia",
          "Cambria",
          "serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        lg: "16px",
        xl: "20px",
      },
      letterSpacing: {
        tightest: "-0.03em",
      },
      transitionTimingFunction: {
        out: "var(--ease-out)",
        smooth: "var(--ease-in-out)",
      },
      boxShadow: {
        soft: "0 1px 0 rgb(var(--line) / 0.04), 0 12px 40px -12px rgb(0 0 0 / 0.6)",
      },
    },
  },
  plugins: [],
};

export default config;
