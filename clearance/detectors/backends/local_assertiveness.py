"""Assertiveness backend (spec section 7).

Lexicon scorer, no model, editable. Positive signals: absolute quantifiers,
policy-voice, bare numerals / currency / dates. Negative signals: hedges.
Normalised to 0..1. Feeds the confidence-evidence gap; it is deliberately
cheap and transparent so a risk owner can read and edit it.
"""
from __future__ import annotations

import re

from ..base import LocalBackend, DetectionRequest, DetectionResult

ABSOLUTES = ["always", "never", "guaranteed", "guarantee", "definitely",
             "certainly", "without exception", "in all cases", "must", "will",
             "entitled", "approved", "immediately"]
POLICY_VOICE = ["the policy is", "you are entitled", "we will refund",
                "you are approved", "our policy", "you qualify", "eligible for",
                "we guarantee", "you can claim", "you are covered"]
HEDGES = ["may", "might", "typically", "usually", "please confirm",
          "based on the documents", "i believe", "it seems", "possibly",
          "i'm not sure", "cannot confirm", "you may want to", "generally"]

_currency = re.compile(r"[\$£€₹]\s?\d|(?:\brs\.?\s?\d)|\b\d+\s?(?:usd|eur|inr|gbp)\b", re.I)
_numeral = re.compile(r"\b\d+(?:\.\d+)?\b")
_date = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
                   r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d)", re.I)
_percent = re.compile(r"\b\d+\s?%")


def _count(text: str, phrases: list[str]) -> int:
    t = text.lower()
    return sum(t.count(p) for p in phrases)


class AssertivenessBackend(LocalBackend):
    name = "local_assertiveness"

    def score(self, req: DetectionRequest) -> DetectionResult:
        text = req.response or ""
        pos = _count(text, ABSOLUTES) + 1.6 * _count(text, POLICY_VOICE)
        pos += 1.0 * (len(_currency.findall(text)) + len(_percent.findall(text)))
        pos += 0.5 * min(len(_numeral.findall(text)), 4)
        pos += 0.6 * len(_date.findall(text))
        neg = _count(text, HEDGES)

        # squashing: hedges pull the score down, commitments push it up
        raw = pos - 1.3 * neg
        # logistic-ish normalise into 0..1
        score = 1.0 / (1.0 + pow(2.71828, -0.9 * (raw - 1.2)))
        score = max(0.0, min(1.0, score))
        return DetectionResult(
            name=self.name, risk=score,
            scores={"assertiveness": score, "pos": pos, "neg": neg},
        )
