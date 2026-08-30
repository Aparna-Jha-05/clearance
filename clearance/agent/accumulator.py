"""Conversation-level risk carry-forward (spec section 10).

The whole thesis, most defensible here. A per-response checker evaluates turn 6
in isolation and sees a well-grounded, low-risk message -- because it is
grounded in the CONVERSATION. Clearance carries forward that an earlier premise
(the turn-3 refund-eligibility window) was never EXTERNALLY supported, so when
turn 6 tries to act on it with an irreversible tool call, the gate bands on
`combine(this_turn_risk, accumulated_risk)` and blocks.

The accumulator does NOT do causal tracing of which earlier claim contaminated
which later decision (documented as a limitation). It carries a decaying scalar.
"""
from __future__ import annotations

from ..schemas import RiskVector

# in-memory per-conversation state: cid -> accumulated risk AFTER its last turn
_STATE: dict[str, float] = {}


def reset(conversation_id: str | None = None) -> None:
    if conversation_id is None:
        _STATE.clear()
    else:
        _STATE.pop(conversation_id, None)


def peek(conversation_id: str) -> float:
    return _STATE.get(conversation_id, 0.0)


def _contribution(rv: RiskVector) -> float:
    """How much this turn adds to the carried premise-risk.

    Driven by UNGROUNDEDNESS (a claim asserted but not externally supported),
    scaled by how strongly it was asserted. A grounded, hedged turn contributes
    almost nothing; an ungrounded, confident entitlement claim contributes a lot.
    """
    ungrounded = 1.0 - rv.groundedness
    # a grounded or purely-hedged turn barely accumulates; an ungrounded claim
    # accumulates more the more confidently it was asserted
    return max(rv.ceg, ungrounded * (0.3 + 0.7 * rv.assertiveness))


def carry_in(conversation_id: str, policy: dict) -> float:
    """Risk carried INTO the current turn (prior state decayed once)."""
    decay = float(policy.get("conversation", {}).get("accumulator_decay", 0.85))
    return round(decay * _STATE.get(conversation_id, 0.0), 4)


def combine(this_turn_fused: float, accumulated: float) -> float:
    """Probabilistic OR: either the turn itself OR the carried premise can raise
    the band. This is what lets a low-this-turn action inherit prior risk."""
    return round(1.0 - (1.0 - this_turn_fused) * (1.0 - accumulated), 4)


def commit(conversation_id: str, accumulated_in: float, rv: RiskVector) -> float:
    """Fold this turn's contribution into the stored state; return new stored."""
    new = min(1.0, accumulated_in + _contribution(rv))
    _STATE[conversation_id] = round(new, 4)
    return _STATE[conversation_id]


def should_force_escalate(accumulated_in: float, policy: dict) -> bool:
    thr = float(policy.get("conversation", {}).get("escalate_accumulated_above", 0.65))
    return accumulated_in >= thr
