"use client";
import { useEffect, useState } from "react";

const KEY = "clearance-theme";

export function applyTheme(theme: "light" | "dark") {
  const root = document.documentElement;
  if (theme === "light") root.setAttribute("data-theme", "light");
  else root.setAttribute("data-theme", "dark");
  try {
    localStorage.setItem(KEY, theme);
  } catch {}
  window.dispatchEvent(new Event("themechange"));
}

export function getTheme(): "light" | "dark" {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.getAttribute("data-theme") === "light"
    ? "light"
    : "dark";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  useEffect(() => setTheme(getTheme()), []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
  };
  return (
    <button
      onClick={toggle}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      className="flex items-center gap-1.5 rounded-md border border-edge bg-panel2 px-2.5 py-1.5 text-xs text-muted transition hover:text-fg"
    >
      <span aria-hidden>{theme === "dark" ? "☀" : "☾"}</span>
      <span className="hidden sm:inline">{theme === "dark" ? "Light" : "Dark"}</span>
    </button>
  );
}

// Read the CSS palette as concrete rgb() strings for Recharts (which cannot use
// Tailwind classes). Re-reads whenever the theme changes.
export function useThemeColors() {
  const read = () => {
    if (typeof document === "undefined") return null;
    const cs = getComputedStyle(document.documentElement);
    const v = (n: string) => `rgb(${cs.getPropertyValue(`--${n}`).trim()})`;
    return {
      bg: v("bg"), panel: v("panel"), edge: v("edge"), muted: v("muted"),
      fg: v("fg"), accent: v("accent"), escal: v("escal"),
      good: v("good"), warn: v("warn"), bad: v("bad"),
    };
  };
  const [colors, setColors] = useState<any>(null);
  useEffect(() => {
    setColors(read());
    const on = () => setColors(read());
    window.addEventListener("themechange", on);
    return () => window.removeEventListener("themechange", on);
  }, []);
  return colors;
}
