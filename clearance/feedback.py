"""Human review queue + feedback store (spec sections 4, M7).

Escalations land in the queue; a human override persists a label. Those labels
are what `scripts/train_l1.py` learns from -- closing the loop that makes the
cheap tier sharper and shrinks paid-tier traffic week over week (spec M8).
"""
from __future__ import annotations

import json
import time
import sqlite3

from .config import FEEDBACK_DB


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(FEEDBACK_DB)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS queue (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   request_id TEXT, ts REAL, use_case TEXT,
                   response   TEXT, rationale TEXT, verdict TEXT,
                   features   TEXT, status TEXT DEFAULT 'pending',
                   human_label INTEGER, reviewer TEXT, resolved_ts REAL
               )"""
        )


def enqueue(request_id: str, use_case: str, response: str, rationale: str,
            verdict: str, features: dict) -> int:
    init()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO queue (request_id, ts, use_case, response, rationale, "
            "verdict, features) VALUES (?,?,?,?,?,?,?)",
            (request_id, time.time(), use_case, response, rationale, verdict,
             json.dumps(features)),
        )
        return cur.lastrowid


def pending(limit: int = 100) -> list[dict]:
    init()
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM queue WHERE status='pending' ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()]


def resolve(item_id: int, human_label: bool, reviewer: str = "risk-owner") -> bool:
    init()
    with _conn() as c:
        r = c.execute("SELECT id FROM queue WHERE id=?", (item_id,)).fetchone()
        if not r:
            return False
        c.execute("UPDATE queue SET status='resolved', human_label=?, reviewer=?, "
                  "resolved_ts=? WHERE id=?",
                  (1 if human_label else 0, reviewer, time.time(), item_id))
    return True


def labels() -> list[dict]:
    """Resolved (features -> human_label) pairs for L1 training."""
    init()
    with _conn() as c:
        out = []
        for r in c.execute("SELECT features, human_label FROM queue "
                           "WHERE status='resolved'").fetchall():
            out.append({"features": json.loads(r["features"]),
                        "label": int(r["human_label"])})
        return out


def clear() -> None:
    with _conn() as c:
        c.execute("DROP TABLE IF EXISTS queue")
    init()
