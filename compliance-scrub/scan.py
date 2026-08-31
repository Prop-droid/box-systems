#!/usr/bin/env python3
"""Nightly compliance scrub: scan recently-changed copy surfaces for banned
Shameless claims, deterministic regex only (no LLM).

Source of truth = ~/systems/compliance-eval/policy.json (hard/warn/allow),
same semantics as the eval scorer: a hard/warn hit whose matched span falls
inside an allow-phrase match on the same line is suppressed.

Scans *.md changed in the last SCRUB_WINDOW_HOURS (default 25) under
~/brain/wiki and ~/brain/projects — but ONLY shippable-copy surfaces.
Internal surfaces that legitimately name banned terms (work logs, weekly
reports, competitor ad dumps/analysis, substantiation/legal, meta) are
excluded, or the digest is 90% noise (183-hit first dry run, 2026-08-31).
Writes reports/latest.md always; posts to Discord #creative only when there
are hits (quiet when clean).

Env: SCRUB_DRY=1 (print, no post), SCRUB_WINDOW_HOURS, SCRUB_ROOTS (colon-sep).
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
POLICY = Path.home() / "systems/compliance-eval/policy.json"
POST = Path.home() / "systems/lib/discord-post.sh"
CREATIVE_CH = "1531648564932120737"
REPORTS = HERE / "reports"
DRY = os.environ.get("SCRUB_DRY") == "1"
WINDOW_H = float(os.environ.get("SCRUB_WINDOW_HOURS", "25"))
ROOTS = [Path(p).expanduser() for p in os.environ.get(
    "SCRUB_ROOTS", "~/brain/wiki:~/brain/projects").split(":")]


def load_policy():
    p = json.loads(POLICY.read_text())
    def comp(rules):
        return [(r["id"], r["why"], [re.compile(pat, re.I) for pat in r["patterns"]])
                for r in rules]
    allow = [re.compile(pat, re.I) for pat in p["allow"]["patterns"]]
    return comp(p["hard"]), comp(p["warn"]), allow


def allowed_spans(line, allow):
    return [m.span() for rx in allow for m in rx.finditer(line)]


def scan_file(path, hard, warn, allow):
    hits = []
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return hits
    for ln, line in enumerate(text.splitlines(), 1):
        spans = allowed_spans(line, allow)
        for sev, rules in (("HARD", hard), ("WARN", warn)):
            for rid, why, rxs in rules:
                for rx in rxs:
                    for m in rx.finditer(line):
                        if any(a <= m.start() and m.end() <= b for a, b in spans):
                            continue
                        hits.append((sev, rid, why, path, ln, m.group(0), line.strip()[:160]))
    return hits


def main():
    hard, warn, allow = load_policy()
    cutoff = time.time() - WINDOW_H * 3600
    files = []
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            s = str(p).lower()
            if any(x in s for x in (
                    "/raw/", "legal", ".bak", "/log.md", "/index.md", "/meta/",
                    "competitor", "competitive", "atria", "weekly-report",
                    "substantiation", "research", "swipe")):
                continue
            try:
                if p.stat().st_mtime >= cutoff:
                    files.append(p)
            except OSError:
                pass

    all_hits = []
    for f in files:
        all_hits.extend(scan_file(f, hard, warn, allow))

    REPORTS.mkdir(exist_ok=True)
    today = time.strftime("%Y-%m-%d")
    lines = [f"# Compliance scrub — {today}",
             f"{len(files)} changed file(s) in last {WINDOW_H:.0f}h, {len(all_hits)} hit(s)", ""]
    for sev, rid, why, path, ln, frag, ctx in all_hits:
        rel = str(path).replace(str(Path.home()), "~")
        lines.append(f"- **{sev}/{rid}** `{rel}:{ln}` — \"{frag}\" ({why})\n  > {ctx}")
    report = "\n".join(lines) + "\n"
    (REPORTS / "latest.md").write_text(report)
    (REPORTS / f"{today}.md").write_text(report)
    print(f"{len(files)} file(s) scanned, {len(all_hits)} hit(s)")

    if not all_hits:
        return 0
    # Digest aggregates per file+rule (52 raw GLP-1 lines = one row), full
    # line-level detail stays in the report file.
    agg = {}
    for sev, rid, why, path, ln, frag, _ in all_hits:
        rel = str(path).replace(str(Path.home()), "~")
        key = (rel, sev, rid)
        agg.setdefault(key, {"n": 0, "frag": frag, "why": why})["n"] += 1
    digest = [f"🚫 **Compliance scrub — {len(all_hits)} hit(s) in copy changed yesterday**"]
    rows = sorted(agg.items(), key=lambda kv: (kv[0][1] != "HARD", -kv[1]["n"]))
    for (rel, sev, rid), v in rows[:10]:
        digest.append(f"- {sev} **{rid}** ×{v['n']} in `{rel}` (e.g. \"{v['frag']}\" — {v['why']})")
    if len(rows) > 10:
        digest.append(f"…and {len(rows) - 10} more rule(s) — full list: ~/systems/compliance-scrub/reports/{today}.md")
    digest.append(f"Line-level detail: ~/systems/compliance-scrub/reports/{today}.md")
    digest.append("Reply `fix` to apply approved replacements (route-to-legal items excluded).")
    body = "\n".join(digest)
    if DRY:
        print("--- DRY digest ---\n" + body)
        return 0
    subprocess.run(["bash", str(POST), CREATIVE_CH, "CREATIVE_TOKEN"],
                   input=body, text=True, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
