#!/usr/bin/env python3
"""VTT YouTube lane (yt-dlp, no API key). Daily heat = sum of view_count across
relevance-filtered top search results per watchlist term. Writes source="youtube".
yt-dlp flat search omits upload_date, so this is a content-presence signal; the
scorer's day-over-day velocity still captures momentum as viral videos climb the
results. Run: python3 ingest_youtube.py  Exit 1 unless >= MIN_OK_TERMS return data.
"""
import json
import subprocess
import sys
import time
from datetime import date

from vtt_common import load_watchlist, relevant, write_merged, write_receipts, top_receipts

PER_TERM = 20
MIN_OK_TERMS = 5


def heat(term):
    try:
        r = subprocess.run(["yt-dlp", f"ytsearch{PER_TERM}:{term}", "--flat-playlist",
                            "--dump-json", "--no-warnings"],
                           capture_output=True, text=True, timeout=90)
    except Exception as e:
        print(f"FAIL {term}: {e}", file=sys.stderr)
        return None
    total, kept, posts = 0, 0, []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if relevant(term, d.get("title", ""), d.get("channel", "")):
            views = int(d.get("view_count") or 0)
            total += views
            kept += 1
            url = d.get("url") or (f"https://www.youtube.com/watch?v={d['id']}" if d.get("id") else "")
            posts.append((d.get("title", ""), url, views))
    return total, kept, posts


def main():
    rows, receipts, ok = [], [], 0
    today = date.today().isoformat()
    for t in load_watchlist():
        h = heat(t)
        if h is None:
            continue
        value, vids, kept = h
        rows.append({"date": today, "source": "youtube", "platform": "youtube",
                     "term": t, "value": value, "posts": vids})
        receipts.extend(top_receipts("youtube", "youtube", t, kept))
        if vids > 0:
            ok += 1
        print(f"{t}: views={value} ({vids} videos)", file=sys.stderr)
        time.sleep(0.3)
    write_merged("youtube", "youtube", rows, ok)
    write_receipts("youtube", "youtube", receipts)
    if ok < MIN_OK_TERMS:
        sys.exit(1)


if __name__ == "__main__":
    main()
