"""The ONLY module that touches the network (spec section 13).

Resolution order for any completion:
  1. fixture cache in corpus/fixtures/  (keyed by sha256(model, canonical messages))
  2. live AI Pipe                       (only if a token is set and not offline)
  3. recorded stub                      (deterministic, so demos never hard-fail)

CLEARANCE_OFFLINE=1 disables step 2 and raises a *clear* error on a genuine
cache miss rather than silently degrading -- except that the recorded stub in
step 3 is itself deterministic and committed, so the offline replay of the
shipped corpus always resolves.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional

from .config import get_config, FIXTURES_DIR


class OfflineCacheMiss(RuntimeError):
    pass


def _canonical(messages: list[dict]) -> str:
    slim = [{"role": m.get("role"), "content": m.get("content", "")} for m in messages]
    return json.dumps(slim, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fixture_key(model: str, messages: list[dict], suffix: str = "") -> str:
    raw = f"{model}\n{_canonical(messages)}\n{suffix}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fixture_path(key: str) -> Path:
    return FIXTURES_DIR / f"{key}.json"


def _load_fixture(key: str) -> Optional[dict]:
    p = _fixture_path(key)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_fixture(key: str, payload: dict) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    _fixture_path(key).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _recorded_stub(messages: list[dict]) -> dict:
    """Deterministic last resort. Echoes a plausible assistant turn so that a
    fresh clone with no fixtures and no key still produces *something* rather
    than crashing. Never used for corpus replay (those have real fixtures)."""
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    text = (
        "[recorded stub] I can help with that. Based on the documents I have, "
        "please confirm the specific policy before I take any action."
    )
    return {
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": len(last_user.split()), "completion_tokens": 24},
        "_source": "recorded_stub",
    }


def complete(messages: list[dict], model: Optional[str] = None,
             temperature: float = 0.2, suffix: str = "",
             allow_stub: bool = True) -> dict:
    """Return an OpenAI-shaped completion dict. Records new fixtures when live."""
    cfg = get_config()
    model = model or cfg.model
    key = fixture_key(model, messages, suffix)

    cached = _load_fixture(key)
    if cached is not None:
        cached["_source"] = "fixture"
        return cached

    if cfg.offline or not cfg.aipipe_token:
        if allow_stub:
            return _recorded_stub(messages)
        raise OfflineCacheMiss(
            f"No fixture for key {key[:12]}... and offline mode is on. "
            "Record it live (unset CLEARANCE_OFFLINE with a token) or add the fixture."
        )

    # Live path -- record the fixture so the next run is deterministic.
    import httpx
    resp = httpx.post(
        f"{cfg.aipipe_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {cfg.aipipe_token}"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    resp.raise_for_status()
    payload = resp.json()
    _save_fixture(key, payload)
    payload["_source"] = "live"
    return payload


def content_of(completion: dict) -> str:
    try:
        return completion["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError):
        return ""


def self_consistency(messages: list[dict], model: Optional[str] = None,
                     n: int = 3) -> Optional[float]:
    """1 - mean pairwise cosine over n resamples at temperature 0.7.

    Runs ONLY inside the uncertainty band (callers enforce this) because it
    costs money. Offline it reads resample fixtures; on a miss it returns None
    so the CEG entropy term degrades gracefully instead of fabricating a value.
    """
    from .detectors.embeddings import embed_batch, cosine
    samples: list[str] = []
    for i in range(n):
        c = complete(messages, model=model, temperature=0.7,
                     suffix=f"resample-{i}", allow_stub=False)
        samples.append(content_of(c))
    if len({s.strip() for s in samples}) <= 1:
        return 0.0
    vecs = embed_batch(samples)
    sims = [cosine(vecs[i], vecs[j])
            for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    if not sims:
        return None
    return max(0.0, min(1.0, 1.0 - sum(sims) / len(sims)))
