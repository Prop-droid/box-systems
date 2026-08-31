#!/usr/bin/env python3
"""Trend->brief gap tracker: did flagged viral trends actually get briefed?

Closes the 2-in-10 exploration-gate loop: vtt-digest flags trends Mondays in
#creative, but nothing checked whether a brief followed. Weekly, this reads
digests 7-28 days old, pulls ClickUp tasks created since each flag date
(Tomas list 901110066469), and reports flagged-but-never-briefed trends.

Matching is heuristic (task NAME tokens vs trend-term tokens; full phrase, or
>=2 significant tokens for multi-word terms) — labeled as such in the digest.

Env: GAP_DRY=1 (print, no post).
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIGESTS = HERE / "digests"
LIST_ID = "901110066469"
POST = Path.home() / "systems/lib/tg-post.sh"
TOPIC, TG_BOT = "📈 Viral Trends", "tg-creative-bot"
DRY = os.environ.get("GAP_DRY") == "1"
STOP = {"the", "and", "for", "with", "candy", "snack", "snacks"}


def clickup_token():
    return (Path.home() / ".config/clickup/pk").read_text().strip()


def flagged_terms():
    """[(term, date)] from digests 7-28 days old."""
    out = []
    today = datetime.now().date()
    for f in sorted(DIGESTS.glob("2026-*.md")):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        age = (today - d).days
        if not 7 <= age <= 28:
            continue
        for m in re.finditer(r"^- \*\*([^*]+)\*\*", f.read_text(), re.M):
            out.append((m.group(1).strip(), d))
    return out


def tasks_created_since(date):
    tok = clickup_token()
    ms = int(time.mktime(date.timetuple()) * 1000)
    names, page = [], 0
    while page < 10:
        q = urllib.parse.urlencode({
            "date_created_gt": ms, "include_closed": "true",
            "subtasks": "true", "page": page})
        req = urllib.request.Request(
            f"https://api.clickup.com/api/v2/list/{LIST_ID}/task?{q}",
            headers={"Authorization": tok})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        batch = d.get("tasks", [])
        names.extend(t.get("name", "") for t in batch)
        if d.get("last_page") or not batch:
            break
        page += 1
    return names


def matches(term, names):
    t = term.lower()
    toks = [w for w in re.findall(r"[a-z0-9]{4,}", t) if w not in STOP]
    hits = []
    for n in names:
        nl = n.lower()
        if t in nl or (len(toks) >= 2 and sum(w in nl for w in toks) >= 2) \
           or (len(toks) == 1 and toks[0] in nl):
            hits.append(n)
    return hits


def main():
    terms = flagged_terms()
    if not terms:
        print("no digests in the 7-28d window")
        return 0
    earliest = min(d for _, d in terms)
    names = tasks_created_since(earliest)
    print(f"{len(terms)} flagged term(s), {len(names)} task(s) created since {earliest}")

    briefed, gaps = [], []
    seen = set()
    for term, d in terms:
        if term.lower() in seen:
            continue
        seen.add(term.lower())
        hit = matches(term, names)
        (briefed if hit else gaps).append((term, d, hit))

    if not gaps:
        print("all flagged trends have matching tasks — staying quiet")
        return 0
    lines = ["📉 **Trend→brief gap check** (name-match heuristic, weekly)"]
    for term, d, _ in gaps:
        lines.append(f"- **{term}** — flagged {d}, no matching task created since. Reply `go {term}` to brief it, or ignore to drop.")
    if briefed:
        ok = ", ".join(t for t, _, _ in briefed)
        lines.append(f"✅ briefed: {ok}")
    body = "\n".join(lines)
    if DRY:
        print("--- DRY ---\n" + body)
        return 0
    subprocess.run(["bash", str(POST), TOPIC, TG_BOT],
                   input=body, text=True, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
