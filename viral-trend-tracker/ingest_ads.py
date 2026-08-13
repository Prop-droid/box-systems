#!/usr/bin/env python3
"""VTT ads lane (no new scraping). Daily ad-heat per watchlist term = sum of
variant_count across competitor ads (today's Atria pull) whose creative text
carries the term — i.e. how hard rivals are already pushing that concept.
Writes source="ads". Run: python3 ingest_ads.py
Exit 1 unless the Atria pull was found (empty = FAILURE).
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from vtt_common import load_watchlist, write_merged

ATRIA_DIR = Path(os.environ.get("ATRIA_DIR", "/home/tomas/brain/projects/2026-06/competitor-ads-scrape/atria"))


def latest_atria():
    files = sorted(ATRIA_DIR.glob("atria-swipe-*-gr-ns-plus10.jsonl"))
    return files[-1] if files else None


def term_words(term):
    return [w for w in re.sub(r"[^a-z0-9 ]", " ", term.lower()).split() if len(w) >= 4]


def main():
    src = latest_atria()
    if not src:
        sys.exit("no Atria daily pull found")
    ads = []
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (str(r.get("title", "")) + " " + str(r.get("body", ""))).lower()
        ads.append((text, int(r.get("variant_count", 0) or 0)))

    today = date.today().isoformat()
    rows, ok = [], 0
    for t in load_watchlist():
        words = term_words(t)
        if not words:
            continue
        heat, matches = 0, 0
        for text, vc in ads:
            if all(w in text for w in words):
                heat += vc
                matches += 1
        rows.append({"date": today, "source": "ads", "platform": "meta",
                     "term": t, "value": heat, "posts": matches})
        if matches > 0:
            ok += 1
        print(f"{t}: ad-heat={heat} ({matches} ads)", file=sys.stderr)
    write_merged("ads", "meta", rows, ok)
    # ads lane can legitimately be sparse (rivals may not run a given concept);
    # only fail if the whole Atria pull was empty/unreadable.
    if not ads:
        sys.exit(1)


if __name__ == "__main__":
    main()
