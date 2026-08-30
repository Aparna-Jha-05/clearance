import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "CLEARANCE — decision layer console",
  description: "Gate the action, not the answer.",
};

function Nav() {
  const items = [
    { href: "/", label: "Live" },
    { href: "/tuning", label: "Tuning" },
    { href: "/ledger", label: "Ledger" },
  ];
  return (
    <header className="sticky top-0 z-20 border-b border-edge bg-ink/85 backdrop-blur">
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
              className="rounded-md px-3 py-1.5 text-sm text-muted transition hover:bg-panel2 hover:text-white"
            >
              {it.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto text-xs text-muted mono">
          gate the action, not the answer
        </div>
      </div>
    </header>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="mx-auto max-w-[1400px] px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
