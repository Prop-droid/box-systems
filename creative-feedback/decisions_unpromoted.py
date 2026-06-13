#!/usr/bin/env python3
"""Print un-promoted decision DISAGREEMENTS from the CCC override log.

Input  : the override JSONL (path from $OVERRIDE_LOG or argv[1]).
Exclude: agreements, dry_run entries, and any entry whose `ts` key is already in
         decisions_promoted.json (in $FEEDBACK_DIR, default this script's dir).
Output : one JSON object per line, with an added `key` (= ts) for idempotency.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv) -> int:
    olog = os.environ.get("OVERRIDE_LOG") or (argv[0] if argv else "")
    if not olog or not os.path.exists(olog):
        print("# (override log empty or missing)", file=sys.stderr)
        return 0
    fb_dir = os.environ.get("FEEDBACK_DIR", HERE)
    promoted_path = os.path.join(fb_dir, "decisions_promoted.json")
    promoted = set()
    if os.path.exists(promoted_path):
        try:
            promoted = set(json.load(open(promoted_path, encoding="utf-8")))
        except (json.JSONDecodeError, ValueError):
            print("# WARN: decisions_promoted.json unreadable, treating as empty", file=sys.stderr)
    count = 0
    with open(olog, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(f"# WARN: skipped malformed override line {n}", file=sys.stderr)
                continue
            if rec.get("agree", True):
                continue
            if rec.get("mode") == "dry_run":
                continue
            key = rec.get("ts")
            if not key or key in promoted:
                continue
            rec["key"] = key
            print(json.dumps(rec, ensure_ascii=False))
            count += 1
    print(f"# {count} un-promoted decision disagreement(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
