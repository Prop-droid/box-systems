#!/usr/bin/env python3
"""VTT lane: Amazon Best Sellers → `retail` source (.10).

Nightly top-40 of Grocery & Gourmet Food + Candy & Chocolate via the Apify
actor khadinakbar/amazon-bestsellers-scraper (M&S chart unsupported there, but
M&S is just Amazon's precomputed rank delta — our scorer derives velocity from
these nightly snapshots itself, same pattern as SCS variant growth).

Watchlist-matching only (product titles aren't trend terms — no discovery):
a term matches a title when ALL its significant words (len ≥4) appear; value =
Σ(41 - rank) across both lists, so a #1 product contributes 40. ~$0.40/night.
"""
import json
import os
import sys
import urllib.request
from datetime import date

from vtt_common import load_watchlist, write_merged

ACTOR = "khadinakbar~amazon-bestsellers-scraper"
TOKEN_FILE = os.path.expanduser("~/.config/apify/token")
MAX_ITEMS = 40
LISTS = [
    {"chartType": "bestsellers", "marketplace": "US", "categorySlug": "grocery",
     "maxItemsPerCategory": MAX_ITEMS, "includeSubcategories": False},
    {"startUrls": [{"url": "https://www.amazon.com/Best-Sellers-Grocery-Gourmet-Food-Candy-Chocolate/zgbs/grocery/16322461"}],
     "maxItemsPerCategory": MAX_ITEMS},
]


def token():
    if os.environ.get("APIFY_TOKEN"):
        return os.environ["APIFY_TOKEN"]
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    sys.exit("APIFY_TOKEN not found (env or ~/.config/apify/token)")


def run_actor(payload, tok):
    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?token={tok}&timeout=110"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=150) as r:
        return json.loads(r.read().decode())


def matches(term, title):
    words = [w for w in term.lower().split() if len(w) >= 4]
    tl = title.lower()
    return bool(words) and all(w in tl for w in words)


def main():
    tok = token()
    items = []
    for payload in LISTS:
        try:
            items.extend(run_actor(payload, tok))
        except Exception as e:  # one dead list must not kill the lane
            print(f"WARN: list failed: {e}", file=sys.stderr)
    if not items:
        sys.exit("amazon actor returned no items (empty-result trap)")
    today = date.today().isoformat()
    rows, with_data = [], 0
    for term in load_watchlist():
        value = hits = 0
        for it in items:
            if matches(term, it.get("title") or ""):
                value += MAX_ITEMS + 1 - min(it.get("rank") or MAX_ITEMS, MAX_ITEMS)
                hits += 1
        rows.append({"date": today, "source": "retail", "platform": "amazon",
                     "term": term, "value": value, "posts": hits})
        with_data += 1 if value else 0
    write_merged("retail", "amazon", rows, with_data)


if __name__ == "__main__":
    main()
