"""Decision engine: tiers -> accumulator -> gate -> Decision (spec sections 4-10).

One `evaluate()` call is the entire decision path. Both the live gateway and the
offline replay go through here, so a number in the README and a number in the
console come from identical code.
"""
from __future__ import annotations

import time
import uuid

from ..schemas import Decision, ActionRequest, RiskVector
from ..tiers import l0, l1, l2
from ..agent import accumulator
from . import loader, gate

# rough per-tier cost model (USD); L0 never calls a model
COST = {"L0": 0.0, "L1": 0.00002, "L2": 0.0018, "HUMAN": 0.0}


def _rationale(rv: RiskVector, accumulated_in: float, action: ActionRequest,
               verdict: str, band: str, tier: str) -> str:
    bits = []
    if rv.unsupported_claims:
        ex = rv.unsupported_claims[0][:90]
        bits.append(f"{len(rv.unsupported_claims)} claim(s) unsupported by retrieval "
                    f"(e.g. “{ex}”)")
    fabricated = [h for h in rv.pii_entities if not h.in_context]
    if fabricated:
        names = ", ".join(f"{h.entity_type}:{h.text}" for h in fabricated[:2])
        bits.append(f"entity not in context -> privacy+hallucination ({names})")
    if rv.pattern_hits:
        bits.append("matched policy pattern(s): " + ", ".join(rv.pattern_hits))
    if rv.injection_score >= 0.45:
        bits.append(f"possible prompt injection (score {rv.injection_score:.2f})")
    if accumulated_in >= 0.3:
        bits.append(f"conversation carries unverified premise risk "
                    f"(accumulated={accumulated_in:.2f})")
    reason = "; ".join(bits) or "no material risk signals"
    return (f"[{tier}] band={band} -> {verdict} for {action.reversibility} action "
            f"'{action.tool or 'none'}'. {reason}.")


def evaluate(*, response: str, context: list[str], user_turn: str = "",
             action_tool: str | None = None, action_args: dict | None = None,
             policy_name: str, conversation_id: str = "single", turn_index: int = 0,
             request_id: str | None = None, prior_turns: list[str] | None = None,
             self_consistency: float | None = None, use_l2: bool = False) -> Decision:
    request_id = request_id or f"req-{uuid.uuid4().hex[:10]}"
    pack, phash = loader.load(policy_name)
    lat: dict[str, float] = {}
    cost = 0.0

    # --- L0 tripwire (100%) --------------------------------------------------
    t = time.perf_counter()
    entropy = self_consistency if self_consistency is not None else 0.0
    rv = l0.run_l0(response, context, user_turn, pack, entropy_term=entropy,
                   prior_turns=prior_turns)
    lat["l0"] = round((time.perf_counter() - t) * 1000, 3)
    tier = "L0"
    fused = rv.fused

    # --- L1 distilled judge (only inside the uncertainty band, ~8%) ----------
    if l0.is_uncertain(fused, pack):
        t = time.perf_counter()
        proba, l1_block = l1.resolve(rv, pack)
        lat["l1"] = round((time.perf_counter() - t) * 1000, 3)
        cost += COST["L1"]
        tier = "L1"
        fused = round(proba, 4)
        rv.fused = fused
        # --- L2 jury + human (still uncertain, ~1%) --------------------------
        if use_l2 and l0.is_uncertain(fused, pack):
            t = time.perf_counter()
            verdict_jury = l2.jury(rv, response, context)
            lat["l2"] = round((time.perf_counter() - t) * 1000, 3)
            cost += COST["L2"]
            tier = "HUMAN" if verdict_jury.get("route_to_human") else "L2"
            if verdict_jury.get("decision") == "RISKY":
                fused = max(fused, float(pack.get("thresholds", {}).get("l0_high", 0.55)))

    # --- conversation accumulator -------------------------------------------
    accumulated_in = accumulator.carry_in(conversation_id, pack)
    fused_total = accumulator.combine(fused, accumulated_in)
    accumulator.commit(conversation_id, accumulated_in, rv)

    # --- gate ----------------------------------------------------------------
    reversibility, blast = gate.reversibility_of(action_tool, pack)
    action = ActionRequest(tool=action_tool or "", reversibility=reversibility,
                           blast_radius=blast, arguments=action_args or {})
    band = l0.band_of(fused_total, pack)
    if accumulator.should_force_escalate(accumulated_in, pack) and reversibility != "reversible":
        band = "high"
    verdict, escalate, _raw = gate.resolve(band, reversibility, pack)

    lat["total"] = round(sum(v for k, v in lat.items() if k != "total"), 3)
    rv.severity = {"low": 0, "medium": 2, "high": 3}[band]

    return Decision(
        request_id=request_id, conversation_id=conversation_id, turn_index=turn_index,
        use_case=pack.get("pack", ""), jurisdiction=pack.get("jurisdiction", ""),
        policy_hash=phash, tier_reached=tier, risk=rv,
        accumulated_risk=accumulated_in,
        action=action if action_tool else None,
        band=band, verdict=verdict, escalate=escalate,
        rationale=_rationale(rv, accumulated_in, action, verdict, band, tier),
        latency_ms=lat, cost_usd=round(cost, 6),
    )
