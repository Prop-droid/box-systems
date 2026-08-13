#!/usr/bin/env python3
"""Rule-gate: pre-promotion check for general (non-creative) rule proposals.

The creative keep-best gate blocks a promotion that raises the compliance
violation_rate. General operating rules (task-lessons -> memory canon) have no
such numeric metric, so this gate catches the three ways a promoted rule rots
the canon instead:

  contradiction  - it conflicts with an existing memory/canon rule
  redundant      - it already exists (canon bloat, no new signal)
  too_vague      - not specific/checkable enough to act on (fable-window
                   lesson #9: an ambiguous rule gets re-litigated forever)
  safe           - none of the above; a genuinely new, actionable rule

Retrieval is deterministic (keyword overlap over the memory corpus); the verdict
is one claude-max judgment over the top-related files. Advisory by default
(annotates, exits 0 so a run never silently drops proposals); --strict makes a
contradiction exit 2 so a caller can block auto-promotion.

Usage:
    python3 gate.py --rule "Always link the ClickUp task at the end of a reply."
    python3 gate.py --proposals proposals.jsonl        # annotate each memory-target proposal
Exit: 0 = advisory/clear, 2 = contradiction under --strict, 1 = error.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from glob import glob

MEMORY_DIR = os.path.expanduser("~/.claude/projects/-home-tomas/memory")
CLAUDE_MAX = "/usr/local/bin/claude-max"
TOP_K = 6
STOP = set("the a an and or of to in on for is are be do not with your you this that "
           "it as at by from into when then than only ever never always use used using "
           "should must can will would may via per if but so we i he".split())
BLOCKING = {"contradiction"}
VALID = {"safe", "redundant", "too_vague", "contradiction"}


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in STOP and len(w) > 2}


def corpus():
    """Return [(name, text)] for every memory file except the index."""
    out = []
    for p in sorted(glob(os.path.join(MEMORY_DIR, "*.md"))):
        if os.path.basename(p) == "MEMORY.md":
            continue
        try:
            out.append((os.path.basename(p), open(p, errors="replace").read()))
        except OSError:
            pass
    return out


def rank(rule, files, k=TOP_K):
    """Deterministic keyword-overlap ranking; returns top-k [(name, score, text)]."""
    rt = tokens(rule)
    if not rt:
        return []
    scored = []
    for name, text in files:
        overlap = len(rt & tokens(text))
        if overlap:
            scored.append((name, overlap, text))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


def build_prompt(rule, ranked):
    ctx = "\n\n".join(f"### {name}\n{text[:1500]}" for name, _, text in ranked) \
        or "(no related canon found)"
    return f"""You gate a proposed operating rule before it enters Tomas's Claude memory canon.

CANDIDATE RULE:
{rule}

MOST-RELATED EXISTING CANON (top {len(ranked)} files by keyword overlap):
{ctx}

Classify the candidate into exactly one verdict:
- "contradiction": it conflicts with a rule in the canon above. Name the file.
- "redundant": the canon above already states this; nothing new. Name the file.
- "too_vague": not specific or checkable enough to act on consistently.
- "safe": a genuinely new, actionable rule that fits the canon.

Output ONLY one JSON object, nothing else:
{{"verdict":"safe|redundant|too_vague|contradiction","conflict_file":"<filename or empty>","reason":"<one line>","suggested_scope":"<if too_vague, a tighter rewrite, else empty>"}}
No em dashes or en dashes anywhere."""


def judge(rule, ranked):
    """One claude-max call -> verdict dict. Returns unknown-verdict on any failure."""
    prompt = build_prompt(rule, ranked)
    try:
        p = subprocess.run([CLAUDE_MAX, "--print", "--model", "claude-sonnet-4-6"],
                           input=prompt, text=True, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"verdict": "unknown", "reason": f"judge failed: {e}", "conflict_file": "",
                "suggested_scope": ""}
    m = re.search(r"\{.*\}", p.stdout, re.S)
    if not m:
        return {"verdict": "unknown", "reason": "no json from judge", "conflict_file": "",
                "suggested_scope": ""}
    try:
        v = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"verdict": "unknown", "reason": "bad json from judge", "conflict_file": "",
                "suggested_scope": ""}
    if v.get("verdict") not in VALID:
        v["verdict"] = "unknown"
    v.setdefault("conflict_file", "")
    v.setdefault("reason", "")
    v.setdefault("suggested_scope", "")
    return v


def gate_rule(rule, files=None):
    files = corpus() if files is None else files
    ranked = rank(rule, files)
    v = judge(rule, ranked)
    v["rule"] = rule
    v["related"] = [name for name, _, _ in ranked]
    return v


def exit_code(verdicts, strict):
    if strict and any(v["verdict"] in BLOCKING for v in verdicts):
        return 2
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", help="single candidate rule to gate")
    ap.add_argument("--proposals", help="proposals.jsonl; gate each memory-target rule")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any verdict is a contradiction")
    ap.add_argument("--json", action="store_true", help="emit verdicts as JSONL")
    args = ap.parse_args()

    rules = []
    if args.rule:
        rules.append(args.rule)
    if args.proposals:
        for line in open(args.proposals):
            line = line.strip()
            if not line:
                continue
            try:
                prop = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Only gate rules headed for memory canon; gbrain lesson pages and
            # contradiction proposals are out of scope.
            if prop.get("kind") == "memory" or prop.get("target", {}).get("type") == "memory":
                body = prop.get("body", "")
                rules.append(body.strip().split("\n")[0][:400] or prop.get("pattern", ""))
    if not rules:
        print("nothing to gate (pass --rule or --proposals)", file=sys.stderr)
        return 1

    files = corpus()
    verdicts = [gate_rule(r, files) for r in rules]

    if args.json:
        for v in verdicts:
            print(json.dumps(v, ensure_ascii=False))
    else:
        for v in verdicts:
            tag = v["verdict"].upper()
            print(f"[{tag}] {v['rule'][:90]}")
            if v["conflict_file"]:
                print(f"    conflict: {v['conflict_file']}")
            if v["reason"]:
                print(f"    {v['reason']}")
            if v["suggested_scope"]:
                print(f"    tighter: {v['suggested_scope']}")
    return exit_code(verdicts, args.strict)


if __name__ == "__main__":
    sys.exit(main())
