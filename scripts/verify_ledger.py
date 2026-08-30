"""Walk the hash chain and report OK / BROKEN (spec M0, M5)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clearance import ledger


def main():
    v = ledger.verify_chain()
    if v["ok"]:
        print(f"OK  chain intact, {v['length']} rows")
        sys.exit(0)
    print(f"BROKEN at seq {v['broken_at']}: {v.get('reason')}  (length {v['length']})")
    sys.exit(1)


if __name__ == "__main__":
    main()
