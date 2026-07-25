import type { Config } from "tailwindcss";

// shadcn/ui-compatible config. Full component tokens land with the components in Phase 7.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
