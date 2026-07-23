#!/usr/bin/env python3
"""Brand-canon needle test — gkamradt needle-in-a-haystack adapted to the wiki.

For each needle in needles.yaml, spawns a headless `claude -p` that must answer
the question ONLY from the wiki, then scores the answer exact_match style:
score = fraction of expected fragments present (case-insensitive substring);
any forbidden fragment present = automatic FAIL (drift detected).

Usage:
    python3 run.py                 # full run
    python3 run.py --only fiber-grams,sub-price
    python3 run.py --dry-run       # print prompts, no claude calls
    python3 run.py --model claude-haiku-4-5-20251001

Output: report-YYYY-MM-DD.md in this directory (+ stdout summary).
Upstream methodology: gkamradt/LLMTest_NeedleInAHaystack (local clone: ~/.tools/needle-in-a-haystack).
"""

import argparse
import datetime
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
WIKI = HERE.parent.parent / "wiki"
DEFAULT_MODEL = "claude-sonnet-5"

PROMPT = (
    "Answer this question about Shameless Snacks using ONLY the wiki files in the current "
    "directory (grep/read them; canon pages live under shameless/brand/ and "
    "shameless/working-cards/). If pages conflict, say so and name the conflict. "
    "If the wiki does not contain the answer, say NOT DOCUMENTED. Be concise (under 80 words). "
    "Question: {q}"
)


def parse_needles(path):
    """Minimal YAML-subset parser for needles.yaml (id/q/expected/forbidden lists)."""
    needles, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"\s*-\s+id:\s*(\S+)", line):
            cur = {"id": m.group(1), "q": "", "expected": [], "forbidden": []}
            needles.append(cur)
        elif cur is not None:
            if m := re.match(r'\s+q:\s*"(.*)"\s*$', line):
                cur["q"] = m.group(1)
            elif m := re.match(r"\s+(expected|forbidden):\s*\[(.*)\]\s*$", line):
                cur[m.group(1)] = [f for f in re.findall(r'"([^"]*)"', m.group(2)) if f]
    return needles


def ask(question, model, timeout=180):
    result = subprocess.run(
        ["claude", "-p", PROMPT.format(q=question), "--model", model,
         "--allowedTools", "Read,Grep,Glob"],
        cwd=WIKI, capture_output=True, text=True, timeout=timeout,
    )
    return (result.stdout or result.stderr).strip()


def score(answer, needle):
    """Fragments support "a|b" alternatives: the fragment counts if ANY alternative matches."""
    low = answer.lower()
    hit_forbidden = [f for f in needle["forbidden"] if f and f.lower() in low]
    found = [e for e in needle["expected"]
             if e and any(alt.strip().lower() in low for alt in e.split("|"))]
    frac = len(found) / len(needle["expected"]) if needle["expected"] else 0.0
    if hit_forbidden:
        return 0.0, f"FORBIDDEN fragment(s) in answer: {hit_forbidden}"
    missing = [e for e in needle["expected"] if e not in found]
    return frac, ("ok" if frac == 1.0 else f"missing: {missing}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated needle ids")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    needles = parse_needles(HERE / "needles.yaml")
    if args.only:
        wanted = set(args.only.split(","))
        needles = [n for n in needles if n["id"] in wanted]

    rows, failures = [], 0
    for n in needles:
        if args.dry_run:
            print(f"[dry] {n['id']}: {n['q']}")
            continue
        try:
            answer = ask(n["q"], args.model)
        except subprocess.TimeoutExpired:
            answer = "(timeout)"
        s, note = score(answer, n)
        status = "PASS" if s == 1.0 else ("FAIL" if s == 0.0 else f"PARTIAL {s:.0%}")
        if s < 1.0:
            failures += 1
        rows.append((n["id"], status, note, answer.replace("\n", " ")[:300]))
        print(f"{status:12} {n['id']:22} {note}")

    if args.dry_run:
        return
    today = datetime.date.today().isoformat()
    suffix = "-partial" if args.only else ""
    report = HERE / f"report-{today}{suffix}.md"
    lines = [f"# Needle test report — {today}",
             f"Model: {args.model} · Needles: {len(rows)} · Failures/partials: {failures}", "",
             "| Needle | Status | Note | Answer (truncated) |", "|---|---|---|---|"]
    lines += [f"| {i} | {st} | {no} | {an} |" for i, st, no, an in rows]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport: {report}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
