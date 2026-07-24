#!/usr/bin/env python3
# Build + post the weekly leaderboard message to Tomas Pod (ClickUp chat v3).
# argv: json_path  boards_url ; env: CLICKUP_TOKEN, DRY_RUN, MSG_FILE
import json, os, sys, urllib.request

WS, CH = "9011638245", "8cj5bz5-125371"  # Tomas Pod (same channel as iteration-suggestions)

d = json.load(open(sys.argv[1]))
boards_url = sys.argv[2]

def money(v): return f"${v:,.0f}"
def line(i, r):
    nm = r.get("cre") or r.get("sh") or r["title"]
    cpa = f"${r['cpa']:,.2f}" if r.get("cpa") is not None else "-"
    cpc = f"${r['cpc']:,.2f}" if r.get("cpc") is not None else "-"
    return f"{i}. **{nm}** — spend {money(r['spend'])} · CPA {cpa} · CPC {cpc}"
def block(title, rows, n):
    rows = rows[:n]
    if not rows: return [f"**{title}**", "_none above the spend floor_", ""]
    return [f"**{title}**"] + [line(i + 1, r) for i, r in enumerate(rows)] + [""]

rg = d["ranges"]
msg = [f"🏆 **Creative Leaderboards** — week of {rg['last7']['to']}", ""]
msg += block("🎬 Top 3 videos · launched last 7 days", d["last7"]["videos"], 3)
msg += block("🖼️ Top 3 images · launched last 7 days", d["last7"]["images"], 3)
msg += block("🎬 Top 5 videos · launched last 30 days", d["last30"]["videos"], 5)
msg += block("🖼️ Top 5 images · launched last 30 days", d["last30"]["images"], 5)
msg += block(f"🏁 Quarter leaderboard · launched since {rg['quarter']['from']}", d["quarter"], 10)
msg += [f"Full boards with thumbnails and margins: {boards_url}"]
text = "\n".join(msg)

open(os.environ.get("MSG_FILE", "/dev/null"), "w").write(text)
if os.environ.get("DRY_RUN") == "1":
    print("DRY_RUN=1 — not posting"); sys.exit(0)

tok = os.environ["CLICKUP_TOKEN"]
body = json.dumps({"type": "message", "content_format": "text/md", "content": text}).encode()
req = urllib.request.Request(
    f"https://api.clickup.com/api/v3/workspaces/{WS}/chat/channels/{CH}/messages",
    data=body, method="POST",
    headers={"Authorization": tok, "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    out = json.load(r)
    print(f"posted message id={(out.get('data') or {}).get('id') or out.get('id')}")
