#!/usr/bin/env python3
"""VTT TikTok lane (Apify data_xplorer/tiktok-trends, Creative Center). Pulls the
US Food & Beverage (27) + Health (29) trending-hashtag rankings, 7-day window,
and writes one row per hashtag: value = Video Views. Unlike the watchlist lanes,
this is a DISCOVERY feed — it surfaces viral food/health hashtags we never listed;
the CCC loader unions them as candidates (and corroborates ones that match a
watchlist term). Writes source="tiktok". Industry IDs mapped live 2026-08-13.

Run: python3 ingest_tiktok.py   Exit 1 unless >= MIN_OK hashtags returned.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date

from vtt_common import VTT_DIR, write_merged

ACTOR = "data_xplorer~tiktok-trends"
INDUSTRIES = {"27000000000": "Food & Beverage", "29000000000": "Health"}
COUNTRY = "US"
PERIOD = "7"
MAX_PER_INDUSTRY = 60
MIN_OK = 20
TOKEN_FILE = os.path.expanduser("~/.config/apify/token")


def token():
    t = os.environ.get("APIFY_TOKEN")
    if t:
        return t
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    sys.exit("APIFY_TOKEN not found (env or ~/.config/apify/token)")


def run_actor(industry_id, tok):
    url = (f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
           f"?token={tok}")
    body = json.dumps({
        "trendType": "hashtags", "countryCode": COUNTRY, "hashtagPeriod": PERIOD,
        "industryId": industry_id, "maxItems": MAX_PER_INDUSTRY,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def norm_tag(h):
    return re.sub(r"[^a-z0-9]+", " ", str(h).lstrip("#").lower()).strip()


def main():
    tok = token()
    today = date.today().isoformat()
    best = {}  # term -> row (dedupe hashtag across industries, keep higher views)
    for iid, label in INDUSTRIES.items():
        try:
            items = run_actor(iid, tok)
        except Exception as e:
            print(f"FAIL {label}: {e}", file=sys.stderr)
            continue
        for it in items:
            term = norm_tag(it.get("Hashtag", ""))
            if not term:
                continue
            views = int(it.get("Video Views") or 0)
            row = {"date": today, "source": "tiktok", "platform": "tiktok",
                   "term": term, "value": views, "posts": int(it.get("Posts") or 0),
                   "rank": it.get("Rank"), "direction": it.get("Trend Direction"),
                   "industry": label}
            if term not in best or views > best[term]["value"]:
                best[term] = row
        print(f"{label}: {len(items)} hashtags", file=sys.stderr)

    rows = list(best.values())
    write_merged("tiktok", "tiktok", rows, len(rows))
    if len(rows) < MIN_OK:
        sys.exit(1)


if __name__ == "__main__":
    main()
