#!/usr/bin/env python3
"""Skill + tool usage telemetry from Claude Code transcripts (box + staged Mac).

Deterministic (no LLM). For a lookback window it counts, per tool and per skill:
how often each is used and how often its result errored, then cross-references the
local skill catalog to surface skills that are NEVER used (dead weight in the
always-loaded catalog listing that token-audit flagged at ~16k chars). Emits a
markdown report and persists stats.json for week-over-week deltas.

The point: "optimised for my usage" needs data on what actually fires. Heavy,
error-prone tools and a long tail of never-invoked skills are the levers.

Usage: python3 telemetry.py [--days 30] [--out report.md]
"""
import argparse
import json
import os
import time
from collections import Counter
from glob import glob

DIR = os.path.dirname(os.path.abspath(__file__))
ROOTS = [
    os.path.expanduser("~/.claude/projects"),
    os.path.join(os.path.dirname(DIR), "correction-capture/staging/mac"),
]
SKILLS_DIR = os.path.expanduser("~/.claude/skills")
STATS = os.path.join(DIR, "stats.json")


def scan_file(path, tools, tool_err, skills):
    """One pass: count tool_use per tool, attribute tool_result errors by name."""
    id2name = {}
    try:
        fh = open(path, errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            try:
                e = json.loads(line)
            except Exception:
                continue
            t = e.get("type")
            content = (e.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            if t == "assistant":
                for b in content:
                    if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                        continue
                    name = b.get("name", "?")
                    tools[name] += 1
                    tid = b.get("id")
                    if tid:
                        id2name[tid] = name
                    if name == "Skill":
                        skills[(b.get("input") or {}).get("skill", "?")] += 1
            elif t == "user":
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                        name = id2name.get(b.get("tool_use_id"), "?")
                        tool_err[name] += 1


def catalog():
    """Local skill directory names (the always-loaded catalog subset we control)."""
    if not os.path.isdir(SKILLS_DIR):
        return set()
    return {n for n in os.listdir(SKILLS_DIR)
            if os.path.isdir(os.path.join(SKILLS_DIR, n)) and not n.startswith(".")}


def collect(days):
    cutoff = time.time() - days * 86400
    tools, tool_err, skills = Counter(), Counter(), Counter()
    files = 0
    for root in ROOTS:
        for path in glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            if "/memory/" in path:
                continue
            try:
                if os.stat(path).st_mtime < cutoff:
                    continue
            except OSError:
                continue
            scan_file(path, tools, tool_err, skills)
            files += 1
    return {"tools": tools, "tool_err": tool_err, "skills": skills, "files": files}


def load_prev():
    if os.path.exists(STATS):
        try:
            return json.load(open(STATS))
        except Exception:
            pass
    return {}


def delta(cur, prev, key):
    p = prev.get(key, {})
    return {k: cur[key][k] - p.get(k, 0) for k in cur[key]}


def render(data, days, prev):
    tools, tool_err, skills = data["tools"], data["tool_err"], data["skills"]
    used = set(skills)
    never = sorted(catalog() - used)
    lines = []
    lines.append(f"# Skill + tool telemetry — last {days}d")
    lines.append("")
    lines.append(f"Scanned {data['files']} transcripts (box + staged Mac). "
                 f"{sum(tools.values())} tool calls, {sum(skills.values())} skill invocations "
                 f"across {len(used)} distinct skills. Skill catalog (local): {len(catalog())}.")
    prev_files = prev.get("files")
    if prev_files is not None:
        lines.append(f"Previous run: {prev_files} transcripts, "
                     f"{sum(prev.get('skills', {}).values())} skill invocations.")
    lines.append("")

    lines.append("## Tool mix (top 15) + error rate")
    lines.append("| Tool | Calls | Errors | Err % |")
    lines.append("|---|---|---|---|")
    for name, n in tools.most_common(15):
        e = tool_err.get(name, 0)
        lines.append(f"| {name} | {n} | {e} | {round(100*e/n,1) if n else 0}% |")
    lines.append("")

    high = [(n, tool_err[n], tools.get(n, 0)) for n in tool_err
            if tools.get(n, 0) >= 10 and tool_err[n] / tools[n] >= 0.15]
    if high:
        lines.append("## High error-rate tools (>=15% over >=10 calls)")
        for n, e, c in sorted(high, key=lambda x: -x[1] / x[2]):
            lines.append(f"- **{n}**: {e}/{c} = {round(100*e/c,1)}% errored")
        lines.append("")

    lines.append("## Skill usage")
    lines.append("| Skill | Uses | Δ vs last |")
    lines.append("|---|---|---|")
    sd = delta(data, prev, "skills") if prev else {}
    for name, n in skills.most_common(30):
        d = sd.get(name)
        dtxt = f"{'+' if d and d > 0 else ''}{d}" if d is not None else "new"
        lines.append(f"| {name} | {n} | {dtxt} |")
    lines.append("")

    lines.append(f"## Never-used local skills ({len(never)} of {len(catalog())})")
    lines.append("These load into the catalog listing every session but never fired in "
                 f"the window. Candidates to prune from the always-loaded set.")
    lines.append("")
    lines.append(", ".join(never) if never else "(all catalog skills used)")
    lines.append("")
    return "\n".join(lines)


def to_stats(data):
    return {"files": data["files"], "tools": dict(data["tools"]),
            "tool_err": dict(data["tool_err"]), "skills": dict(data["skills"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default=os.path.join(DIR, "report.md"))
    ap.add_argument("--no-save", action="store_true", help="do not overwrite stats.json")
    args = ap.parse_args()

    prev = load_prev()
    data = collect(args.days)
    report = render(data, args.days, prev)
    with open(args.out, "w") as f:
        f.write(report + "\n")
    if not args.no_save:
        tmp = STATS + ".tmp"
        json.dump(to_stats(data), open(tmp, "w"))
        os.replace(tmp, STATS)
    print(report)


if __name__ == "__main__":
    main()
