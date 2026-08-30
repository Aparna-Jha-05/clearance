"""Groundedness backend (spec section 7).

Split the response into claim-bearing sentences, embed them and the context
chunks, and take per-claim max cosine against context. coverage = fraction of
claims whose best match clears tau (from policy). Unsupported claims are
returned verbatim -- they become the human-readable rationale.
"""
from __future__ import annotations

from ..base import LocalBackend, DetectionRequest, DetectionResult
from ..embeddings import embed_batch, cosine
from ..nlp import claim_sentences


class GroundednessBackend(LocalBackend):
    name = "local_groundedness"

    def score(self, req: DetectionRequest) -> DetectionResult:
        tau = float(req.config.get("tau", 0.55))
        claims = claim_sentences(req.response)
        res = DetectionResult(name=self.name)
        if not claims:
            res.scores = {"groundedness": 1.0, "coverage": 1.0, "n_claims": 0}
            return res
        if not req.context:
            # No retrieval to check against: cannot support any claim.
            res.risk = 1.0
            res.scores = {"groundedness": 0.0, "coverage": 0.0, "n_claims": len(claims)}
            res.evidence = {"unsupported_claims": claims}
            res.categories = {"hallucination"}
            return res

        ctx_vecs = embed_batch(req.context)
        claim_vecs = embed_batch(claims)
        unsupported, supported = [], 0
        for claim, cv in zip(claims, claim_vecs):
            best = max(cosine(cv, xv) for xv in ctx_vecs)
            if best >= tau:
                supported += 1
            else:
                unsupported.append(claim)

        coverage = supported / len(claims)
        res.risk = 1.0 - coverage
        res.scores = {"groundedness": coverage, "coverage": coverage,
                      "n_claims": len(claims), "tau": tau}
        if unsupported:
            res.evidence = {"unsupported_claims": unsupported}
            res.categories = {"hallucination"}
        return res
