"""The adapter seam (spec section 1).

Every detector -- ours or a vendor's -- implements `DetectorBackend`. Ship thin
local defaults so the repo runs offline with zero keys, but keep the interface
wide enough that Lakera, Presidio, Bedrock Guardrails or Patronus drop in as a
backend without touching the tiers, policy engine, or gate.

`patronus_stub.py` implements exactly this Protocol (config-only, no key) to
prove the seam is real and not a slide.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from dataclasses import dataclass, field


@dataclass
class DetectionRequest:
    response: str                       # model output under inspection
    context: list[str] = field(default_factory=list)   # retrieved chunks
    user_turn: str = ""                 # last user message
    prior_turns: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)          # per-detector policy block


@dataclass
class DetectionResult:
    name: str
    risk: float = 0.0                   # 0..1 normalised risk contribution
    scores: dict = field(default_factory=dict)          # named sub-scores
    categories: set = field(default_factory=set)        # OVERLAPPING labels
    evidence: dict = field(default_factory=dict)        # spans/claims for rationale


@runtime_checkable
class DetectorBackend(Protocol):
    name: str

    def score(self, req: DetectionRequest) -> DetectionResult:
        ...


class LocalBackend:
    """Base for shipped local detectors. Sync `score`; the tier layer awaits
    an executor so a future async vendor backend fits the same call site."""
    name = "local"

    def score(self, req: DetectionRequest) -> DetectionResult:  # pragma: no cover
        raise NotImplementedError
