"""Throughput + latency benchmark (spec section 3 Tier C, M9).

Runs the L0 tripwire over the corpus repeatedly and reports requests/sec and
p50/p95/p99 added latency, plus the weekly-volume extrapolation the console
quotes. Single-machine, local -- not a production load number (limitations.md).

    python scripts/bench.py --iters 5
"""
from __future__ import annotations

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=5)
    args = ap.parse_args()

    from clearance import replay
    from clearance.tiers import l0
    from clearance.policy import loader

    packs = {"support-assistant": "support-assistant.eu",
             "internal-copilot": "internal-copilot.in",
             "decision-support": "decision-support.eu"}
    records = []
    for f in ("support.jsonl", "copilot.jsonl", "decision.jsonl",
              "adversarial.jsonl", "borderline.jsonl"):
        records.extend(replay.load_jsonl(f))

    lat = []
    t_start = time.perf_counter()
    for _ in range(args.iters):
        for rec in records:
            pack, _ = loader.load(packs.get(rec.use_case, "support-assistant.eu"))
            user = rec.turns[-1]["content"] if rec.turns else ""
            t = time.perf_counter()
            l0.run_l0(rec.response, rec.retrieved, user, pack,
                      entropy_term=rec.self_consistency or 0.0)
            lat.append((time.perf_counter() - t) * 1000)
    elapsed = time.perf_counter() - t_start

    lat.sort()
    n = len(lat)

    def pct(p):
        return lat[min(n - 1, int(p * n))]

    rps = n / elapsed
    print("CLEARANCE L0 benchmark (single core, local)")
    print(f"  requests scored : {n}")
    print(f"  throughput      : {rps:,.0f} req/sec")
    print(f"  latency p50/p95/p99 : {pct(0.50):.2f} / {pct(0.95):.2f} / {pct(0.99):.2f} ms")
    print(f"  weekly extrapolation @ this rate: {rps * 3600 * 24 * 7:,.0f} req/week")
    if pct(0.95) < 15:
        print("  p95 < 15ms target: MET")
    else:
        print("  p95 target 15ms: not met on this machine (embedding backend?)")


if __name__ == "__main__":
    main()
