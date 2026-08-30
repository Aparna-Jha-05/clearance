"""Sentence splitting + light NER with graceful fallback.

spaCy `en_core_web_sm` when installed (spec section 7); otherwise a regex
sentencizer and regex/lexicon NER. Deterministic either way.
"""
from __future__ import annotations

import re

_NLP = None
_TRIED = False

_ABBR = {"mr", "mrs", "ms", "dr", "inc", "ltd", "e.g", "i.e", "vs", "rs", "no"}
_sent_split = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_word = re.compile(r"\b\w+\b")


def _try_load():
    global _NLP, _TRIED
    if _TRIED:
        return _NLP
    _TRIED = True
    try:
        import spacy
        _NLP = spacy.load("en_core_web_sm")
    except Exception:
        _NLP = None
    return _NLP


def nlp_backend() -> str:
    return "spacy:en_core_web_sm" if _try_load() is not None else "regex-fallback"


def sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    nlp = _try_load()
    if nlp is not None:
        return [s.text.strip() for s in nlp(text).sents if s.text.strip()]
    # regex fallback
    parts = _sent_split.split(text)
    return [p.strip() for p in parts if p.strip()]


def has_content(sentence: str) -> bool:
    """Drop sentences with no verb/content word (spec section 7)."""
    words = _word.findall(sentence.lower())
    if len(words) < 3:
        return False
    # crude: at least one token that isn't a stopword-ish function word
    stop = {"the", "a", "an", "of", "to", "and", "or", "is", "are", "please",
            "thanks", "hi", "hello", "ok", "okay", "yes", "no", "so"}
    return any(w not in stop for w in words)


def claim_sentences(text: str) -> list[str]:
    return [s for s in sentences(text) if has_content(s)]
