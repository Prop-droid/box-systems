#!/usr/bin/env python3
"""Skill + tool usage telemetry from Claude Code transcripts (box + staged Mac).

Deterministic (no LLM). For a lookback window it counts, per tool and per skill:
how often each is used and how often its result errored, then cross-references the
local skill catalog to surface skills that are NEVER used (dead weight in the
always-loaded catalog listing that token-audit flagged at ~16k chars). Emits a
markdown report and persists stats.json for week-over-week deltas.

The point: "optimised for my usage" needs data on what actually fires. Heavy,
error-prone tools and a long tail of never-invoked skills are the levers.

Skill usage is read from three signals, because the Skill tool alone undercounts:
  1. Skill tool calls in the transcripts (bot/Hermes-dispatched sessions land in
     ~/.claude/projects too, so they ARE counted here).
  2. Direct SKILL.md reads (Read tool, or cat/sed in Bash): how headless and
     dispatched sessions use a skill without the Skill tool.
  3. Hermes's own ledger (~/.hermes/skills/.usage.json): skills the Hermes agent
     loaded itself, which never appear in any Claude Code transcript.
A skill is "never used" only when all three are silent for the window.

Usage: python3 telemetry.py [--days 30] [--out report.md]
"""
import argparse
import json
import os
import re
import time
from collections import Counter
from glob import glob

DIR = os.path.dirname(os.path.abspath(__file__))
ROOTS = [
    os.path.expanduser("~/.claude/projects"),
    os.path.join(os.path.dirname(DIR), "correction-capture/staging/mac"),
]
SKILLS_DIR = os.path.expanduser("~/.claude/skills")
HERMES_USAGE = os.path.expanduser("~/.hermes/skills/.usage.json")
STATS = os.path.join(DIR, "stats.json")
# .../skills/<name>/SKILL.md, also nested (.../skills/creative/comfyui/SKILL.md)
SKILL_MD = re.compile(r"/skills/(?:[\w.-]+/)*?([\w-]+)/SKILL\.md")
# Bash only counts as a read when it actually prints the file (not ls/rm/ln/grep -l).
READ_VERB = re.compile(r"\b(cat|head|tail|sed|less|awk|bat)\b")


def hermes_ledger(path=None):
    """Hermes's per-skill counters: {name: {"uses": int, "last": "YYYY-MM-DD"}}. {} if absent."""
    try:
        with open(path or HERMES_USAGE) as fh:
            raw = json.load(fh)
    except Exception:
        return {}
    out = {}
    for name, v in (raw.items() if isinstance(raw, dict) else []):
        if isinstance(v, dict):
            out[name] = {"uses": int(v.get("use_count") or 0),
                         "last": str(v.get("last_used_at") or "")[:10]}
    return out


def hermes_recent(ledger, days, now=None):
    """Names Hermes itself used inside the window (by last_used_at; counts are all-time)."""
    cutoff = time.strftime("%Y-%m-%d", time.gmtime((now or time.time()) - days * 86400))
    return {n for n, v in ledger.items() if v.get("last") and v["last"] >= cutoff}


def scan_file(path, tools, tool_err, skills, reads=None):
    """One pass: count tool_use per tool, attribute tool_result errors by name.
    When `reads` is given, also count direct SKILL.md reads per skill."""
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
                    elif reads is not None and name in ("Read", "Bash"):
                        inp = b.get("input") or {}
                        src = inp.get("file_path") if name == "Read" else inp.get("command")
                        if (isinstance(src, str) and "SKILL.md" in src
                                and (name == "Read" or READ_VERB.search(src))):
                            for s in set(SKILL_MD.findall(src)):
                                reads[s] += 1
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
    tools, tool_err, skills, reads = Counter(), Counter(), Counter(), Counter()
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
            scan_file(path, tools, tool_err, skills, reads)
            files += 1
    return {"tools": tools, "tool_err": tool_err, "skills": skills, "files": files,
            "reads": reads, "hermes": hermes_ledger()}


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
    reads = data.get("reads") or Counter()
    ledger = data.get("hermes") or {}
    h_recent = hermes_recent(ledger, days)
    used = set(skills)
    never = sorted(catalog() - used - set(reads) - h_recent)
    lines = []
    lines.append(f"# Skill + tool telemetry — last {days}d")
    lines.append("")
    lines.append(f"Scanned {data['files']} transcripts (box + staged Mac). "
                 f"{sum(tools.values())} tool calls, {sum(skills.values())} skill invocations "
                 f"across {len(used)} distinct skills, {sum(reads.values())} direct SKILL.md reads. "
                 f"Skill catalog (local): {len(catalog())}.")
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
    lines.append("| Skill | Uses | Δ vs last | SKILL.md reads |")
    lines.append("|---|---|---|---|")
    sd = delta(data, prev, "skills") if prev else {}
    names = sorted(set(skills) | set(reads),
                   key=lambda s: (-skills.get(s, 0), -reads.get(s, 0), s))
    for name in names[:30]:
        n = skills.get(name, 0)
        d = sd.get(name)
        dtxt = f"{'+' if d and d > 0 else ''}{d}" if d is not None else ("new" if n else "-")
        lines.append(f"| {name} | {n} | {dtxt} | {reads.get(name, 0)} |")
    lines.append("")

    lines.append("## Hermes-side skill usage")
    if ledger:
        lines.append(f"From Hermes's own ledger (`~/.hermes/skills/.usage.json`, {len(ledger)} skills "
                     "tracked): skills the Hermes agent loaded itself, which never show up in Claude "
                     "Code transcripts. Counts are all-time; rows = last used inside the window.")
        lines.append("")
        if h_recent:
            lines.append("| Skill | Hermes uses (all-time) | Last used |")
            lines.append("|---|---|---|")
            for name in sorted(h_recent, key=lambda s: (-ledger[s]["uses"], s)):
                lines.append(f"| {name} | {ledger[name]['uses']} | {ledger[name]['last']} |")
        else:
            lines.append("(no Hermes-side skill use in the window)")
    else:
        lines.append("(no Hermes ledger found)")
    lines.append("")

    lines.append(f"## Never-used local skills ({len(never)} of {len(catalog())})")
    lines.append("Silent on all three signals in the window (Skill tool, direct SKILL.md reads, "
                 "Hermes ledger), yet they load into the catalog listing every session. "
                 "Candidates to prune from the always-loaded set.")
    lines.append("")
    lines.append(", ".join(never) if never else "(all catalog skills used)")
    lines.append("")
    return "\n".join(lines)


def to_stats(data):
    return {"files": data["files"], "tools": dict(data["tools"]),
            "tool_err": dict(data["tool_err"]), "skills": dict(data["skills"]),
            "reads": dict(data.get("reads") or {})}


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
