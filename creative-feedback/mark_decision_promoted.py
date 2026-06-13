#!/usr/bin/env python3
"""Append override ts-keys to decisions_promoted.json (deduped JSON array).

Usage:  python3 mark_decision_promoted.py <ts1> <ts2> ...
Dir:    $FEEDBACK_DIR (default: this script's dir).
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv) -> int:
    if not argv:
        print("ERROR: pass one or more override ts keys", file=sys.stderr)
        return 1
    fb_dir = os.environ.get("FEEDBACK_DIR", HERE)
    path = os.path.join(fb_dir, "decisions_promoted.json")
    existing = []
    if os.path.exists(path):
        try:
            existing = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            existing = []
    merged = sorted(set(existing) | set(argv))
    fd, tmp = tempfile.mkstemp(dir=fb_dir, prefix=".decprom_", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(merged, out, ensure_ascii=False, indent=0)
    os.replace(tmp, path)
    print(f"OK promoted {len(set(argv))} decision key(s); {len(merged)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
