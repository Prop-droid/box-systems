#!/usr/bin/env python3
"""Pull all saved posts from Instagram (all-posts collection) via the web private API.
Reads cookies.json (sessionid/ds_user_id/csrftoken). Writes saved_raw.jsonl (one
media per line, flattened fields) and prints a summary.
"""
import json, time, urllib.request, urllib.error, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(os.path.join(DIR, "cookies.json")))
COOKIE = "; ".join(f"{k}={v}" for k, v in c.items())
HDRS = {
    "x-ig-app-id": "936619743392459",
    "x-csrftoken": c.get("csrftoken", ""),
    "cookie": COOKIE,
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "referer": "https://www.instagram.com/tomas.saltis/saved/all-posts/",
    "x-requested-with": "XMLHttpRequest",
}
TYPE = {1: "image", 2: "video", 8: "carousel"}


def get(max_id):
    url = "https://www.instagram.com/api/v1/feed/saved/posts/?count=50"
    if max_id:
        url += "&max_id=" + urllib.parse.quote(max_id)
    req = urllib.request.Request(url, headers=HDRS)
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(5 * (attempt + 1)); continue
            raise
    raise RuntimeError("too many retries")


import urllib.parse  # noqa: E402

def flatten(media):
    m = media
    cap = (m.get("caption") or {})
    vv = m.get("video_versions") or []
    return {
        "code": m.get("code"),
        "pk": str(m.get("pk", "")),
        "type": TYPE.get(m.get("media_type"), m.get("media_type")),
        "url": f"https://www.instagram.com/p/{m.get('code')}/",
        "user": (m.get("user") or {}).get("username"),
        "user_full": (m.get("user") or {}).get("full_name"),
        "caption": cap.get("text", "") if cap else "",
        "like_count": m.get("like_count"),
        "play_count": m.get("play_count") or m.get("view_count"),
        "taken_at": m.get("taken_at"),
        "video_url": vv[0].get("url") if vv else None,
        "is_video": bool(vv) or m.get("media_type") == 2,
    }


def main():
    out = open(os.path.join(DIR, "saved_raw.jsonl"), "w")
    seen, max_id, page = set(), None, 0
    while True:
        d = get(max_id)
        items = d.get("items", [])
        page += 1
        for it in items:
            m = it.get("media") or it
            code = m.get("code")
            if not code or code in seen:
                continue
            seen.add(code)
            out.write(json.dumps(flatten(m), ensure_ascii=False) + "\n")
        print(f"page {page}: +{len(items)} (total {len(seen)})", file=sys.stderr)
        max_id = d.get("next_max_id") or d.get("max_id")
        if not d.get("more_available") or not max_id:
            break
        time.sleep(1.5)
    out.close()
    print(f"DONE: {len(seen)} saved posts -> saved_raw.jsonl")


if __name__ == "__main__":
    main()
