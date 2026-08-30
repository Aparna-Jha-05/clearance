"""PII backend (spec section 7).

Presidio when it installs cleanly, else spaCy NER + regex for Indian and EU
identifiers. The load-bearing rule:

    An entity present in the RESPONSE but ABSENT from the retrieved CONTEXT is
    BOTH a privacy hit AND a hallucination hit.

That single rule produces the overlap demo -- categories == {hallucination,
privacy} for a fabricated named-person detail.
"""
from __future__ import annotations

import re

from ..base import LocalBackend, DetectionRequest, DetectionResult
from ...schemas import PIIHit
from ..nlp import _try_load as _load_spacy

REGEXES = {
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\d{5}[\s-]?\d{5}|\d{3}[\s-]?\d{3}[\s-]?\d{4})\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}
_cap_name = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")
_STOP_CAPS = {"The", "This", "That", "Based", "Please", "Your", "You", "Our",
              "We", "It", "As", "If", "For", "Dear", "Hi", "Hello", "Thank",
              "Thanks", "Regards", "Best", "Kind", "Yes", "No", "Okay", "Good",
              # common capitalised org / function / doc words that are NOT names
              "People", "Ops", "Team", "Human", "Resources", "Operations",
              "Finance", "Legal", "Support", "Sales", "Company", "Policy",
              "Standard", "Guidelines", "System", "Store", "Members", "Note",
              "Returns", "Refund", "Warranty", "Damage", "Increase", "Issuing",
              "Processing", "Confirm", "Compensation", "Directory"}


def _persons(text: str) -> list[tuple[str, int, int]]:
    nlp = _load_spacy()
    out = []
    if nlp is not None:
        for ent in nlp(text).ents:
            if ent.label_ in {"PERSON"}:
                out.append((ent.text, ent.start_char, ent.end_char))
        if out:
            return out
    # fallback: multi-token capitalised phrases not starting with a stopword
    for m in _cap_name.finditer(text):
        first = m.group(1).split()[0]
        if first not in _STOP_CAPS:
            out.append((m.group(1), m.start(), m.end()))
    return out


class PIIBackend(LocalBackend):
    name = "local_pii"

    def score(self, req: DetectionRequest) -> DetectionResult:
        text = req.response or ""
        ctx = " \n ".join(req.context).lower()
        hits: list[PIIHit] = []

        for etype, rx in REGEXES.items():
            for m in rx.finditer(text):
                val = m.group(0).strip()
                if etype == "CARD" and len(re.sub(r"\D", "", val)) < 13:
                    continue
                hits.append(PIIHit(text=val, entity_type=etype,
                                   in_context=val.lower() in ctx,
                                   start=m.start(), end=m.end()))
        for val, s, e in _persons(text):
            hits.append(PIIHit(text=val, entity_type="PERSON",
                               in_context=val.lower() in ctx, start=s, end=e))

        res = DetectionResult(name=self.name)
        if not hits:
            return res

        fabricated = [h for h in hits if not h.in_context]
        # base risk from presence; big bump for fabricated (hallucinated) PII
        risk = 0.35 if hits else 0.0
        if fabricated:
            risk = min(1.0, 0.7 + 0.1 * len(fabricated))
        res.risk = risk
        res.scores = {"pii_count": len(hits), "fabricated_pii": len(fabricated)}
        res.evidence = {"hits": [h.model_dump() for h in hits]}
        res.categories = {"privacy"}
        if fabricated:
            # entity in response but not in context -> also a hallucination
            res.categories = {"privacy", "hallucination"}
        return res
