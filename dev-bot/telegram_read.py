#!/usr/bin/env python3
"""Cross-chat/topic recall over the Telegram archive — discord_read.py's sibling.

The Bot API has no history endpoint, so this reads ~/systems/dev-bot/tg_archive/
(written live by every telegram bot instance: inbound human messages, outbound
bot replies, topic creations). Inbound lines are deduped by (chat, mid) since
all bots in one group archive the same messages.

Usage:
  telegram_read.py list                  # chats + topics seen, with counts
  telegram_read.py <chat-or-topic> [N]   # last N messages (default 30)
"""
import json
import sys
import time
from pathlib import Path

ARCHIVE_DIR = Path(__file__).resolve().parent / "tg_archive"


def load():
    chats = {}  # chat_id -> {"topics": {thread_id: name}, "msgs": [rec]}
    for f in sorted(ARCHIVE_DIR.glob("*.jsonl")):
        cid = f.stem
        c = chats.setdefault(cid, {"topics": {}, "msgs": [], "seen": set()})
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if r.get("topic"):
                c["topics"][r.get("thread")] = r["topic"]
            key = (r.get("mid"), r.get("from"))
            if r.get("mid") and key in c["seen"]:
                continue
            c["seen"].add(key)
            c["msgs"].append(r)
    return chats


def fmt(r, topics):
    ts = time.strftime("%m-%d %H:%M", time.localtime(r.get("ts", 0)))
    label = topics.get(r.get("thread"))
    where = f" [{label}]" if label else ""
    text = " ".join(str(r.get("text", "")).split())[:500]
    return f"{ts} {r.get('from', '?')}{where}: {text}"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__.strip())
    chats = load()
    if sys.argv[1] == "list":
        if not chats:
            print("(archive empty — it fills as messages flow)")
        for cid, c in chats.items():
            kind = "DM" if int(cid) > 0 else "group"
            print(f"{cid}  ({kind}, {len(c['msgs'])} msgs)")
            for tid, name in sorted(c["topics"].items(), key=lambda x: x[0] or 0):
                n = sum(1 for m in c["msgs"] if m.get("thread") == tid)
                print(f"  topic {tid}  {name}  ({n} msgs)")
        return
    target, limit = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30
    tl = target.lower()
    for cid, c in chats.items():
        # whole chat by id
        if cid == target or cid.lstrip("-") == target.lstrip("-"):
            for r in c["msgs"][-limit:]:
                print(fmt(r, c["topics"]))
            return
        # topic by id or name substring
        for tid, name in c["topics"].items():
            if str(tid) == target or tl in name.lower():
                msgs = [m for m in c["msgs"] if m.get("thread") == tid]
                for r in msgs[-limit:]:
                    print(fmt(r, c["topics"]))
                return
    sys.exit(f"no chat or topic matching {target!r} — try: telegram_read.py list")


if __name__ == "__main__":
    main()
