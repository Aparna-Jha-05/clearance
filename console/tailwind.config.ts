import type { Config } from "tailwindcss";

// Colors are CSS variables (space-separated RGB channels) so Tailwind's alpha
// modifiers (bg-good/10, border-accent/40) keep working while the palette swaps
// between light and dark. Values live in app/globals.css.
const c = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: c("bg"),
        ink: c("bg"), // alias: existing bg-ink usages map to the page background
        panel: c("panel"),
        panel2: c("panel2"),
        edge: c("edge"),
        muted: c("muted"),
        fg: c("fg"),
        accent: c("accent"),
        good: c("good"),
        warn: c("warn"),
        bad: c("bad"),
        escal: c("escal"),
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
