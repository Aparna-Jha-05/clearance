"use client";
import { useEffect, useState } from "react";
import { api } from "./lib/api";
import { Card, Verdict, Chip, Meter, bandTone } from "../components/ui";

function norm(v: string) {
  return v === "block_escalate" ? "escalate" : v;
}

// ---- the hero: same text, two actions, two verdicts ------------------------
function PairedHero({ pairs }: any) {
  if (!pairs?.length) return null;
  const p = pairs[0];
  const Side = ({ s, label }: any) => (
    <div className="flex-1 rounded-lg border border-edge bg-panel2 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-muted">{label}</span>
        <Verdict v={norm(s.verdict)} />
      </div>
      <div className="mono text-xs text-muted">
        action <span className="text-white">{s.tool}</span>
        <span className="mx-1">·</span>
        <span
          className={
            s.reversibility === "irreversible" ? "text-bad" : "text-good"
          }
        >
          {s.reversibility}
        </span>
      </div>
      <div className="mt-1 mono text-[11px] text-muted">band {s.band}</div>
    </div>
  );
  return (
    <Card
      title="The paired verdict — identical text, two actions, two verdicts"
      right={
        <span className="rounded bg-escal/15 px-2 py-0.5 text-[10px] font-semibold text-escal">
          THE PITCH
        </span>
      }
    >
      <div className="rounded-lg border border-edge bg-ink/60 p-3">
        <span className="text-[10px] uppercase tracking-wider text-muted">
          one model response
        </span>
        <p className="mt-1 text-sm leading-relaxed text-white">“{p.response}”</p>
      </div>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <Side s={p.A} label="context A" />
        <div className="flex items-center justify-center px-1 text-2xl text-muted">→</div>
        <Side s={p.B} label="context B" />
      </div>
      <p className="mt-3 text-xs text-muted">
        Same fabricated sentence. As a reversible draft it is annotated; driving an
        irreversible refund it is blocked and escalated. Detection is identical —
        the <span className="text-white">decision</span> is not.
      </p>
    </Card>
  );
}

