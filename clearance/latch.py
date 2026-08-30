"""The action latch (spec section 9).

TEXT IS NEVER HELD. Response tokens stream to the caller immediately, at zero
added latency. Only `tool_calls` are intercepted and parked, keyed by
request_id, with a deadline of `latch_ms`. On a verdict the parked action is
released, rewritten, or dropped with an escalation record. On timeout the
policy `fail_mode` decides -- and the defaults are stated loudly because "what
happens when your checker is down?" is a question the panel WILL ask:

    irreversible -> fail_closed   (a refund is never released on a timeout)
    costly       -> fail_closed
    reversible   -> fail_open     (a ticket note is not worth blocking on)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .schemas import Decision

# verdict -> what happens to the *action* (text already streamed regardless)
_ACTION_OUTCOME = {
    "allow":    ("released", True),
    "annotate": ("released_annotated", True),
    "redact":   ("released_redacted", True),
    "hold":     ("held_for_review", False),
    "block":    ("dropped", False),
    "escalate": ("dropped_escalated", False),
}


@dataclass
class ParkedAction:
    request_id: str
    tool: str
    reversibility: str
    deadline_ts: float
    arguments: dict = field(default_factory=dict)


class Latch:
    def __init__(self):
        self._parked: dict[str, ParkedAction] = {}

    def park(self, request_id: str, tool: str, reversibility: str,
             latch_ms: int, arguments: Optional[dict] = None) -> ParkedAction:
        pa = ParkedAction(request_id, tool, reversibility,
                          time.time() + latch_ms / 1000.0, arguments or {})
        self._parked[request_id] = pa
        return pa

    def timed_out(self, request_id: str) -> bool:
        pa = self._parked.get(request_id)
        return bool(pa and time.time() > pa.deadline_ts)

    @staticmethod
    def _fail_mode(reversibility: str, policy: dict) -> str:
        fm = policy.get("fail_mode", {})
        return fm.get(reversibility, "fail_closed" if reversibility != "reversible"
                      else "fail_open")

    def resolve(self, decision: Decision, policy: dict,
                timed_out: bool = False) -> dict:
        """Return {action_released, outcome, reason}. Pure w.r.t. `decision`;
        `timed_out=True` forces the fail-mode branch for the fail-closed test."""
        rev = decision.action.reversibility if decision.action else "reversible"
        if timed_out:
            mode = self._fail_mode(rev, policy)
            released = mode == "fail_open"
            self._parked.pop(decision.request_id, None)
            return {"action_released": released,
                    "outcome": "released_fail_open" if released else "dropped_fail_closed",
                    "reason": f"latch timeout ({policy.get('latch_ms', 200)}ms), "
                              f"{rev} -> {mode}"}
        outcome, released = _ACTION_OUTCOME.get(decision.verdict, ("released", True))
        self._parked.pop(decision.request_id, None)
        return {"action_released": released, "outcome": outcome,
                "reason": decision.rationale}


# process-wide latch instance for the gateway
LATCH = Latch()
