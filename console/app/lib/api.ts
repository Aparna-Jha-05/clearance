// One place that knows where the gateway lives. CORS is open on the API.
// Set NEXT_PUBLIC_API_BASE (a Vercel env var) to your deployed backend URL;
// Next.js inlines it at BUILD time, so set it before deploying. Locally it
// defaults to the uvicorn dev server on :8000.
function resolveBase(): string {
  const env = process.env.NEXT_PUBLIC_API_BASE;
  if (env) return env.replace(/\/$/, "");
  if (
    typeof window !== "undefined" &&
    !["localhost", "127.0.0.1"].includes(window.location.hostname)
  ) {
    return ""; // deployed with no backend configured -> surface a clear error
  }
  return "http://localhost:8000";
}

export const API = resolveBase();

async function j(path: string, opts?: RequestInit) {
  if (!API) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE is not set — point it at your deployed backend URL"
    );
  }
  const r = await fetch(`${API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

export const api = {
  health: () => j("/health"),
  policies: () => j("/api/policies"),
  ledger: (limit = 200, use_case?: string, verdict?: string) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (use_case) q.set("use_case", use_case);
    if (verdict) q.set("verdict", verdict);
    return j(`/api/ledger?${q.toString()}`);
  },
  verify: () => j("/api/ledger/verify"),
  tamper: (seq: number, verdict = "allow") =>
    j("/api/ledger/tamper", { method: "POST", body: JSON.stringify({ seq, verdict }) }),
  seed: () => j("/api/seed", { method: "POST" }),
  paired: () => j("/api/replay/paired"),
  agentic: () => j("/api/replay/agentic"),
  recompute: (use_case: string, overrides: any) =>
    j("/api/tuning/recompute", {
      method: "POST",
      body: JSON.stringify({ use_case, overrides }),
    }),
};

export const VERDICT_COLOR: Record<string, string> = {
  allow: "text-good border-good/40 bg-good/10",
  annotate: "text-accent border-accent/40 bg-accent/10",
  redact: "text-warn border-warn/40 bg-warn/10",
  hold: "text-warn border-warn/40 bg-warn/10",
  block: "text-bad border-bad/40 bg-bad/10",
  escalate: "text-escal border-escal/40 bg-escal/10",
};

export const CAT_COLOR: Record<string, string> = {
  hallucination: "bg-bad/15 text-bad border-bad/30",
  privacy: "bg-escal/15 text-escal border-escal/30",
  policy_violation: "bg-warn/15 text-warn border-warn/30",
  prompt_injection: "bg-accent/15 text-accent border-accent/30",
};

export function catClass(c: string) {
  return CAT_COLOR[c] || "bg-panel2 text-muted border-edge";
}
export function verdictClass(v: string) {
  return VERDICT_COLOR[v] || "text-muted border-edge bg-panel2";
}