// ---- agentic compounding ---------------------------------------------------
function Agentic({ ag }: any) {
  if (!ag?.turns?.length) return null;
  return (
    <Card title="Agentic compounding — turn 6 blocked on a turn-3 premise">
      <div className="space-y-1.5">
        {ag.turns.map((t: any) => (
          <div
            key={t.turn}
            className="grid grid-cols-[2rem_1fr_7rem_7rem] items-center gap-2 rounded-md border border-edge bg-panel2 px-2 py-1.5"
          >
            <span className="mono text-xs text-muted">#{t.turn}</span>
            <div className="min-w-0">
              <div className="truncate text-xs text-white">{t.response}</div>
              <div className="mt-1 w-40">
                <Meter value={t.accumulated_risk} tone={t.accumulated_risk > 0.6 ? "bad" : "warn"} />
              </div>
            </div>
            <div className="text-center">
              <Verdict v={norm(t.clearance_verdict)} />
              <div className="mt-0.5 text-[9px] text-muted mono">clearance</div>
            </div>
            <div className="text-center">
              <span className="mono text-[11px] text-muted">{t.naive_verdict}</span>
              <div className="mt-0.5 text-[9px] text-muted mono">per-response</div>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted">
        A per-response checker sees turn 6 as well-grounded — it is grounded in the
        conversation. CLEARANCE carries forward that the turn-3 premise was never
        externally supported, and blocks the irreversible action.
      </p>
    </Card>
  );
}

// ---- decision feed ---------------------------------------------------------
function Feed({ rows, onPick }: any) {
  return (
    <Card title={`Live decisions (${rows.length})`}>
      <div className="max-h-[520px] overflow-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-panel text-[10px] uppercase tracking-wider text-muted">
            <tr>
              <th className="pb-2 pr-2">use case</th>
              <th className="pb-2 pr-2">CEG</th>
              <th className="pb-2 pr-2">categories</th>
              <th className="pb-2 pr-2">tier</th>
              <th className="pb-2 pr-2">verdict</th>
              <th className="pb-2 pr-2 text-right">+ms</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any) => {
              const d = r.decision;
              return (
                <tr
                  key={r.seq}
                  onClick={() => onPick(d)}
                  className="cursor-pointer border-t border-edge/60 hover:bg-panel2"
                >
                  <td className="py-1.5 pr-2 mono text-muted">{d.use_case}</td>
                  <td className="py-1.5 pr-2">
                    <div className="w-16">
                      <Meter value={d.risk.ceg} tone={bandTone(d.band)} />
                    </div>
                  </td>
                  <td className="py-1.5 pr-2">
                    <div className="flex flex-wrap gap-1">
                      {(d.risk.categories || []).map((c: string) => (
                        <Chip key={c} label={c} />
                      ))}
                    </div>
                  </td>
                  <td className="py-1.5 pr-2 mono text-muted">{d.tier_reached}</td>
                  <td className="py-1.5 pr-2">
                    <Verdict v={norm(d.verdict)} />
                  </td>
                  <td className="py-1.5 pr-2 text-right mono text-muted">
                    {d.latency_ms?.total ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Detail({ d, onClose }: any) {
  if (!d) return null;
  return (
    <div
      className="fixed inset-0 z-30 flex items-start justify-end bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="mt-14 w-full max-w-md rounded-xl border border-edge bg-panel p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="mono text-xs text-muted">{d.request_id}</span>
          <Verdict v={norm(d.verdict)} />
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <KV k="use case" v={d.use_case} />
          <KV k="jurisdiction" v={d.jurisdiction} />
          <KV k="tier" v={d.tier_reached} />
          <KV k="band" v={d.band} />
          <KV k="groundedness" v={d.risk.groundedness} />
          <KV k="assertiveness" v={d.risk.assertiveness} />
          <KV k="CEG" v={d.risk.ceg} />
          <KV k="fused" v={d.risk.fused} />
          <KV k="accumulated" v={d.accumulated_risk} />
          <KV k="policy_hash" v={(d.policy_hash || "").slice(0, 12)} />
        </div>
        {d.risk.unsupported_claims?.length > 0 && (
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-wider text-muted">
              unsupported claims
            </div>
            {d.risk.unsupported_claims.map((c: string, i: number) => (
              <div
                key={i}
                className="mt-1 rounded border border-bad/30 bg-bad/10 px-2 py-1 text-xs text-bad"
              >
                {c}
              </div>
            ))}
          </div>
        )}
        <div className="mt-3">
          <div className="text-[10px] uppercase tracking-wider text-muted">rationale</div>
          <p className="mt-1 text-xs text-white">{d.rationale}</p>
        </div>
      </div>
    </div>
  );
}
function KV({ k, v }: any) {
  return (
    <div className="rounded border border-edge bg-panel2 px-2 py-1">
      <div className="text-[9px] uppercase text-muted">{k}</div>
      <div className="mono text-white">{String(v)}</div>
    </div>
  );
}

export default function LivePage() {
  const [pairs, setPairs] = useState<any[]>([]);
  const [ag, setAg] = useState<any>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [pick, setPick] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    try {
      let led = await api.ledger(200);
      if (!led.rows?.length) {
        await api.seed();
        led = await api.ledger(200);
      }
      const [p, a] = await Promise.all([api.paired(), api.agentic()]);
      setPairs(p.pairs || []);
      setAg(a);
      setRows(led.rows || []);
    } catch (e: any) {
      setErr(e.message + " — is the gateway running on :8000?");
    }
  }
  async function reseed() {
    setBusy(true);
    try {
      await api.seed();
      await load();
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Live decisions</h1>
          <p className="text-xs text-muted">
            Every request: 100% L0 coverage, escalation only when uncertain,
            immutable ledger row.
          </p>
        </div>
        <button
          onClick={reseed}
          disabled={busy}
          className="rounded-lg border border-edge bg-panel2 px-3 py-1.5 text-xs font-medium hover:bg-edge disabled:opacity-50"
        >
          {busy ? "replaying…" : "↻ replay corpus"}
        </button>
      </div>

      {err && (
        <div className="rounded-lg border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
          {err}
        </div>
      )}

      <PairedHero pairs={pairs} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Agentic ag={ag} />
        <Feed rows={rows} onPick={setPick} />
      </div>

      <Detail d={pick} onClose={() => setPick(null)} />
    </div>
  );
}
