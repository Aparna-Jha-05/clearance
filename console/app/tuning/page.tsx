"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceDot,
} from "recharts";
import { api } from "../lib/api";
import { Card, Stat } from "../../components/ui";
import { useThemeColors } from "../../components/theme";

// plain-language help shown on hover over each metric tile
const METRIC_HELP: Record<string, string> = {
  precision: "of everything we flagged, the share that was truly risky",
  recall: "of everything truly risky, the share we caught",
  F2: "combined score that weights recall over precision (safety-leaning)",
  "FP rate": "benign requests we wrongly flagged (false alarms)",
  "FN rate": "risky requests we missed",
  "escal / 1k": "irreversible actions sent to a human, per 1,000 requests",
  "reviewer hrs/wk": "estimated human review load at this operating point",
  "$ / 1k": "model spend on the paid tiers, per 1,000 requests",
};

const USE_CASES = [
  { id: "support-assistant", label: "Support assistant (EU)" },
  { id: "internal-copilot", label: "Internal copilot (IN)" },
  { id: "decision-support", label: "Decision support (EU)" },
];

type OP = {
  l0_low: number; l0_high: number; l1_block_above: number; tau: number;
};

const DEFAULTS: Record<string, OP> = {
  "support-assistant": { l0_low: 0.2, l0_high: 0.5, l1_block_above: 0.72, tau: 0.55 },
  "internal-copilot": { l0_low: 0.2, l0_high: 0.48, l1_block_above: 0.7, tau: 0.58 },
  "decision-support": { l0_low: 0.18, l0_high: 0.45, l1_block_above: 0.66, tau: 0.6 },
};

function Slider({ label, value, min, max, step, onChange }: any) {
  return (
    <label className="block">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-muted">{label}</span>
        <span className="mono text-fg">{value.toFixed(2)}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="mt-1 w-full"
      />
    </label>
  );
}

