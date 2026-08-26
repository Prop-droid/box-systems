#!/usr/bin/env python3
"""VTT X/Twitter lane. Daily social-heat = sum(likes+retweets+replies) of
relevance-filtered tweets per watchlist term (last week) via the `tw` wrapper
(sources x.env + refreshes the CT cache). Writes source="x".
Run: python3 ingest_x.py   Exit 1 unless >= MIN_OK_TERMS terms return data.
"""
import json
import os
import subprocess
import sys
import time
from datetime import date

from vtt_common import load_watchlist, relevant, write_merged, write_receipts, top_receipts

TW = os.path.expanduser("~/.local/bin/tw")
PER_TERM = 25
MIN_OK_TERMS = 5


def heat(term):
    try:
        r = subprocess.run([TW, "search", term, "-n", str(PER_TERM), "--json"],
                           capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout)
    except Exception as e:
        print(f"FAIL {term}: {e}", file=sys.stderr)
        return None
    if not data.get("ok"):
        print(f"FAIL {term}: tw not ok", file=sys.stderr)
        return None
    total, kept, posts = 0, 0, []
    for tw in data.get("data", []):
        if not relevant(term, tw.get("text", "")):
            continue
        m = tw.get("metrics", {})
        score = int(m.get("likes", 0)) + int(m.get("retweets", 0)) + int(m.get("replies", 0))
        total += score
        kept += 1
        if tw.get("id"):
            title = " ".join(str(tw.get("text", "")).split())
            posts.append((title, f"https://x.com/i/web/status/{tw['id']}", score))
    return total, kept, posts


def main():
    rows, receipts, ok = [], [], 0
    today = date.today().isoformat()
    for t in load_watchlist():
        h = heat(t)
        if h is None:
            continue
        value, posts, kept = h
        rows.append({"date": today, "source": "x", "platform": "x",
                     "term": t, "value": value, "posts": posts})
        receipts.extend(top_receipts("x", "x", t, kept))
        if posts > 0:
            ok += 1
        print(f"{t}: heat={value} ({posts} tweets)", file=sys.stderr)
        time.sleep(1)
    write_merged("x", "x", rows, ok)
    write_receipts("x", "x", receipts)
    if ok < MIN_OK_TERMS:
        sys.exit(1)


if __name__ == "__main__":
    main()
