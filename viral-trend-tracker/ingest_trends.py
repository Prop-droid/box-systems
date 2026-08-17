#!/usr/bin/env python3
"""VTT lane: Google Trends "Trending Now" RSS (geo=US) — the `trends` source (.25).

Zero-auth discovery feed like the tiktok lane: ~20 currently-trending US search
terms with approximate traffic. Terms are unioned into the candidate pool by the
CCC loader; most are general news noise, filtered downstream by volume floors,
cross-source corroboration, and the watchlist/discovery split in the Trends tab.
value = approx_traffic ("20,000+" → 20000).
"""
import re
import sys
import urllib.request
from xml.etree import ElementTree

from vtt_common import write_merged

RSS = "https://trends.google.com/trending/rss?geo=US"
NS = {"ht": "https://trends.google.com/trending/rss"}


def main():
    req = urllib.request.Request(RSS, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ElementTree.parse(r).getroot()
    rows = []
    from datetime import date
    today = date.today().isoformat()
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip().lower()
        traffic = item.findtext("ht:approx_traffic", default="", namespaces=NS)
        value = int(re.sub(r"[^0-9]", "", traffic) or 0)
        if title and value > 0:
            rows.append({"date": today, "source": "trends", "platform": "google",
                         "term": title, "value": value, "posts": 1})
    if not rows:
        sys.exit("trends RSS returned no items (empty-result trap)")
    write_merged("trends", "google", rows, len(rows))


if __name__ == "__main__":
    main()