function Panel({ initialUseCase }: { initialUseCase: string }) {
  const [uc, setUc] = useState(initialUseCase);
  const [op, setOp] = useState<OP>(DEFAULTS[initialUseCase]);
  const [m, setM] = useState<any>(null);
  const [ms, setMs] = useState<number>(0);
  const timer = useRef<any>(null);
  const col = useThemeColors() || {
    edge: "#232c3d", muted: "#8494ad", panel: "#111722",
    accent: "#5eb0ff", escal: "#c792ea", bg: "#0a0e14",
  };

  function reset(next: string) {
    setUc(next);
    setOp(DEFAULTS[next]);
  }

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const t0 = performance.now();
      try {
        const res = await api.recompute(uc, {
          l0_low: op.l0_low, l0_high: op.l0_high,
          l1_block_above: op.l1_block_above, tau: op.tau,
        });
        setM(res);
        setMs(Math.round(performance.now() - t0));
      } catch {
        /* gateway down */
      }
    }, 120); // debounce -> comfortably < 300ms perceived
    return () => timer.current && clearTimeout(timer.current);
  }, [uc, op]);

  const curve = useMemo(
    () => (m?.pr_curve || []).map((p: any) => ({ recall: p.recall, precision: p.precision })),
    [m]
  );

  return (
    <div className="rounded-xl border border-edge bg-panel">
      <div className="flex items-center justify-between border-b border-edge px-4 py-2.5">
        <select
          value={uc}
          onChange={(e) => reset(e.target.value)}
          className="rounded-md border border-edge bg-panel2 px-2 py-1 text-xs text-fg"
        >
          {USE_CASES.map((u) => (
            <option key={u.id} value={u.id}>{u.label}</option>
          ))}
        </select>
        <span className="mono text-[10px] text-muted">
          recompute {ms}ms {ms < 300 ? "✓" : ""}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
        {/* sliders */}
        <div className="space-y-3">
          <Slider label="l0_low (flag above)" value={op.l0_low} min={0.05} max={0.6} step={0.01}
            onChange={(v: number) => setOp({ ...op, l0_low: v })} />
          <Slider label="l0_high (escalate above)" value={op.l0_high} min={0.3} max={0.9} step={0.01}
            onChange={(v: number) => setOp({ ...op, l0_high: v })} />
          <Slider label="l1_block_above" value={op.l1_block_above} min={0.5} max={0.95} step={0.01}
            onChange={(v: number) => setOp({ ...op, l1_block_above: v })} />
          <Slider label="tau (groundedness)" value={op.tau} min={0.3} max={0.8} step={0.01}
            onChange={(v: number) => setOp({ ...op, tau: v })} />
          <button
            onClick={() => setOp(DEFAULTS[uc])}
            className="w-full rounded-md border border-edge bg-panel2 px-2 py-1 text-[11px] text-muted hover:bg-edge"
          >
            reset to signed operating point
          </button>
        </div>

        {/* PR curve */}
        <div className="h-[190px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={curve} margin={{ top: 6, right: 8, bottom: 0, left: -22 }}>
              <CartesianGrid stroke={col.edge} strokeDasharray="2 3" />
              <XAxis dataKey="recall" type="number" domain={[0, 1]}
                tick={{ fill: col.muted, fontSize: 9 }} tickCount={6} />
              <YAxis dataKey="precision" type="number" domain={[0, 1]}
                tick={{ fill: col.muted, fontSize: 9 }} tickCount={6} />
              <Tooltip
                contentStyle={{ background: col.panel, border: `1px solid ${col.edge}`, fontSize: 11 }}
                labelStyle={{ color: col.muted }} />
              <Line type="monotone" dataKey="precision" stroke={col.accent} dot={false} strokeWidth={2} />
              {m?.current_point && (
                <ReferenceDot x={m.current_point.recall} y={m.current_point.precision}
                  r={5} fill={col.escal} stroke={col.bg} />
              )}
            </LineChart>
          </ResponsiveContainer>
          <div className="text-center text-[10px] text-muted">
            precision (y) vs recall (x) · ◆ current operating point
          </div>
        </div>
      </div>

      {/* metrics */}
      {m && (
        <div className="grid grid-cols-2 gap-2 px-4 pb-4 sm:grid-cols-4">
          <Stat label="precision" value={m.precision.toFixed(2)} tone="good" help={METRIC_HELP["precision"]} />
          <Stat label="recall" value={m.recall.toFixed(2)} tone={m.recall < 0.8 ? "bad" : "good"} help={METRIC_HELP["recall"]} />
          <Stat label="F2" value={m.f2.toFixed(2)} help={METRIC_HELP["F2"]} />
          <Stat label="FP rate" value={m.fp_rate.toFixed(2)} tone={m.fp_rate > 0.1 ? "warn" : "good"} help={METRIC_HELP["FP rate"]} />
          <Stat label="FN rate" value={m.fn_rate.toFixed(2)} tone={m.fn_rate > 0.15 ? "warn" : "good"} help={METRIC_HELP["FN rate"]} />
          <Stat label="escal / 1k" value={m.escalations_per_1000} sub="irreversible" help={METRIC_HELP["escal / 1k"]} />
          <Stat label="reviewer hrs/wk" value={m.reviewer_hours_per_week} tone="warn" help={METRIC_HELP["reviewer hrs/wk"]} />
          <Stat label="$ / 1k" value={m.cost_per_1000_usd.toFixed(4)} sub={`p95 +${m.added_p95_latency_ms}ms`} help={METRIC_HELP["$ / 1k"]} />
        </div>
      )}
    </div>
  );
}

export default function TuningPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold">Operating point</h1>
        <p className="text-xs text-muted">
          The threshold set is a signed governance artifact. Two use cases,
          deliberately different operating points — different risk tolerance,
          visible side by side. Recompute runs against the labelled corpus in
          &lt; 300ms.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel initialUseCase="support-assistant" />
        <Panel initialUseCase="decision-support" />
      </div>
      <p className="text-xs text-muted">
        Notice decision-support sits at a tighter point (lower l0_high, escalates
        irreversible advice from the medium band) than support-assistant. Same
        engine, same corpus, different appetite — that is the product.
      </p>
    </div>
  );
}
