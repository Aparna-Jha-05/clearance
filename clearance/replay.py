"""Deterministic corpus replay (spec sections 13, 14).

`python scripts/run_replay.py --offline` runs everything here and must
reproduce every number in the README exactly, on committed fixtures, with no
keys. All demo moments (paired verdict, agentic block) are functions here so
the CLI, the tests, and the console share one implementation.
"""
from __future__ import annotations

import json
import uuid

from .config import CORPUS_DIR
from .schemas import CorpusRecord, Decision
from .policy import engine
from .agent import accumulator
from . import ledger

PACK = {
    "support-assistant": "support-assistant.eu",
    "internal-copilot": "internal-copilot.in",
    "decision-support": "decision-support.eu",
}


def _pack_for(use_case: str) -> str:
    return PACK.get(use_case, "support-assistant.eu")


def load_jsonl(name: str) -> list[CorpusRecord]:
    p = CORPUS_DIR / name
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(CorpusRecord(**json.loads(line)))
    return out


def evaluate_record(rec: CorpusRecord, action_tool: str | None, policy_name: str,
                    cid: str) -> Decision:
    accumulator.reset(cid)
    user = rec.turns[-1]["content"] if rec.turns else ""
    return engine.evaluate(
        response=rec.response, context=rec.retrieved, user_turn=user,
        action_tool=action_tool, policy_name=policy_name,
        conversation_id=cid, request_id=f"{rec.id}-{uuid.uuid4().hex[:6]}",
        self_consistency=rec.self_consistency,
    )


# --- demo: the paired verdict ------------------------------------------------
def replay_paired() -> list[dict]:
    """Same response text, two action contexts, two verdicts. THE pitch."""
    out = []
    for rec in load_jsonl("paired.jsonl"):
        pol = _pack_for(rec.use_case)
        tool_a = (rec.action_requested or {}).get("tool")
        tool_b = (rec.action_requested_b or {}).get("tool")
        da = evaluate_record(rec, tool_a, pol, f"{rec.id}-A")
        db = evaluate_record(rec, tool_b, pol, f"{rec.id}-B")
        out.append({
            "id": rec.id, "response": rec.response, "use_case": rec.use_case,
            "A": {"tool": tool_a, "reversibility": da.action.reversibility if da.action else "reversible",
                  "verdict": da.verdict, "band": da.band,
                  "expected": rec.gold.expected_verdict if rec.gold else None},
            "B": {"tool": tool_b, "reversibility": db.action.reversibility if db.action else "reversible",
                  "verdict": db.verdict, "band": db.band,
                  "expected": rec.gold_b.expected_verdict if rec.gold_b else None},
            "same_text_different_verdict": da.verdict != db.verdict,
            "decisions": [da, db],
        })
    return out


# --- demo: agentic compounding ----------------------------------------------
def replay_agentic(policy_name: str = "internal-copilot.in") -> dict:
    """Process a multi-turn conversation in order. Turn 6's irreversible action
    is blocked on a premise planted at turn 3 that per-response checking passes."""
    recs = sorted(load_jsonl("agentic.jsonl"), key=lambda r: r.turn_index)
    if not recs:
        return {"turns": []}
    cid = recs[0].conversation_id or "agentic-1"
    accumulator.reset(cid)
    turns = []
    for rec in recs:
        user = rec.turns[-1]["content"] if rec.turns else ""
        tool = (rec.action_requested or {}).get("tool")
        d = engine.evaluate(
            response=rec.response, context=rec.retrieved, user_turn=user,
            action_tool=tool, policy_name=policy_name, conversation_id=cid,
            turn_index=rec.turn_index, request_id=f"{rec.id}",
            self_consistency=rec.self_consistency,
        )
        # per-response baseline: evaluate the SAME turn with prior assistant
        # turns folded into context (what a naive per-response checker sees)
        naive_ctx = list(rec.retrieved) + [r.response for r in recs
                                           if r.turn_index < rec.turn_index]
        accumulator.reset(f"{cid}-naive")
        naive = engine.evaluate(
            response=rec.response, context=naive_ctx, user_turn=user,
            action_tool=tool, policy_name=policy_name,
            conversation_id=f"{cid}-naive", request_id=f"{rec.id}-naive",
            self_consistency=rec.self_consistency,
        )
        turns.append({
            "turn": rec.turn_index, "tool": tool,
            "response": rec.response,
            "clearance_verdict": d.verdict, "clearance_band": d.band,
            "accumulated_risk": d.accumulated_risk,
            "naive_verdict": naive.verdict, "naive_band": naive.band,
            "decision": d,
        })
    return {"conversation_id": cid, "turns": turns}


# --- full replay into the ledger --------------------------------------------
def replay_all(write_ledger: bool = True) -> list[Decision]:
    decisions: list[Decision] = []
    if write_ledger:
        ledger.clear()
    for fname in ("support.jsonl", "copilot.jsonl", "decision.jsonl",
                  "adversarial.jsonl", "borderline.jsonl"):
        for rec in load_jsonl(fname):
            pol = _pack_for(rec.use_case)
            tool = (rec.action_requested or {}).get("tool")
            d = evaluate_record(rec, tool, pol, f"{rec.id}")
            decisions.append(d)
            if write_ledger:
                ledger.append(d)
    # paired + agentic into the ledger too, so the Ledger page shows them
    for p in replay_paired():
        for d in p["decisions"]:
            decisions.append(d)
            if write_ledger:
                ledger.append(d)
    for t in replay_agentic().get("turns", []):
        d = t["decision"]
        decisions.append(d)
        if write_ledger:
            ledger.append(d)
    return decisions
