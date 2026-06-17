#!/usr/bin/env python3
"""Render proposals.jsonl (stdin) into a human-readable proposals.md digest (stdout).

Each proposal becomes a section a human can scan and approve. The gated promotion
step reads proposals.jsonl (not this digest) for the machine-applicable fields.

Usage:  python3 render_proposals_md.py < proposals.jsonl > proposals.md
"""
import json
import sys


def main() -> int:
    props = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            props.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not props:
        print("No stable patterns yet (need >= 3 consistent lessons per pattern).")
        return 0

    print(f"# Task-lessons promotion proposals ({len(props)})\n")
    print("Review, then apply approved ones and run "
          "`python3 mark_promoted.py <support_ids>`.\n")
    for p in props:
        kind = p.get("kind", "?")
        print(f"## [{p.get('id', '?')}] {p.get('skill', '?')} — {kind}\n")
        print(f"**Pattern:** {p.get('pattern', '')}\n")
        tgt = p.get("target", {}) or {}
        if kind == "contradiction":
            print("**Action:** human review (conflicting lessons)\n")
        elif tgt.get("type") == "gbrain_canon":
            print(f"**Target:** gbrain page `{tgt.get('slug', '?')}`\n")
        elif tgt.get("type") == "memory":
            print(f"**Target:** memory file `{tgt.get('path', '?')}`\n")
        ids = ", ".join(p.get("support_ids", []))
        print(f"**Supporting records:** {ids}\n")
        body = (p.get("body") or "").strip()
        if body:
            print("**Proposed body:**\n")
            print("```")
            print(body)
            print("```\n")
        print("---\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
