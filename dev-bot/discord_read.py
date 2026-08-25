#!/usr/bin/env python3
"""Read Agentic OS Discord history from the box — for agent sessions that need
context from another channel or thread ("read between channels and threads").

Usage:
  discord_read.py list                    # ALL channels (text/forum) + ALL threads (active + archived)
  discord_read.py <name-or-id> [limit]    # last N messages (default 30), oldest first

Name matching is case-insensitive substring over channel and thread names.
Token: Developer bot (~/systems/dev-bot/.env, has Administrator). Read-only.
Discord REST from urllib needs a real User-Agent or Cloudflare 403s (error 1010).
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GUILD_ID = 1515766239228723410
ENV = Path(__file__).resolve().parent / ".env"
API = "https://discord.com/api/v10"


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("DISCORD_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("DISCORD_TOKEN missing in dev-bot/.env")


def get(path: str, _tries: int = 4):
    req = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bot {token()}",
        "User-Agent": "DiscordBot (box, 1.0)",
    })
    for attempt in range(_tries):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _tries - 1:
                time.sleep(float(e.headers.get("Retry-After") or 2) + 0.5)
                continue
            raise


def targets(include_archived: bool = True) -> list[dict]:
    """All channels + all threads (active AND archived), each {'id', 'name', 'kind'}."""
    out, seen = [], set()

    def add(cid, name, kind):
        if cid not in seen:
            seen.add(cid)
            out.append({"id": cid, "name": name, "kind": kind})

    chans = get(f"/guilds/{GUILD_ID}/channels")
    for c in chans:
        if c.get("type") in (0, 5, 15, 16):  # text / announcement / forum / media
            add(c["id"], c["name"], "channel" if c["type"] in (0, 5) else "forum")
    for t in get(f"/guilds/{GUILD_ID}/threads/active").get("threads", []):
        add(t["id"], t["name"], "thread")
    if include_archived:
        for c in chans:
            if c.get("type") not in (0, 5, 15, 16):
                continue
            try:
                arch = get(f"/channels/{c['id']}/threads/archived/public?limit=100")
                for t in arch.get("threads", []):
                    add(t["id"], t["name"], "archived")
            except Exception:
                pass  # channel without thread support / missing history perm
    return out


def show(chan_id: str, limit: int):
    msgs = get(f"/channels/{chan_id}/messages?limit={min(limit, 100)}")
    for m in reversed(msgs):
        txt = " ".join((m.get("content") or "").split())
        if not txt or txt.startswith(("⏳", "☑", "◻", "▸", "-#")):
            continue  # live status boards
        author = m["author"].get("global_name") or m["author"]["username"]
        stamp = m["timestamp"][:16].replace("T", " ")
        print(f"[{stamp}] {author}: {txt[:600]}")
        for a in m.get("attachments", []):
            print(f"    (attachment: {a['filename']})")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__.strip())
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    if query.isdigit():  # direct id: skip the (expensive) target listing entirely
        show(query, limit)
        return
    ts = targets()
    if query == "list":
        for t in ts:
            print(f"{t['kind']:7}  {t['id']}  {t['name']}")
        return
    hits = [t for t in ts if query.lower() in t["name"].lower()]
    exact = [t for t in hits if t["name"].lower() == query.lower().lstrip("#")]
    if exact:
        hits = exact
    if not hits:
        sys.exit(f"no channel/thread matching '{query}' — try: discord_read.py list")
    if len(hits) > 1:
        for t in hits:
            print(f"{t['kind']:7}  {t['id']}  {t['name']}", file=sys.stderr)
        sys.exit(f"ambiguous '{query}' ({len(hits)} matches above) — use the id")
    print(f"# {hits[0]['kind']} {hits[0]['name']}", file=sys.stderr)
    show(hits[0]["id"], limit)


if __name__ == "__main__":
    main()
