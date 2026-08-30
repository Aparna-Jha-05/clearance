"""The judge's entry point (spec sections 13, 14).

    python scripts/run_replay.py --offline

Runs entirely on committed corpus + fixtures, no keys, and reproduces every
number the README quotes. Prints the paired verdict, the agentic block, the
per-use-case results table, and seeds the hash-chained ledger.
"""
from __future__ import annotations

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:  # Windows consoles default to cp1252; force UTF-8 so glyphs render
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="force offline (default posture)")
    ap.add_argument("--tier", choices=["l0", "all"], default="all")
    args = ap.parse_args()
    if args.offline:
        os.environ["CLEARANCE_OFFLINE"] = "1"

    from clearance import replay, ledger, metrics
    from clearance.detectors.embeddings import backend_name
    from clearance.detectors.nlp import nlp_backend

    print("=" * 72)
    print(" CLEARANCE offline replay  —  gate the action, not the answer")
    print("=" * 72)
    print(f" embeddings backend: {backend_name()}")
    print(f" nlp backend:        {nlp_backend()}")
    print()

    # --- 1. THE PAIRED VERDICT ----------------------------------------------
    print("―― 1. Paired verdict: same text, different action, different verdict ――")
    for p in replay.replay_paired():
        print(f"\n  [{p['id']}]  “{p['response'][:70]}…”")
        def norm(v):
            return "escalate" if v in ("block_escalate", "escalate") else v
        for side in ("A", "B"):
            s = p[side]
            mark = "✓" if norm(s["verdict"]) == norm(s["expected"]) else "✗"
            print(f"    {side}: {s['tool']:<14} {s['reversibility']:<12} "
                  f"-> {s['verdict']:<16} (band {s['band']}, expected {s['expected']}) {mark}")
        print(f"    same text, different verdict: {p['same_text_different_verdict']}")

    # --- 2. AGENTIC COMPOUNDING ---------------------------------------------
    print("\n\n―― 2. Agentic compounding: turn-6 blocked on a turn-3 premise ――")
    ag = replay.replay_agentic()
    for t in ag["turns"]:
        tool = t["tool"] or "-"
        print(f"  turn {t['turn']}: acc={t['accumulated_risk']:.2f}  "
              f"clearance={t['clearance_verdict']:<16} (band {t['clearance_band']})  "
              f"| naive per-response={t['naive_verdict']:<10} tool={tool}")
    t6 = ag["turns"][-1]
    print(f"\n  => turn 6 irreversible refund: Clearance='{t6['clearance_verdict']}' "
          f"while a naive per-response checker says '{t6['naive_verdict']}'.")

    # --- 3. RESULTS TABLE ----------------------------------------------------
    print("\n\n―― 3. Results by use case (default operating point) ――")
    hdr = f"  {'use case':<20}{'P':>7}{'R':>7}{'F2':>7}{'FP':>7}{'FN':>7}{'p95ms':>8}{'$/1k':>9}"
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    for uc in ("support-assistant", "internal-copilot", "decision-support"):
        m = metrics.recompute(uc)
        print(f"  {uc:<20}{m['precision']:>7.2f}{m['recall']:>7.2f}{m['f2']:>7.2f}"
              f"{m['fp_rate']:>7.2f}{m['fn_rate']:>7.2f}"
              f"{m['added_p95_latency_ms']:>8.2f}{m['cost_per_1000_usd']:>9.4f}")

    # --- 4. LEDGER -----------------------------------------------------------
    print("\n\n―― 4. Hash-chained ledger ――")
    decisions = replay.replay_all(write_ledger=True)
    v = ledger.verify_chain()
    print(f"  seeded {len(decisions)} decisions into the ledger")
    print(f"  chain verify: {'OK ✓' if v['ok'] else 'BROKEN ✗'}  (length {v['length']})")
    print("\nDone. Start the console API with:  uvicorn clearance.app:app --reload")


if __name__ == "__main__":
    main()
