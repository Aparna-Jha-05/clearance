"""Patronus adapter STUB -- proves the seam, requires no key to read (spec 1).

This file exists to defuse "why not just use Lakera / Patronus?" in one glance:
a named commercial detector is a drop-in `DetectorBackend`. CLEARANCE's tiers,
policy engine and gate never change; only the backend behind the groundedness
(or PII, or injection) slot does.

It is config-only. With `PATRONUS_API_KEY` set and `enabled: true` in the pack,
`score()` would POST to Patronus's Lynx/judge endpoint and map the response
into a `DetectionResult`. Offline and keyless, it raises a clear, honest error
rather than pretending to score -- so the repo never *looks* like it is calling
a vendor it is not.

    detectors:
      groundedness: { backend: patronus, enabled: true }   # <- one line swap
"""
from __future__ import annotations

import os

from ..base import LocalBackend, DetectionRequest, DetectionResult


class PatronusGroundednessBackend(LocalBackend):
    """Type-checks as a DetectorBackend. Network path is illustrative only."""
    name = "patronus_groundedness"
    endpoint = "https://api.patronus.ai/v1/evaluate"
    evaluator = "lynx-groundedness"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.api_key = os.getenv("PATRONUS_API_KEY", "")

    def available(self) -> bool:
        return bool(self.api_key)

    def score(self, req: DetectionRequest) -> DetectionResult:
        if not self.api_key:
            raise RuntimeError(
                "PatronusGroundednessBackend selected but PATRONUS_API_KEY is unset. "
                "This is a seam-proving stub: set the key and enable it in the policy "
                "pack to route groundedness to Patronus, or keep backend: local."
            )
        # --- illustrative live mapping (not executed offline) -------------------
        import httpx
        payload = {
            "evaluators": [{"evaluator": self.evaluator}],
            "evaluated_model_output": req.response,
            "evaluated_model_retrieved_context": req.context,
            "evaluated_model_input": req.user_turn,
        }
        resp = httpx.post(
            self.endpoint,
            headers={"x-api-key": self.api_key, "content-type": "application/json"},
            json=payload, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Patronus returns pass/fail + score in [0,1]; map to our risk convention.
        score = float(data["results"][0].get("score", 0.0))
        return DetectionResult(
            name=self.name,
            risk=1.0 - score,                         # groundedness -> ungroundedness risk
            scores={"groundedness": score, "provider": "patronus"},
            categories={"hallucination"} if score < 0.5 else set(),
            evidence={"raw": data},
        )
