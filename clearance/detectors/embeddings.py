"""Sentence embeddings with a deterministic offline fallback.

Preferred: sentence-transformers `all-MiniLM-L6-v2` (spec section 7).
Fallback: a hashed word-bigram bag-of-words vector, L2-normalised. It is not
semantic, but it is deterministic, dependency-free, and gives sane lexical
overlap for groundedness -- so the repo runs on a fresh clone with no model
downloads. Which path is active is reported by `backend_name()` and surfaced
in the docs, never hidden.
"""
from __future__ import annotations

import re
import math
import hashlib
from functools import lru_cache

import numpy as np

_DIM = 384
_MODEL = None
_TRIED = False


def _try_load_model():
    global _MODEL, _TRIED
    if _TRIED:
        return _MODEL
    _TRIED = True
    try:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _MODEL = None
    return _MODEL


def backend_name() -> str:
    return "all-MiniLM-L6-v2" if _try_load_model() is not None else "hashed-bow-fallback"


_word = re.compile(r"[a-z0-9]+")


def _hash_embed(text: str) -> np.ndarray:
    toks = _word.findall(text.lower())
    vec = np.zeros(_DIM, dtype=np.float32)
    grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    for g in grams:
        h = int(hashlib.md5(g.encode()).hexdigest(), 16)
        idx = h % _DIM
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec


def embed_batch(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, _DIM), dtype=np.float32)
    model = _try_load_model()
    if model is not None:
        embs = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return np.asarray(embs, dtype=np.float32)
    return np.vstack([_hash_embed(t) for t in texts])


@lru_cache(maxsize=2048)
def embed_one(text: str) -> tuple:
    return tuple(embed_batch([text])[0].tolist())


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
