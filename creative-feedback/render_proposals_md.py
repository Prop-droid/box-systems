#!/usr/bin/env python3
"""Render proposals.jsonl (stdin) as a markdown digest (stdout). Pure, deterministic."""
import json, sys
from datetime import datetime


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
        print("No stable patterns yet (need >= 3 consistent records per pattern).")
        return 0
    print(f"# Feedback — Promotion Proposals ({datetime.now().date().isoformat()})\n")
    for i, p in enumerate(props, 1):
        tgt = p.get("target", {})
        tgt_str = tgt.get("path") or tgt.get("key") or tgt.get("type", "")
        print(f"## Proposal {i}: {p.get('pattern', '(no pattern)')}  [{p.get('id','')}]")
        print(f"- Kind: {p.get('kind','')}")
        print(f"- Evidence: {len(p.get('support_ids', []))} records — {', '.join(p.get('support_ids', []))}")
        print(f"- Target: {tgt.get('type','')} {tgt_str}")
        print(f"- Proposed change:\n  {p.get('diff','')}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
