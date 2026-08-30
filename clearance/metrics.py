"""Operating-point metrics over the labelled corpus (spec sections 11, 12).

Two-phase by design so the tuning console stays under 300ms:

  precompute_features()  runs the expensive, threshold-INDEPENDENT work once
                         (embeddings, per-claim cosines, lexicon scores).
  recompute()            sweeps any operating point with pure arithmetic over
                         the cached features -- no model calls, no embeddings.

Changing `tau` only re-thresholds cached cosines; changing weights or l0_* only
re-fuses cached sub-scores. That is what makes the slider feel instant.
"""
from __future__ import annotations

import time
from functools import lru_cache

from .config import CORPUS_DIR
from .schemas import CorpusRecord
from .detectors.backends.local_groundedness import claim_sentences
from .detectors.embeddings import embed_batch, cosine
from .detectors.backends.local_assertiveness import AssertivenessBackend
from .detectors.backends.local_pii import PIIBackend
from .detectors.backends.local_patterns import PatternsBackend
from .detectors.backends.local_injection import InjectionBackend
from .detectors.base import DetectionRequest
from .policy import loader

# assumed weekly request volume + review economics for the console read-outs
WEEKLY_VOLUME = 50_000
MINUTES_PER_REVIEW = 4
COST_L1_PER = 0.00002
COST_L2_PER = 0.0018

_ASSERT = AssertivenessBackend()
_PII = PIIBackend()
_PAT = PatternsBackend()
_INJ = InjectionBackend()


def _records(use_case: str | None = None) -> list[CorpusRecord]:
    import json
    out = []
    for f in sorted(CORPUS_DIR.glob("*.jsonl")):
        if f.name == "agentic.jsonl":
            continue  # multi-turn, scored by the replay not the single-shot metrics
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = CorpusRecord(**json.loads(line))
            if use_case and rec.use_case != use_case:
                continue
            out.append(rec)
    return out


@lru_cache(maxsize=8)
def precompute_features(use_case: str | None = None) -> tuple:
    """Return an immutable tuple of per-record feature dicts (cached)."""
    rows = []
    for rec in _records(use_case):
        if not rec.response or rec.gold is None:
            continue
        t = time.perf_counter()
        claims = claim_sentences(rec.response)
        if claims and rec.retrieved:
            cvs = embed_batch(rec.retrieved)
            qvs = embed_batch(claims)
            max_cos = [max(cosine(q, c) for c in cvs) for q in qvs]
        elif claims and not rec.retrieved:
            max_cos = [0.0] * len(claims)
        else:
            max_cos = []
        base = DetectionRequest(response=rec.response, context=rec.retrieved,
                                user_turn=rec.turns[-1]["content"] if rec.turns else "")
        assertiveness = _ASSERT.score(base).scores.get("assertiveness", 0.0)
        pii = _PII.score(base)
        pat = _PAT.score(base)
        inj = _INJ.score(base)
        measured_ms = (time.perf_counter() - t) * 1000
        rows.append({
            "id": rec.id, "use_case": rec.use_case,
            "max_cos": max_cos, "n_claims": len(claims),
            "assertiveness": assertiveness,
            "pii_risk": pii.risk, "pii_categories": list(pii.categories),
            "pattern_risk": pat.risk, "injection": inj.risk,
            "entropy": rec.self_consistency or 0.0,
            "gold_risky": rec.gold.risky,
            "gold_categories": rec.gold.categories,
            "action_tool": (rec.action_requested or {}).get("tool"),
            "measured_ms": measured_ms,
        })
    return tuple(rows)


def _fuse(fr: dict, tau: float, w: dict) -> float:
    if fr["n_claims"]:
        coverage = sum(1 for c in fr["max_cos"] if c >= tau) / fr["n_claims"]
    else:
        coverage = 1.0
    groundedness = coverage
    ceg = fr["assertiveness"] * (1 - groundedness) * (1 + fr["entropy"]) / 2
    ground_component = min(1.0, 2 * ceg)   # ungroundedness gated by assertiveness (CEG)
    wsum = sum(w.values()) or 1.0
    fused = (w["groundedness"] * ground_component + w["pii"] * fr["pii_risk"]
             + w["patterns"] * fr["pattern_risk"] + w["injection"] * fr["injection"]) / wsum
    if fr["injection"] >= 0.5:
        fused = max(fused, 0.85 * fr["injection"])
    return max(0.0, min(1.0, fused))


