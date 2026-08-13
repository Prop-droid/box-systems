#!/usr/bin/env python3
"""Re-seed twitter-cli's x-client-transaction cache (browser-free).

twitter-cli's ClientTransaction init fetches x.com ANONYMOUSLY, but the
logged-out shell no longer carries the ondemand-JS reference the regex needs,
so init throws `'NoneType' has no attribute 'group'` and every call 404s. The
cache (~/.twitter-cli/transaction_cache.json, 1h TTL) is the only path that
works — so we seed it from the LOGGED-IN homepage using the auth cookies +
curl_cffi (same Chrome TLS fingerprint the CLI uses). No browser needed.

Run standalone or via the ad-rank-neighbour timer every 45 min to stay <1h.
Must run under the twitter-cli venv python (has curl_cffi + x_client_transaction).
"""
import json
import os
import sys
import time

CACHE = os.path.expanduser("~/.twitter-cli/transaction_cache.json")
COOKIES = os.path.expanduser("~/systems/ig-ingest/xr_cookies.json")
FRESH_SECONDS = 45 * 60  # reseed only if older than this

def fresh() -> bool:
    try:
        return time.time() - json.load(open(CACHE)).get("created_at", 0) < FRESH_SECONDS
    except Exception:
        return False

def main():
    if "--force" not in sys.argv and fresh():
        return
    from curl_cffi import requests as cffi
    from x_client_transaction.utils import get_ondemand_file_url, generate_headers
    import bs4

    jar = json.load(open(COOKIES))["x"]
    s = cffi.Session(impersonate="chrome")
    for k, v in jar.items():
        s.cookies.set(k, v, domain=".x.com")
    h = generate_headers()
    home = s.get("https://x.com/home", headers=h, timeout=15)
    soup = bs4.BeautifulSoup(home.content, "html.parser")
    url = get_ondemand_file_url(response=soup)
    od = s.get(url, headers=h, timeout=15)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump({"home_html": home.text, "ondemand_text": od.text, "created_at": time.time()},
              open(CACHE, "w"))
    print(f"CT cache seeded ({len(home.text)}B home, ondemand {od.status_code})", file=sys.stderr)

if __name__ == "__main__":
    main()
