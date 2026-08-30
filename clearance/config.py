"""Runtime configuration and canonical filesystem paths.

Everything is resolved relative to the repo root so the code runs identically
from VS Code, a packaged run, or a judge's fresh clone.
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv is optional; env vars still work without it
    pass

# --- paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
FIXTURES_DIR = CORPUS_DIR / "fixtures"
POLICIES_DIR = ROOT / "policies"
DATA_DIR = ROOT / "data"          # runtime state (ledger db, feedback, models)
DATA_DIR.mkdir(exist_ok=True)

LEDGER_DB = DATA_DIR / "ledger.sqlite"
FEEDBACK_DB = DATA_DIR / "feedback.sqlite"
L1_MODEL = DATA_DIR / "l1_model.json"


def _flag(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Process-wide settings. Read once, cheap to reference everywhere."""

    aipipe_base_url: str = os.getenv("AIPIPE_BASE_URL", "https://aipipe.org/openai/v1")
    aipipe_token: str = os.getenv("AIPIPE_TOKEN", "")
    model: str = os.getenv("CLEARANCE_MODEL", "gpt-4o-mini")

    # Offline is the default posture. A judge must never need a key.
    offline: bool = _flag("CLEARANCE_OFFLINE", True)

    # Default policy pack the gateway uses when a request names none.
    default_policy: str = os.getenv("CLEARANCE_POLICY", "support-assistant.eu")


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()
