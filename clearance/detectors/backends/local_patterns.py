"""Pattern backend (spec section 7).

Compiled regex rules drawn from the policy pack: refund commitments, price
guarantees, approval language, dosage language. Which rules are active is
controlled per-pack via `detectors.patterns.rules`.
"""
from __future__ import annotations

import re

from ..base import LocalBackend, DetectionRequest, DetectionResult

RULES = {
    "refund_commitment": re.compile(
        r"\b(we (?:will|'ll) (?:refund|reimburse|credit)|"
        r"you (?:are|'re) entitled to a (?:full )?refund|"
        r"issue(?:d|ing)? (?:a|the|your) (?:full )?refund|"
        r"refund (?:will be|has been) (?:processed|approved)|"
        r"bereavement refund|(?:full|complete) refund)\b", re.I),
    "price_guarantee": re.compile(
        r"\b(price match|lowest price guaranteed|we guarantee the price|"
        r"guaranteed (?:lowest|best) price)\b", re.I),
    "approval_language": re.compile(
        r"\b(you (?:are|'re) approved|your (?:loan|claim|application) is approved|"
        r"pre-approved|approved for)\b", re.I),
    "dosage_language": re.compile(
        r"\b(take \d+\s?(?:mg|ml|tablets?|pills?)|increase your dose|"
        r"\d+\s?mg (?:twice|once|three times) (?:a|per) day)\b", re.I),
    "medical_advice": re.compile(
        r"\b(you should stop taking|safe to (?:take|combine)|diagnos(?:e|is)|"
        r"you (?:have|are experiencing) (?:a|an) )\b", re.I),
    "legal_commitment": re.compile(
        r"\b(you have a (?:strong )?case|you will win|legally entitled|"
        r"we can (?:guarantee|assure) (?:the )?outcome)\b", re.I),
}


class PatternsBackend(LocalBackend):
    name = "local_patterns"

    def score(self, req: DetectionRequest) -> DetectionResult:
        text = req.response or ""
        active = req.config.get("rules") or list(RULES.keys())
        hits = []
        for rule in active:
            rx = RULES.get(rule)
            if rx and rx.search(text):
                hits.append(rule)
        res = DetectionResult(name=self.name)
        if hits:
            res.risk = min(1.0, 0.8 + 0.15 * (len(hits) - 1))
            res.scores = {"pattern_hits": len(hits)}
            res.evidence = {"rules": hits}
            res.categories = {"policy_violation"}
        return res
