import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0a0e14",
        panel: "#111722",
        panel2: "#161d2b",
        edge: "#232c3d",
        muted: "#8494ad",
        accent: "#5eb0ff",
        good: "#3ddc97",
        warn: "#ffcb6b",
        bad: "#ff6b81",
        escal: "#c792ea",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
