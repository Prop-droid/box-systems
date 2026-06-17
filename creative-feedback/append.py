#!/usr/bin/env python3
"""Append one creative-feedback record to ledger.jsonl (atomic, append-only).

Reads a JSON object from stdin, injects id/ts/promoted if missing, validates
required fields, and writes exactly one line. Used by the /feedback command.

Usage:  python3 append.py < record.json
"""
import json
import os
import sys
import uuid
from datetime import datetime

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.jsonl")

REQUIRED = ("brand", "artifact_type", "verdict", "draft")
VALID_VERDICTS = {"shipped", "edited", "killed"}
VALID_TYPES = {"script", "brief", "ad_copy", "email", "lp", "hook"}


def main() -> int:
    try:
        rec = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: stdin is not valid JSON: {e}", file=sys.stderr)
        return 1

    if not isinstance(rec, dict):
        print("ERROR: record must be a JSON object", file=sys.stderr)
        return 1

    missing = [k for k in REQUIRED if not rec.get(k)]
    if missing:
        print(f"ERROR: missing required field(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    if rec["verdict"] not in VALID_VERDICTS:
        print(f"ERROR: verdict must be one of {sorted(VALID_VERDICTS)}", file=sys.stderr)
        return 1
    if rec["artifact_type"] not in VALID_TYPES:
        print(f"ERROR: artifact_type must be one of {sorted(VALID_TYPES)}", file=sys.stderr)
        return 1

    rec.setdefault("id", "fb_" + uuid.uuid4().hex[:8])
    rec.setdefault("ts", datetime.now().astimezone().isoformat(timespec="seconds"))
    rec.setdefault("promoted", False)
    rec.setdefault("tags", [])
    # normalize field order for readability (not required, but tidy)
    ordered = {k: rec[k] for k in
               ("ts", "id", "brand", "artifact_type", "skill", "verdict",
                "draft", "final", "diff_summary", "lesson", "tags", "promoted")
               if k in rec}
    # keep any extra keys
    for k, v in rec.items():
        ordered.setdefault(k, v)

    line = json.dumps(ordered, ensure_ascii=False)
    # O_APPEND guarantees the whole line lands atomically for a single write().
    fd = os.open(LEDGER, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)

    print(f"OK logged {ordered['id']} [{ordered['brand']}/{ordered['artifact_type']}/{ordered['verdict']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
