"use client";
import { catClass, verdictClass } from "../app/lib/api";

export function Card({ title, right, children, className = "" }: any) {
  return (
    <div className={`rounded-xl border border-edge bg-panel ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between border-b border-edge px-4 py-2.5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            {title}
          </h3>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function Verdict({ v }: { v: string }) {
  return (
    <span
      className={`inline-block rounded-md border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide mono ${verdictClass(
        v
      )}`}
    >
      {v}
    </span>
  );
}

export function Chip({ label }: { label: string }) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium mono ${catClass(
        label
      )}`}
    >
      {label}
    </span>
  );
}

export function Meter({ value, tone = "accent", label }: any) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color =
    tone === "bad" ? "#ff6b81" : tone === "warn" ? "#ffcb6b" : tone === "good" ? "#3ddc97" : "#5eb0ff";
  return (
    <div className="w-full">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel2">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      {label && <div className="mt-1 text-[10px] text-muted mono">{label}</div>}
    </div>
  );
}

export function Stat({ label, value, sub, tone }: any) {
  const color =
    tone === "bad" ? "text-bad" : tone === "good" ? "text-good" : tone === "warn" ? "text-warn" : "text-white";
  return (
    <div className="rounded-lg border border-edge bg-panel2 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-0.5 text-lg font-semibold mono ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-muted mono">{sub}</div>}
    </div>
  );
}

export function bandTone(band: string) {
  return band === "high" ? "bad" : band === "medium" ? "warn" : "good";
}
