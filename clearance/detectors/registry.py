"""Resolve a policy `backend:` name to a concrete DetectorBackend instance.

The only place backend selection happens. Swapping `backend: local` for
`backend: patronus` in a pack changes what runs here and nowhere else -- that
is the adapter seam working.
"""
from __future__ import annotations

from .backends.local_groundedness import GroundednessBackend
from .backends.local_assertiveness import AssertivenessBackend
from .backends.local_pii import PIIBackend
from .backends.local_patterns import PatternsBackend
from .backends.local_injection import InjectionBackend
from .backends.patronus_stub import PatronusGroundednessBackend

_SINGLETONS = {
    "assertiveness": AssertivenessBackend(),
}


def groundedness_backend(cfg: dict):
    backend = (cfg or {}).get("backend", "local")
    if backend == "patronus":
        return PatronusGroundednessBackend(cfg)
    return GroundednessBackend()


def assertiveness_backend(cfg: dict):
    return _SINGLETONS["assertiveness"]


def pii_backend(cfg: dict):
    return PIIBackend()


def patterns_backend(cfg: dict):
    return PatternsBackend()


def injection_backend(cfg: dict):
    return InjectionBackend()
