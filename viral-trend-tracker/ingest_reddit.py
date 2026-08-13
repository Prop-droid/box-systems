#!/usr/bin/env python3
"""VTT ingest — Reddit social-heat lane (spec 2026-08-13-trend-tracker-research).

For each watchlist term, query Reddit (last week, relevance-sorted) via the `rdt`
CLI (auth wired 2026-08-13, see [[reference_ig_sourced_tools_installed]]), keep
topically-relevant posts, and record a daily "social heat" scalar = sum of
(score + comments) across kept posts. Over days these rows become the per-term
time series the VTT scorer consumes as the `social` lane (the .45 viral weight).

Appends {date, source:"social", platform:"reddit", term, value, posts} JSONL to
$VTT_DIR/social-reddit-<date>.jsonl (default VTT_DIR below). Merge-by-term on
re-run so a partial run never wipes the day's file (ad-rank lesson).

Run: rdt must be authenticated. `python3 ingest_reddit.py`
Exit 1 unless >= MIN_OK_TERMS terms returned data (empty result = FAILURE).
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

VTT_DIR = Path(os.environ.get("VTT_DIR", "/home/tomas/brain/projects/2026-08/viral-trend-tracker"))
WATCHLIST = Path(__file__).with_name("watchlist.txt")
RDT = os.path.expanduser("~/.local/bin/rdt")
PER_TERM = 25          # results pulled per term
MIN_OK_TERMS = 6       # run-level success floor
RELEVANT_SUBS = {
    "snacks", "eatcheapandhealthy", "nutrition", "fitness", "loseit", "functionalfood",
    "guthealth", "healthyfood", "xxfitness", "volumeeating", "candy", "keto", "1200isplenty",
    "productivity", "supplements", "advancedfitness", "flexibledieting", "gainit",
}

def load_watchlist():
    terms = []
    for line in WATCHLIST.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms

def relevant(term, title, subreddit):
    if subreddit.lower() in RELEVANT_SUBS:
        return True
    tl = title.lower()
    return any(w for w in term.lower().split() if len(w) >= 4 and w in tl)

def heat(term):
    try:
        r = subprocess.run([RDT, "search", term, "-s", "relevance", "-t", "week",
                            "-n", str(PER_TERM), "--json"],
                           capture_output=True, text=True, timeout=45)
        children = json.loads(r.stdout)["data"]["data"]["children"]
    except Exception as e:
        print(f"FAIL {term}: {e}", file=sys.stderr)
        return None
    total, kept = 0, 0
    for ch in children:
        d = ch.get("data", {})
        if relevant(term, d.get("title", ""), d.get("subreddit", "")):
            total += int(d.get("score", 0)) + int(d.get("num_comments", 0))
            kept += 1
    return total, kept

def main():
    terms = load_watchlist()
    today = date.today().isoformat()
    VTT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VTT_DIR / f"social-reddit-{today}.jsonl"

    rows, ok = [], 0
    for t in terms:
        h = heat(t)
        if h is None:
            continue
        value, posts = h
        rows.append({"date": today, "source": "social", "platform": "reddit",
                     "term": t, "value": value, "posts": posts})
        if posts > 0:
            ok += 1
        print(f"{t}: heat={value} ({posts} posts)", file=sys.stderr)
        time.sleep(1)

    # merge-by-term: keep today's rows for terms not scraped this run
    scraped = {r["term"] for r in rows}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("term") not in scraped:
                rows.append(r)
    rows.sort(key=lambda r: r["term"])
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.rename(out_path)
    print(f"{out_path}: {len(rows)} rows, {ok}/{len(terms)} terms with data", file=sys.stderr)
    if ok < MIN_OK_TERMS:
        sys.exit(1)

if __name__ == "__main__":
    main()
