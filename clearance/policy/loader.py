"""Load policy packs and compute their governance hash (spec sections 8, 12).

`policy_hash` is the SHA-256 of the canonicalised pack and is written into
every ledger row, so an auditor can prove exactly which rules decided a case.
Editing any byte of the pack -- a threshold, the operating-point signer -- gives
a new hash and a new, attributable operating point.
"""
from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from pathlib import Path

import yaml

from ..config import POLICIES_DIR


def canonical(pack: dict) -> str:
    return json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def policy_hash(pack: dict) -> str:
    return hashlib.sha256(canonical(pack).encode("utf-8")).hexdigest()


def _path_for(name: str) -> Path:
    # accept "support-assistant.eu" or "support-assistant.eu.yaml"
    if not name.endswith(".yaml"):
        name = name + ".yaml"
    return POLICIES_DIR / name


@lru_cache(maxsize=32)
def load(name: str) -> tuple:
    """Return (pack_dict, policy_hash). Cached; call `clear_cache()` after edits."""
    p = _path_for(name)
    if not p.exists():
        raise FileNotFoundError(f"policy pack not found: {p}")
    pack = yaml.safe_load(p.read_text(encoding="utf-8"))
    return pack, policy_hash(pack)


def load_pack(name: str) -> dict:
    return load(name)[0]


def hash_of(name: str) -> str:
    return load(name)[1]


def list_packs() -> list[str]:
    return sorted(p.stem for p in POLICIES_DIR.glob("*.yaml"))


def clear_cache() -> None:
    load.cache_clear()


def with_overrides(pack: dict, overrides: dict) -> dict:
    """Return a deep-ish copy of `pack` with threshold/tau overrides applied.

    Used by the tuning console to score alternative operating points without
    writing to disk. Recognised override keys: l0_low, l0_high, l1_block_above,
    tau, and per-detector weights (weight_groundedness, ...).
    """
    import copy
    p = copy.deepcopy(pack)
    th = p.setdefault("thresholds", {})
    for k in ("l0_low", "l0_high", "l1_block_above"):
        if k in overrides and overrides[k] is not None:
            th[k] = float(overrides[k])
    det = p.setdefault("detectors", {})
    if overrides.get("tau") is not None:
        det.setdefault("groundedness", {})["tau"] = float(overrides["tau"])
    for name in ("groundedness", "pii", "patterns", "injection"):
        key = f"weight_{name}"
        if overrides.get(key) is not None:
            det.setdefault(name, {})["weight"] = float(overrides[key])
    return p
