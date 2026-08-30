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

// Set true whenever a call falls back to committed sample data (e.g. the
// backend is asleep on a free-tier cold start). Pages surface a small banner.
export const sample = { active: false };

async function j(path: string, opts?: RequestInit) {
  if (!API) throw new Error("no-backend");
  // fast timeout so a sleeping backend falls back quickly instead of hanging
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 4000);
  try {
    const r = await fetch(`${API}${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
      cache: "no-store",
      signal: ctrl.signal,
    });
    if (!r.ok) throw new Error(`${path} -> ${r.status}`);
    return r.json();
  } finally {
    clearTimeout(t);
  }
}

// Try live; on any failure read the committed sample file and flag sample mode.
async function withSample(path: string, sampleFile: string, opts?: RequestInit) {
  try {
    return await j(path, opts);
  } catch (e) {
    const r = await fetch(`/sample/${sampleFile}`, { cache: "force-cache" });
    if (!r.ok) throw e;
    sample.active = true;
    return { ...(await r.json()), _sample: true };
  }
}

export const api = {
  health: () => j("/health"),
  policies: () => withSample("/api/policies", "policies.json"),
  ledger: (limit = 200, use_case?: string, verdict?: string) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (use_case) q.set("use_case", use_case);
    if (verdict) q.set("verdict", verdict);
    return withSample(`/api/ledger?${q.toString()}`, "ledger.json");
  },
  verify: () => withSample("/api/ledger/verify", "verify.json"),
  paired: () => withSample("/api/replay/paired", "paired.json"),
  agentic: () => withSample("/api/replay/agentic", "agentic.json"),
  recompute: (use_case: string, overrides: any) =>
    withSample(
      "/api/tuning/recompute",
      `tuning-${use_case}.json`,
      { method: "POST", body: JSON.stringify({ use_case, overrides }) }
    ),
  // interactive, live-only: degrade gracefully in sample mode instead of throwing
  seed: async () => {
    try {
      return await j("/api/seed", { method: "POST" });
    } catch {
      sample.active = true;
      return { _sample: true, seeded: 0 };
    }
  },
  tamper: async (seq: number, verdict = "allow") => {
    try {
      return await j("/api/ledger/tamper", {
        method: "POST",
        body: JSON.stringify({ seq, verdict }),
      });
    } catch {
      sample.active = true;
      // simulate the tamper so the "chain broken" demo still shows offline
      return {
        _sample: true,
        tampered: true,
        verify: { ok: false, broken_at: seq, length: 0,
                  reason: "row_hash mismatch (row was mutated)" },
      };
    }
  },
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
