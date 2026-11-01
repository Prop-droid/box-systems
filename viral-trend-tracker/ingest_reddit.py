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

from vtt_common import load_watchlist, relevant, write_merged, write_receipts, top_receipts

RDT = os.path.expanduser("~/.local/bin/rdt")
PER_TERM = 25
MIN_OK_TERMS = 6


def heat(term):
    try:
        r = subprocess.run([RDT, "search", term, "-s", "relevance", "-t", "week",
                            "-n", str(PER_TERM), "--json"], capture_output=True, text=True, timeout=45)
        payload = json.loads(r.stdout)
        if payload.get("ok") is False:  # rdt error envelope, e.g. {"error": {"code": "forbidden"}}
            err = payload.get("error") or {}
            raise RuntimeError(f"rdt {err.get('code')}: {err.get('message')}")
        children = payload["data"]["data"]["children"]
    except Exception as e:
        print(f"FAIL {term}: {e}", file=sys.stderr)
        return None
    total, kept, posts = 0, 0, []
    for ch in children:
        d = ch.get("data", {})
        if relevant(term, d.get("title", ""), d.get("subreddit", "")):
            score = int(d.get("score", 0)) + int(d.get("num_comments", 0))
            total += score
            kept += 1
            if d.get("permalink"):
                posts.append((d.get("title", ""), "https://reddit.com" + d["permalink"], score))
    return total, kept, posts


def main():
    rows, receipts, ok = [], [], 0
    from datetime import date
    today = date.today().isoformat()
    for t in load_watchlist():
        h = heat(t)
        if h is None:
            continue
        value, posts, kept = h
        rows.append({"date": today, "source": "reddit", "platform": "reddit",
                     "term": t, "value": value, "posts": posts})
        receipts.extend(top_receipts("reddit", "reddit", t, kept))
        if posts > 0:
            ok += 1
        print(f"{t}: heat={value} ({posts} posts)", file=sys.stderr)
        time.sleep(1)
    write_merged("reddit", "reddit", rows, ok)
    write_receipts("reddit", "reddit", receipts)
    if ok < MIN_OK_TERMS:
        if ok == 0:
            # Every term failing = the lane, not the terms. The 2026-10-27..11-01
            # outage was Reddit rejecting the saved cookies ("forbidden"); anonymous
            # search.json is 403 from this box, so the only fix is fresh cookies.
            print("reddit lane DOWN: 0 terms returned data. If the errors say 'forbidden', Reddit rejected the saved "
                  "cookies — refresh ~/.config/rdt-cli/credential.json (export reddit.com cookies from a logged-in "
                  "browser; `rdt status` must show authenticated) and re-run.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
