import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { ThemeToggle } from "../components/theme";

export const metadata: Metadata = {
  title: "CLEARANCE — decision layer console",
  description: "Gate the action, not the answer.",
};

// Set the theme before first paint so there is no flash.
const themeInit = `(function(){try{var t=localStorage.getItem('clearance-theme');document.documentElement.setAttribute('data-theme', t==='light'?'light':'dark');}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;

function Nav() {
  const items = [
    { href: "/", label: "Live", hint: "decisions as they happen" },
    { href: "/tuning", label: "Tuning", hint: "the operating point" },
    { href: "/ledger", label: "Ledger", hint: "the audit trail" },
  ];
  return (
    <header className="sticky top-0 z-20 border-b border-edge bg-bg/85 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-6 py-3">
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-6 rounded-md bg-gradient-to-br from-accent to-escal" />
          <span className="text-sm font-semibold tracking-wide">CLEARANCE</span>
          <span className="hidden text-xs text-muted sm:inline">
            · the decision layer above detection
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {items.map((it) => (
            <Link
              key={it.href}
              href={it.href}
              title={it.hint}
              className="rounded-md px-3 py-1.5 text-sm text-muted transition hover:bg-panel2 hover:text-fg"
            >
              {it.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <span className="hidden text-xs text-muted mono md:inline">
            gate the action, not the answer
          </span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body>
        <Nav />
        <main className="mx-auto max-w-[1400px] px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
