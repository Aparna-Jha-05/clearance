"""Append-only, hash-chained decision ledger (spec sections 4 and 12.3).

Each row commits to the previous row's hash, so any tampering downstream
breaks the chain. `verify_chain()` walks it and reports the first break.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from typing import Optional, Iterable

from .config import LEDGER_DB
from .schemas import Decision

GENESIS = "0" * 64


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(LEDGER_DB)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS ledger (
                   seq        INTEGER PRIMARY KEY AUTOINCREMENT,
                   request_id TEXT,
                   ts         REAL,
                   prev_hash  TEXT,
                   row_hash   TEXT,
                   payload    TEXT
               )"""
        )


def _row_digest(prev_hash: str, payload_json: str) -> str:
    return hashlib.sha256(f"{prev_hash}\n{payload_json}".encode("utf-8")).hexdigest()


def _last_hash(c: sqlite3.Connection) -> str:
    row = c.execute("SELECT row_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
    return row["row_hash"] if row else GENESIS


def append(decision: Decision, ts: Optional[float] = None) -> str:
    import time
    ts = ts if ts is not None else time.time()
    payload = decision.model_dump(mode="json")
    # canonical JSON so the hash is reproducible across machines
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), default=list)
    with _conn() as c:
        init_needed = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ledger'"
        ).fetchone()
        if not init_needed:
            init()
        prev = _last_hash(c)
        row_hash = _row_digest(prev, payload_json + f"|{ts}")
        c.execute(
            "INSERT INTO ledger (request_id, ts, prev_hash, row_hash, payload) "
            "VALUES (?,?,?,?,?)",
            (decision.request_id, ts, prev, row_hash, payload_json),
        )
    return row_hash


def rows(limit: int = 500, use_case: Optional[str] = None,
         verdict: Optional[str] = None) -> list[dict]:
    q = "SELECT * FROM ledger"
    where, args = [], []
    if use_case:
        where.append("payload LIKE ?"); args.append(f'%"use_case":"{use_case}"%')
    if verdict:
        where.append("payload LIKE ?"); args.append(f'%"verdict":"{verdict}"%')
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY seq DESC LIMIT ?"; args.append(limit)
    with _conn() as c:
        out = []
        for r in c.execute(q, args).fetchall():
            d = dict(r)
            d["decision"] = json.loads(d.pop("payload"))
            out.append(d)
        return out


def verify_chain() -> dict:
    """Walk the whole chain. Returns {ok, length, broken_at}."""
    with _conn() as c:
        init()
        prev = GENESIS
        seqs = c.execute(
            "SELECT seq, ts, prev_hash, row_hash, payload FROM ledger ORDER BY seq ASC"
        ).fetchall()
        for r in seqs:
            if r["prev_hash"] != prev:
                return {"ok": False, "length": len(seqs), "broken_at": r["seq"],
                        "reason": "prev_hash mismatch"}
            expect = _row_digest(r["prev_hash"], r["payload"] + f'|{r["ts"]}')
            if expect != r["row_hash"]:
                return {"ok": False, "length": len(seqs), "broken_at": r["seq"],
                        "reason": "row_hash mismatch (row was mutated)"}
            prev = r["row_hash"]
    return {"ok": True, "length": len(seqs), "broken_at": None}


def tamper(seq: int, new_verdict: str = "allow") -> bool:
    """DEMO ONLY: mutate a row's verdict in place to prove the chain catches it."""
    with _conn() as c:
        r = c.execute("SELECT payload FROM ledger WHERE seq=?", (seq,)).fetchone()
        if not r:
            return False
        payload = json.loads(r["payload"])
        payload["verdict"] = new_verdict
        c.execute("UPDATE ledger SET payload=? WHERE seq=?",
                  (json.dumps(payload, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":")), seq))
    return True


def clear() -> None:
    with _conn() as c:
        c.execute("DROP TABLE IF EXISTS ledger")
    init()
