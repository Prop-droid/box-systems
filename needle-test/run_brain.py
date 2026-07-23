#!/usr/bin/env python3
"""Brand-canon needle test — eJam Company Brain edition.

Same needles and scoring as run.py, but each headless run may use ONLY the
company-brain MCP tools (search_knowledge / read_knowledge / knowledge_index)
— no wiki file access — so it measures whether an agent grounding on the
BRAIN (like any ejam teammate's AI will) retrieves the right canon.

Usage mirrors run.py:  python3 run_brain.py [--only ids] [--dry-run] [--model m]
Report: report-brain-YYYY-MM-DD.md
"""

import argparse
import concurrent.futures
import datetime
import pathlib
import subprocess
import sys
import threading

import guard
from run import parse_needles, score

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_MODEL = "claude-sonnet-5"
CWD = pathlib.Path.home()  # NOT ~/brain: must not see the wiki or its CLAUDE.md
BRAIN_TOOLS = "mcp__brain__search_knowledge,mcp__brain__read_knowledge,mcp__brain__knowledge_index"

PROMPT = (
    "Answer this question about Shameless Snacks using ONLY the ejam company-brain MCP "
    "(server name: brain). Ground first: search_knowledge with the key terms, read_knowledge "
    "the top hits, and answer only from entry content, citing the slug(s) you used. "
    "Do NOT use your own knowledge and do NOT read any local files. "
    "If the brain does not contain the answer, say NOT DOCUMENTED. Be concise (under 80 words). "
    "Question: {q}"
)


def ask(question, model, timeout=300):
    # guard.mcp_args pins the MCP config to ONLY the brain server: without it
    # each needle boots all 6 ~/.claude.json servers (melted the box 2026-07-23).
    result = subprocess.run(
        ["claude", "-p", PROMPT.format(q=question), "--model", model,
         "--allowedTools", BRAIN_TOOLS,
         "--disallowedTools", "Read,Grep,Glob,Bash,WebFetch,WebSearch",
         *guard.mcp_args(["brain"])],
        cwd=CWD, capture_output=True, text=True, timeout=timeout,
    )
    return (result.stdout or result.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated needle ids")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    # 2 workers max: this is a shared 4-core box, and each worker is a full
    # claude process. 4 concurrent spawns contributed to the 2026-07-23 melt.
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--fresh", action="store_true", help="ignore today's checkpoint; re-ask everything")
    args = ap.parse_args()
    args.workers = min(args.workers, 2)

    needles = parse_needles(HERE / "needles.yaml")
    if args.only:
        wanted = set(args.only.split(","))
        needles = [n for n in needles if n["id"] in wanted]
    if args.dry_run:
        for n in needles:
            print(f"[dry] {n['id']}: {n['q']}")
        return

    today = datetime.date.today().isoformat()
    ckpt = HERE / f"rows-brain-{today}.jsonl"
    if args.fresh:
        ckpt.unlink(missing_ok=True)
    done = {} if (args.only or args.fresh) else guard.load_done(ckpt)
    ckpt_lock = threading.Lock()

    def run_one(n):
        if n["id"] in done:
            r = done[n["id"]]
            print(f"{r['status']:12} {n['id']:22} (resumed from checkpoint)", flush=True)
            return (r["id"], r["status"], r["note"], r["answer"], r["score"])
        guard.wait_for_capacity()
        try:
            answer = ask(n["q"], args.model)
        except subprocess.TimeoutExpired:
            answer = "(timeout)"
        s, note = score(answer, n)
        status = "PASS" if s == 1.0 else ("FAIL" if s == 0.0 else f"PARTIAL {s:.0%}")
        print(f"{status:12} {n['id']:22} {note}", flush=True)
        row = (n["id"], status, note, answer.replace("\n", " ")[:300], s)
        with ckpt_lock:
            guard.checkpoint(ckpt, {"id": row[0], "status": status, "note": note,
                                    "answer": row[3], "score": s})
        return row

    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run_one, needles))

    failures = sum(1 for r in rows if r[4] < 1.0)
    today = datetime.date.today().isoformat()
    suffix = "-partial" if args.only else ""
    report = HERE / f"report-brain-{today}{suffix}.md"
    lines = [f"# Needle test report (Company Brain grounding) — {today}",
             f"Model: {args.model} · Needles: {len(rows)} · Failures/partials: {failures}",
             "Haystack: eJam Company Brain MCP (no wiki access)", "",
             "| Needle | Status | Note | Answer (truncated) |", "|---|---|---|---|"]
    lines += [f"| {i} | {st} | {no} | {an} |" for i, st, no, an, _ in rows]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport: {report}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
