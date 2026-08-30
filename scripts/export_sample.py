"""Export committed sample JSON for the console's offline fallback.

When the console is deployed on Vercel and its backend is asleep (Render free
tier cold start) or not configured, the pages read these files from
console/public/sample/ so the demo is never blank. Regenerate after changing
the corpus or policies:

    python scripts/export_sample.py
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("CLEARANCE_OFFLINE", "1")

from clearance import replay, ledger, metrics
from clearance.policy import loader

OUT = Path(__file__).resolve().parent.parent / "console" / "public" / "sample"
OUT.mkdir(parents=True, exist_ok=True)


def write(name: str, obj: dict):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote console/public/sample/{name}")


def main():
    # seed a fresh ledger so the sample rows are chain-consistent
    replay.replay_all(write_ledger=True)

    # paired (strip decision objects)
    pairs = [{k: v for k, v in p.items() if k != "decisions"} for p in replay.replay_paired()]
    write("paired.json", {"pairs": pairs})

    # agentic
    ag = replay.replay_agentic()
    write("agentic.json", {
        "conversation_id": ag.get("conversation_id"),
        "turns": [{k: v for k, v in t.items() if k != "decision"} for t in ag.get("turns", [])],
    })

    # ledger + verify
    rows = ledger.rows(limit=90)
    write("ledger.json", {"rows": rows})
    write("verify.json", ledger.verify_chain())

    # policies
    pol = []
    for name in loader.list_packs():
        pack, phash = loader.load(name)
        pol.append({"name": name, "pack": pack.get("pack"),
                    "jurisdiction": pack.get("jurisdiction"),
                    "risk_appetite": pack.get("risk_appetite"),
                    "policy_hash": phash[:16],
                    "operating_point": pack.get("operating_point", {})})
    write("policies.json", {"policies": pol})

    # tuning snapshots at the default operating point, per use case
    for uc in ("support-assistant", "internal-copilot", "decision-support"):
        write(f"tuning-{uc}.json", metrics.recompute(uc))

    print("\nsample export complete.")


if __name__ == "__main__":
    main()
