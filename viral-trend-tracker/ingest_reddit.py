#!/usr/bin/env python3
"""VTT Reddit lane. Daily social-heat = sum(score+comments) of relevance-filtered
posts per watchlist term (last week, relevance-sorted) via the `rdt` CLI.
Writes source="reddit". Run: python3 ingest_reddit.py  (rdt must be authed).
Exit 1 unless >= MIN_OK_TERMS terms return data.
"""
import json
import os
import subprocess
import sys
import time

from vtt_common import load_watchlist, relevant, write_merged

RDT = os.path.expanduser("~/.local/bin/rdt")
PER_TERM = 25
MIN_OK_TERMS = 6


def heat(term):
    try:
        r = subprocess.run([RDT, "search", term, "-s", "relevance", "-t", "week",
                            "-n", str(PER_TERM), "--json"], capture_output=True, text=True, timeout=45)
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
    rows, ok = [], 0
    from datetime import date
    today = date.today().isoformat()
    for t in load_watchlist():
        h = heat(t)
        if h is None:
            continue
        value, posts = h
        rows.append({"date": today, "source": "reddit", "platform": "reddit",
                     "term": t, "value": value, "posts": posts})
        if posts > 0:
            ok += 1
        print(f"{t}: heat={value} ({posts} posts)", file=sys.stderr)
        time.sleep(1)
    write_merged("reddit", "reddit", rows, ok)
    if ok < MIN_OK_TERMS:
        sys.exit(1)


if __name__ == "__main__":
    main()
