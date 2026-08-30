"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, Verdict } from "../../components/ui";

function norm(v: string) {
  return v === "block_escalate" ? "escalate" : v;
}

export default function LedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [verify, setVerify] = useState<any>(null);
  const [uc, setUc] = useState("");
  const [verdict, setVerdict] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    try {
      let led = await api.ledger(300, uc || undefined, verdict || undefined);
      if (!led.rows?.length && !uc && !verdict) {
        await api.seed();
        led = await api.ledger(300);
      }
      setRows(led.rows || []);
      setVerify(await api.verify());
    } catch (e: any) {
      setErr(e.message + " — is the gateway running on :8000?");
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uc, verdict]);

  async function doVerify() {
    setVerify(await api.verify());
  }
  async function tamperMid() {
    setBusy(true);
    try {
      const mid = rows[Math.floor(rows.length / 2)];
      if (mid) {
        const res = await api.tamper(mid.seq, mid.decision.verdict === "allow" ? "escalate" : "allow");
        setVerify(res.verify);
        await load();
      }
    } finally {
      setBusy(false);
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

  const ok = verify?.ok;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Ledger</h1>
          <p className="text-xs text-muted">
            Append-only, hash-chained. Every row commits to the previous row&apos;s
            hash and carries the deciding policy_hash.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={reseed} disabled={busy}
            className="rounded-lg border border-edge bg-panel2 px-3 py-1.5 text-xs hover:bg-edge disabled:opacity-50">
            ↻ reseed
          </button>
          <button onClick={tamperMid} disabled={busy}
            className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-1.5 text-xs text-bad hover:bg-bad/20 disabled:opacity-50">
            ⚠ tamper a row
          </button>
          <button onClick={doVerify}
            className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-1.5 text-xs text-accent hover:bg-accent/20">
            verify chain
          </button>
        </div>
      </div>

      {err && (
        <div className="rounded-lg border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">{err}</div>
      )}

      {verify && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            ok ? "border-good/40 bg-good/10 text-good" : "border-bad/40 bg-bad/10 text-bad"
          }`}
        >
          {ok ? (
            <>✓ chain intact — {verify.length} rows verified, no tampering detected.</>
          ) : (
            <>✗ chain BROKEN at seq {verify.broken_at}: {verify.reason}. The tampered row no
              longer matches its hash — the audit trail caught it.</>
          )}
        </div>
      )}

      <Card
        title="Audit trail"
        right={
          <div className="flex items-center gap-2">
            <select value={uc} onChange={(e) => setUc(e.target.value)}
              className="rounded border border-edge bg-panel2 px-2 py-1 text-[11px]">
              <option value="">all use cases</option>
              <option value="support-assistant">support-assistant</option>
              <option value="internal-copilot">internal-copilot</option>
              <option value="decision-support">decision-support</option>
            </select>
            <select value={verdict} onChange={(e) => setVerdict(e.target.value)}
              className="rounded border border-edge bg-panel2 px-2 py-1 text-[11px]">
              <option value="">all verdicts</option>
              {["allow", "annotate", "redact", "hold", "block", "escalate"].map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>
        }
      >
        <div className="max-h-[560px] overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-panel text-[10px] uppercase tracking-wider text-muted">
              <tr>
                <th className="pb-2 pr-2">#</th>
                <th className="pb-2 pr-2">use case</th>
                <th className="pb-2 pr-2">verdict</th>
                <th className="pb-2 pr-2">policy_hash</th>
                <th className="pb-2 pr-2">prev → row hash</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r: any) => (
                <tr key={r.seq} className="border-t border-edge/60 hover:bg-panel2">
                  <td className="py-1.5 pr-2 mono text-muted">{r.seq}</td>
                  <td className="py-1.5 pr-2 mono text-muted">{r.decision.use_case}</td>
                  <td className="py-1.5 pr-2"><Verdict v={norm(r.decision.verdict)} /></td>
                  <td className="py-1.5 pr-2 mono text-muted">{(r.decision.policy_hash || "").slice(0, 10)}</td>
                  <td className="py-1.5 pr-2 mono text-[10px] text-muted">
                    {r.prev_hash.slice(0, 8)} → <span className="text-accent">{r.row_hash.slice(0, 8)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
