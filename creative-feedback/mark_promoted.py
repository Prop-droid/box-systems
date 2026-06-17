#!/usr/bin/env python3
"""Flip promoted=true for the given ledger record id(s).

Rewrites ledger.jsonl in place (via a temp file + atomic replace). Called by the
gated promotion step after a proposal is approved and applied to canon.

Usage:  python3 mark_promoted.py fb_1a2b3c4d fb_5e6f7a8b ...
"""
import json
import os
import sys
import tempfile

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.jsonl")


def main(argv) -> int:
    ids = set(argv)
    if not ids:
        print("ERROR: pass one or more record ids", file=sys.stderr)
        return 1
    if not os.path.exists(LEDGER):
        print("ERROR: ledger not found", file=sys.stderr)
        return 1

    flipped = 0
    dir_ = os.path.dirname(LEDGER)
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".ledger_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out, \
             open(LEDGER, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    rec = json.loads(s)
                except json.JSONDecodeError:
                    out.write(line if line.endswith("\n") else line + "\n")
                    continue
                if rec.get("id") in ids and not rec.get("promoted", False):
                    rec["promoted"] = True
                    flipped += 1
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp, LEDGER)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    print(f"OK promoted {flipped} record(s) of {len(ids)} requested")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
