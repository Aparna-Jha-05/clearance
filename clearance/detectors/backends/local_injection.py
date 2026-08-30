"""Prompt-injection backend (spec section 7).

Scans the user turn AND the retrieved documents. Retrieved-document injection
matters because loosely governed internal sources are named in the brief -- an
attacker who can seed an internal wiki page can smuggle instructions into
context. Lexicon + regex, deterministic.
"""
from __future__ import annotations

import re

from ..base import LocalBackend, DetectionRequest, DetectionResult

SIGNALS = [
    r"ignore (?:all |the |your )?(?:previous|prior|above) instructions",
    r"disregard (?:all |the )?(?:previous|prior|earlier) (?:instructions|rules)",
    r"you are now (?:a|an|in) ",
    r"system prompt",
    r"reveal (?:your |the )?(?:system )?prompt",
    r"developer mode",
    r"do anything now|\bDAN\b",
    r"pretend (?:you are|to be)",
    r"new instructions:",
    r"override (?:the |your )?(?:policy|guardrail|safety)",
    r"forget (?:everything|all previous)",
    r"print (?:your|the) instructions",
    r"act as if",
]
_RX = [re.compile(s, re.I) for s in SIGNALS]


def _scan(text: str) -> list[str]:
    return [rx.pattern for rx in _RX if rx.search(text or "")]


class InjectionBackend(LocalBackend):
    name = "local_injection"

    def score(self, req: DetectionRequest) -> DetectionResult:
        user_hits = _scan(req.user_turn)
        doc_hits = []
        for chunk in req.context:
            doc_hits.extend(_scan(chunk))

        res = DetectionResult(name=self.name)
        total = len(user_hits) + len(doc_hits)
        if total:
            # document-borne injection is weighted higher: it is stealthier
            score = min(1.0, 0.5 * len(user_hits) + 0.7 * len(doc_hits))
            res.risk = max(res.risk, min(1.0, 0.45 + 0.25 * total))
            res.scores = {"injection_score": res.risk,
                          "user_hits": len(user_hits), "doc_hits": len(doc_hits)}
            res.evidence = {"user_signals": user_hits, "doc_signals": doc_hits}
            res.categories = {"prompt_injection"}
            if doc_hits:
                res.evidence["source"] = "retrieved_document"
        return res
