"""Air unique-creative counter. Creds at ~/.config/air/{api_key,workspace_id}. Proven on S42/S43."""
import json, sys, re, urllib.request, os, urllib.parse
def _hdr():
    K = open(os.path.expanduser('~/.config/air/api_key')).read().strip(); W = open(os.path.expanduser('~/.config/air/workspace_id')).read().strip()
    return {"x-api-key": K, "x-air-workspace-id": W}
def get(url): return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=_hdr()), timeout=60))
def assets(bid):
    out = []; cur = None
    while True:
        u = f"https://api.air.inc/v1/assets?parentBoardId={bid}&includeNestedAssets=true&limit=100" + (f"&cursor={urllib.parse.quote(cur)}" if cur else "")
        d = get(u); out += d.get('data', []); cur = (d.get('pagination') or {}).get('cursor') or d.get('cursor')
        if not cur or not d.get('data'): break
    return out
def stem(n):
    n = re.sub(r'\.[A-Za-z0-9]{2,4}$', '', n)
    n = re.sub(r'[_-]?(VID|IMG)?-?\d{3,4}x\d{3,4}', '', n, flags=re.I)
    n = re.sub(r'[_-](FEED|REELS?|STORY|STORIES|SQUARE|VERTICAL|HORIZONTAL|4X5|9X16|1X1|16X9|APPLOVIN|THUMB(NAIL)?)\b', '', n, flags=re.I)
    return n.strip('_- ').lower()
def count(sid):
    sh = json.load(urllib.request.urlopen(f"https://api.air.inc/shorturl/{sid}", timeout=60))
    if sh.get('type') == 'asset':
        t = sh['data'].get('type', 'video')
        return {"sid": sid, "files": 1, "unique_video": 1 if t == 'video' else 0, "unique_image": 1 if t == 'image' else 0}
    a = assets(sh['data']['id'])
    names = [((x.get('coverVersion') or {}).get('fileName') or '', (x.get('coverVersion') or {}).get('type')) for x in a]
    return {"sid": sid, "files": len(a),
            "unique_video": len({stem(n) for n, t in names if t == 'video'}),
            "unique_image": len({stem(n) for n, t in names if t == 'image'})}
if __name__ == "__main__":
    for sid in sys.argv[1:]:
        try: print(json.dumps(count(sid)))
        except Exception as e: print(json.dumps({"sid": sid, "err": str(e)[:80]}))
