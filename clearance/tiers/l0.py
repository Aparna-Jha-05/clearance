"""Layer 0 tripwire (spec sections 7, 9).

100% of traffic, no LLM call, p95 target < 15ms on one core. Runs the five
local detectors behind the adapter interface, computes the confidence-evidence
gap, and fuses everything into a single scalar the gate can band on.

The fused scalar uses the policy detector WEIGHTS, so re-weighting a pack in the
tuning console moves this number and therefore every downstream verdict.
"""
from __future__ import annotations

from ..schemas import RiskVector, PIIHit
from ..detectors.base import DetectionRequest
from ..detectors import registry


def _ceg(assertiveness: float, groundedness: float, entropy_term: float) -> float:
    # spec section 7:  ceg = assertiveness * (1 - groundedness) * (1 + entropy) / 2
    return max(0.0, min(1.0,
        assertiveness * (1.0 - groundedness) * (1.0 + entropy_term) / 2.0))


def _band(fused: float, low: float, high: float) -> str:
    if fused < low:
        return "low"
    if fused < high:
        return "medium"
    return "high"


def _severity(fused: float, low: float, high: float) -> int:
    if fused < low:
        return 0
    if fused < (low + high) / 2:
        return 1
    if fused < high:
        return 2
    return 3


def run_l0(response: str, context: list[str], user_turn: str,
           policy: dict, entropy_term: float = 0.0,
           prior_turns: list[str] | None = None) -> RiskVector:
    det = policy.get("detectors", {})
    th = policy.get("thresholds", {})
    l0_low = float(th.get("l0_low", 0.20))
    l0_high = float(th.get("l0_high", 0.55))

    def cfg(name):
        return det.get(name, {}) or {}

    base = DetectionRequest(response=response, context=context,
                            user_turn=user_turn, prior_turns=prior_turns or [])

    # --- run detectors (each behind the adapter Protocol) --------------------
    g = registry.groundedness_backend(cfg("groundedness")).score(
        DetectionRequest(**{**base.__dict__, "config": cfg("groundedness")}))
    a = registry.assertiveness_backend(cfg("assertiveness")).score(base)
    p = registry.pii_backend(cfg("pii")).score(base)
    pat = registry.patterns_backend(cfg("patterns")).score(
        DetectionRequest(**{**base.__dict__, "config": cfg("patterns")}))
    inj = registry.injection_backend(cfg("injection")).score(base)

    groundedness = g.scores.get("groundedness", 1.0)
    assertiveness = a.scores.get("assertiveness", 0.0)
    ceg = _ceg(assertiveness, groundedness, entropy_term)

    # The groundedness RISK is the confidence-evidence gap, i.e. ungroundedness
    # GATED BY assertiveness. A hedged answer ("based on the documents I have,
    # ... please confirm") is not punished for a groundedness estimate the local
    # backend cannot fully confirm; only a CONFIDENT ungrounded claim is. This is
    # what keeps false positives down when the offline embedding fallback is in
    # use, and it is exactly the CEG thesis.
    ground_component = min(1.0, 2.0 * ceg)

    # weighted fusion using policy weights (default to spec section 8 values)
    w_g = float(cfg("groundedness").get("weight", 0.40))
    w_pii = float(cfg("pii").get("weight", 0.30))
    w_pat = float(cfg("patterns").get("weight", 0.20))
    w_inj = float(cfg("injection").get("weight", 0.10))
    wsum = w_g + w_pii + w_pat + w_inj or 1.0

    fused = (w_g * ground_component + w_pii * p.risk
             + w_pat * pat.risk + w_inj * inj.risk) / wsum
    # A detected prompt injection is a hard tripwire, not a weighted nudge: a
    # compromised turn should be able to flag on its own regardless of weights.
    if inj.risk >= 0.5:
        fused = max(fused, 0.85 * inj.risk)
    fused = max(0.0, min(1.0, fused))

    categories: set[str] = set()
    for r in (g, p, pat, inj):
        categories |= set(r.categories)

    pii_entities = [PIIHit(**h) for h in p.evidence.get("hits", [])]

    return RiskVector(
        groundedness=round(groundedness, 4),
        assertiveness=round(assertiveness, 4),
        ceg=round(ceg, 4),
        entropy_term=round(entropy_term, 4),
        pii_entities=pii_entities,
        pattern_hits=pat.evidence.get("rules", []),
        injection_score=round(inj.risk, 4),
        unsupported_claims=g.evidence.get("unsupported_claims", []),
        categories=categories,
        severity=_severity(fused, l0_low, l0_high),
        fused=round(fused, 4),
        backend_scores={
            "groundedness": round(g.risk, 4),
            "assertiveness": round(assertiveness, 4),
            "pii": round(p.risk, 4),
            "patterns": round(pat.risk, 4),
            "injection": round(inj.risk, 4),
        },
    )


def is_uncertain(fused: float, policy: dict) -> bool:
    th = policy.get("thresholds", {})
    return float(th.get("l0_low", 0.20)) <= fused < float(th.get("l0_high", 0.55))


def band_of(fused: float, policy: dict) -> str:
    th = policy.get("thresholds", {})
    return _band(fused, float(th.get("l0_low", 0.20)), float(th.get("l0_high", 0.55)))