def recompute(use_case: str, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    pack, _ = loader.load(_pack_name(use_case))
    det = pack.get("detectors", {})
    th = pack.get("thresholds", {})
    tau = float(overrides.get("tau", det.get("groundedness", {}).get("tau", 0.55)))
    l0_low = float(overrides.get("l0_low", th.get("l0_low", 0.20)))
    l0_high = float(overrides.get("l0_high", th.get("l0_high", 0.55)))
    w = {
        "groundedness": float(overrides.get("weight_groundedness",
                              det.get("groundedness", {}).get("weight", 0.40))),
        "pii": float(overrides.get("weight_pii", det.get("pii", {}).get("weight", 0.30))),
        "patterns": float(overrides.get("weight_patterns",
                          det.get("patterns", {}).get("weight", 0.20))),
        "injection": float(overrides.get("weight_injection",
                           det.get("injection", {}).get("weight", 0.10))),
    }
    feats = precompute_features(use_case)
    tp = fp = fn = tn = 0
    uncertain = escal = 0
    fused_scores = []
    for fr in feats:
        fused = _fuse(fr, tau, w)
        fused_scores.append((fused, fr["gold_risky"]))
        flagged = fused >= l0_low
        band_high = fused >= l0_high
        if l0_low <= fused < l0_high:
            uncertain += 1
        rev = _reversibility(fr["action_tool"], pack)
        if band_high and rev == "irreversible":
            escal += 1
        if fr["gold_risky"] and flagged:
            tp += 1
        elif (not fr["gold_risky"]) and flagged:
            fp += 1
        elif fr["gold_risky"] and not flagged:
            fn += 1
        else:
            tn += 1

    n = max(1, tp + fp + fn + tn)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f2 = (5 * precision * recall / (4 * precision + recall)) if (precision + recall) else 0.0
    fp_rate = fp / (fp + tn) if (fp + tn) else 0.0
    fn_rate = fn / (fn + tp) if (fn + tp) else 0.0
    escalations_per_1000 = escal / n * 1000
    reviewer_hours = (escalations_per_1000 / 1000) * WEEKLY_VOLUME * MINUTES_PER_REVIEW / 60
    cost_per_1000 = (uncertain / n) * COST_L1_PER * 1000 + (escal / n) * COST_L2_PER * 1000
    p95_latency = _p95([fr["measured_ms"] for fr in feats])

    return {
        "use_case": use_case, "n": n,
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f2": round(f2, 4), "fp_rate": round(fp_rate, 4), "fn_rate": round(fn_rate, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "escalations_per_1000": round(escalations_per_1000, 2),
        "reviewer_hours_per_week": round(reviewer_hours, 1),
        "cost_per_1000_usd": round(cost_per_1000, 5),
        "added_p95_latency_ms": round(p95_latency, 3),
        "uncertain_fraction": round(uncertain / n, 4),
        "operating_point": {"tau": tau, "l0_low": l0_low, "l0_high": l0_high, **w},
        "pr_curve": _pr_curve(fused_scores),
        "current_point": _point_at(fused_scores, l0_low),
    }


def _pr_curve(scores: list[tuple]) -> list[dict]:
    pts = []
    for i in range(0, 101, 4):
        t = i / 100
        pts.append({"t": round(t, 2), **_point_at(scores, t)})
    return pts


def _point_at(scores: list[tuple], t: float) -> dict:
    tp = sum(1 for s, g in scores if g and s >= t)
    fp = sum(1 for s, g in scores if (not g) and s >= t)
    fn = sum(1 for s, g in scores if g and s < t)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4)}


def _p95(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, int(round(0.95 * (len(s) - 1))))
    return s[k]


def _pack_name(use_case: str) -> str:
    return {
        "support-assistant": "support-assistant.eu",
        "internal-copilot": "internal-copilot.in",
        "decision-support": "decision-support.eu",
    }.get(use_case, "support-assistant.eu")


def _reversibility(tool: str | None, pack: dict) -> str:
    if not tool:
        return "reversible"
    return pack.get("action_classes", {}).get(tool, {}).get("reversibility", "costly")


def clear_cache():
    precompute_features.cache_clear()
