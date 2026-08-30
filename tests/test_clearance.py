"""The six required tests (spec section 15).

Runnable with pytest, or directly:  python tests/test_clearance.py
Every test forces offline mode so it depends on nothing but committed data.
"""
from __future__ import annotations

import os
import sys

os.environ["CLEARANCE_OFFLINE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clearance.policy import engine, loader, gate
from clearance.tiers import l0
from clearance.agent import accumulator
from clearance import ledger, replay


def _norm(v):
    return "escalate" if v in ("escalate", "block_escalate") else v


# 1. Paired-context: same text, two actions, two verdicts ---------------------
def test_paired_same_text_two_verdicts():
    pairs = replay.replay_paired()
    assert pairs, "no paired records found"
    for p in pairs:
        assert p["same_text_different_verdict"], f"{p['id']} did not diverge"
        assert _norm(p["A"]["verdict"]) == _norm(p["A"]["expected"])
        assert _norm(p["B"]["verdict"]) == _norm(p["B"]["expected"])
        # A is reversible -> not blocked; B is irreversible -> escalated
        assert p["A"]["verdict"] in ("allow", "annotate")
        assert _norm(p["B"]["verdict"]) == "escalate"


# 2. Overlap: fabricated named-person detail -> {hallucination, privacy} -------
def test_overlap_categories():
    pack = loader.load_pack("internal-copilot.in")
    rv = l0.run_l0(
        response="Rahul Verma's current salary is 1450000 and he was flagged as underperforming.",
        context=["Compensation figures are confidential and not available in this workspace."],
        user_turn="Tell me about Rahul Verma.", policy=pack,
    )
    assert "hallucination" in rv.categories
    assert "privacy" in rv.categories
    assert {"hallucination", "privacy"} <= rv.categories


# 3. Latch fail-closed: no verdict -> irreversible action not released ---------
def test_latch_fail_closed():
    from clearance.latch import Latch
    from clearance.schemas import Decision, ActionRequest
    pack = loader.load_pack("support-assistant.eu")
    latch = Latch()
    d = Decision(request_id="r1", verdict="allow",
                 action=ActionRequest(tool="refund.issue", reversibility="irreversible"))
    latch.park("r1", "refund.issue", "irreversible", pack.get("latch_ms", 200))
    out = latch.resolve(d, pack, timed_out=True)
    assert out["action_released"] is False, "irreversible action released on timeout!"
    assert out["outcome"] == "dropped_fail_closed"
    # a reversible action, by contrast, fails open
    d2 = Decision(request_id="r2", verdict="allow",
                  action=ActionRequest(tool="ticket.note", reversibility="reversible"))
    out2 = latch.resolve(d2, pack, timed_out=True)
    assert out2["action_released"] is True


# 4. Ledger tamper: mutate a row -> chain verification fails -------------------
def test_ledger_tamper_detected():
    ledger.clear()
    replay.replay_all(write_ledger=True)
    assert ledger.verify_chain()["ok"] is True
    rows = ledger.rows(limit=5)
    seq = rows[len(rows) // 2]["seq"]
    assert ledger.tamper(seq, new_verdict="allow")
    v = ledger.verify_chain()
    assert v["ok"] is False, "tamper not detected"
    assert v["broken_at"] is not None


# 5. Policy swap: same input, two packs, two verdicts, two hashes -------------
def test_policy_swap_two_verdicts():
    text = ("You are entitled to a full bereavement refund of 200 within 30 days, "
            "and we will refund it to your card now.")
    ctx = ["Returns must be initiated within 14 days for unused items in original packaging."]
    d_eu = engine.evaluate(response=text, context=ctx, action_tool="refund.issue",
                           policy_name="support-assistant.eu", conversation_id="eu")
    d_in = engine.evaluate(response=text, context=ctx, action_tool="refund.issue",
                           policy_name="support-assistant.in", conversation_id="in")
    assert d_eu.policy_hash != d_in.policy_hash
    assert d_eu.verdict != d_in.verdict, (d_eu.verdict, d_in.verdict)
    assert _norm(d_eu.verdict) == "escalate" and d_in.verdict == "hold"


# 6. Agentic accumulator: turn-6 blocked on a turn-3 premise ------------------
def test_agentic_block_on_prior_premise():
    ag = replay.replay_agentic()
    turns = ag["turns"]
    t6 = turns[-1]
    assert t6["turn"] == 6 and t6["tool"] == "refund.issue"
    assert _norm(t6["clearance_verdict"]) in ("escalate", "block", "hold")
    assert _norm(t6["clearance_verdict"]) == "escalate"
    # the naive per-response checker (conversation folded into context) passes it
    assert t6["naive_verdict"] in ("allow", "annotate")
    assert t6["clearance_verdict"] != t6["naive_verdict"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
