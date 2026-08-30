"""Action gate (spec section 9).

    verdict = gate[risk_band][action.reversibility]

This is the whole thesis in one line: the SAME content risk maps to different
verdicts depending on the reversibility of the action it would drive. No action
means reversibility = "reversible" -- which is exactly why a fabricated sentence
ships in a brainstorm and blocks in a refund flow.
"""
from __future__ import annotations

# gate cell -> (verdict enum, escalate?)
_NORMALISE = {
    "allow": ("allow", False),
    "allow_logged": ("allow", False),
    "annotate": ("annotate", False),
    "redact": ("redact", False),
    "hold": ("hold", False),
    "block": ("block", False),
    "escalate": ("escalate", True),
    "block_escalate": ("escalate", True),
}


def default_gate() -> dict:
    return {
        "low":    {"reversible": "allow",    "costly": "allow",  "irreversible": "allow_logged"},
        "medium": {"reversible": "annotate", "costly": "hold",   "irreversible": "hold"},
        "high":   {"reversible": "annotate", "costly": "redact", "irreversible": "block_escalate"},
    }


def resolve(band: str, reversibility: str, policy: dict) -> tuple[str, bool, str]:
    """Return (verdict, escalate, raw_cell)."""
    gate = policy.get("gate") or default_gate()
    row = gate.get(band, {})
    raw = row.get(reversibility, "allow")
    verdict, escalate = _NORMALISE.get(raw, ("allow", False))
    return verdict, escalate, raw


def reversibility_of(tool: str | None, policy: dict) -> tuple[str, int]:
    """Look up an action's reversibility + blast radius from the pack.
    No action at all -> reversible, blast radius 0."""
    if not tool:
        return "reversible", 0
    classes = policy.get("action_classes", {})
    spec = classes.get(tool)
    if not spec:
        # unknown tool: treat conservatively as costly
        return "costly", 1
    return spec.get("reversibility", "reversible"), int(spec.get("blast_radius", 0))
