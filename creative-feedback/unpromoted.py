#!/usr/bin/env python3
"""Print all un-promoted ledger records (promoted == false), one JSON per line.

This is the synthesis input. Idempotency comes from the `promoted` flag rather
than a timestamp watermark: a record stays eligible until a pattern that
includes it is promoted into canon. Malformed lines are skipped with a warning.

Usage:  python3 unpromoted.py
"""
import json
import os
import sys

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.jsonl")


def main() -> int:
    if not os.path.exists(LEDGER) or os.path.getsize(LEDGER) == 0:
        print("# (ledger empty or missing — nothing to synthesize)", file=sys.stderr)
        return 0
    count = 0
    with open(LEDGER, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(f"# WARN: skipped malformed ledger line {n}", file=sys.stderr)
                continue
            if not rec.get("promoted", False):
                print(json.dumps(rec, ensure_ascii=False))
                count += 1
    print(f"# {count} un-promoted record(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
