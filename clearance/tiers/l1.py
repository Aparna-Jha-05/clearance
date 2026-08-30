"""Layer 1 distilled judge (spec sections 4, 17).

Honest scope: L1 is a *calibrated classifier over L0 feature vectors*, not a
distilled language model. The learning loop is real (L2/human labels retrain
it, spec M8); the tier is simplified. It only runs for the ~8% of traffic that
lands in L0's uncertainty band, and it nudges the fused score toward the
calibrated probability of true risk so the cheap tier gets sharper over time.
"""
from __future__ import annotations

import json
import math
from ..config import L1_MODEL
from ..schemas import RiskVector

FEATURES = ["groundedness", "assertiveness", "ceg", "injection_score",
            "pii", "patterns", "fused"]


def featurize(rv: RiskVector) -> list[float]:
    bs = rv.backend_scores
    return [
        1.0 - rv.groundedness,
        rv.assertiveness,
        rv.ceg,
        rv.injection_score,
        bs.get("pii", 0.0),
        bs.get("patterns", 0.0),
        rv.fused,
    ]


class L1Model:
    """Thin logistic model. Loads trained weights if present, else identity."""

    def __init__(self):
        self.weights = None
        self.bias = 0.0
        self.trained = False
        self._load()

    def _load(self):
        if L1_MODEL.exists():
            data = json.loads(L1_MODEL.read_text(encoding="utf-8"))
            self.weights = data.get("weights")
            self.bias = data.get("bias", 0.0)
            self.trained = bool(self.weights)

    def predict_proba(self, rv: RiskVector) -> float:
        x = featurize(rv)
        if not self.trained or not self.weights:
            # untrained: fall back to L0 fused score (no learning yet)
            return rv.fused
        z = self.bias + sum(w * xi for w, xi in zip(self.weights, x))
        return 1.0 / (1.0 + math.exp(-z))


_MODEL: L1Model | None = None


def get_model() -> L1Model:
    global _MODEL
    if _MODEL is None:
        _MODEL = L1Model()
    return _MODEL


def reload_model() -> None:
    global _MODEL
    _MODEL = L1Model()


def resolve(rv: RiskVector, policy: dict) -> tuple[float, bool]:
    """Return (adjusted_fused, blocked_by_l1). Called only in the L0 band."""
    proba = get_model().predict_proba(rv)
    th = policy.get("thresholds", {})
    block_above = float(th.get("l1_block_above", 0.72))
    # L1 replaces the fused score with its calibrated estimate inside the band
    return proba, proba >= block_above
