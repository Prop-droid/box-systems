#!/usr/bin/env bash
# Post markdown into the fleet Telegram group under a named topic, AS a fleet bot.
# Usage: tg-post.sh <topic-name> <instance> [file]    (stdin if no file)
# instance = tg-dev-bot | tg-ea-bot | tg-creative-bot | tg-coach-bot | tg-qa-bot
# Topic is auto-created (cached in lib/.tg-topics) and OWNERSHIP is registered in
# dev-bot/tg_topics.json, so Tomas's replies in that topic dispatch the posting
# bot's executor. Posts are appended to dev-bot/tg_archive/ for agent recall.
# Telegram-only rule (Tomas 2026-08-31): this replaces discord-post.sh.
set -uo pipefail
TOPIC_NAME="${1:?topic name}"; INSTANCE="${2:?instance}"; FILE="${3:-}"
ENV_FILE="$HOME/systems/$INSTANCE/.env"
[ -f "$ENV_FILE" ] || { echo "tg-post: $ENV_FILE missing" >&2; exit 2; }
TMP=""
if [ -z "$FILE" ]; then TMP="$(mktemp)"; cat > "$TMP"; FILE="$TMP"; fi
trap '[ -n "$TMP" ] && rm -f "$TMP"' EXIT

TOPIC_NAME="$TOPIC_NAME" INSTANCE="$INSTANCE" FILE="$FILE" ENV_FILE="$ENV_FILE" \
python3 - <<'PY'
import fcntl, json, os, sys, time, urllib.parse, urllib.request

env = dict(l.split("=", 1) for l in open(os.environ["ENV_FILE"])
           if "=" in l and not l.startswith("#"))
tok = env.get("TELEGRAM_TOKEN", "").strip()
chat = env.get("CHAT_ID", "").strip()
if not tok or not chat:
    print("tg-post: TELEGRAM_TOKEN/CHAT_ID missing", file=sys.stderr); sys.exit(2)
name, inst = os.environ["TOPIC_NAME"], os.environ["INSTANCE"]
text = open(os.environ["FILE"]).read().strip()
if not text:
    print("tg-post: empty body", file=sys.stderr); sys.exit(2)


def api(method, **params):
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}",
                                 data=urllib.parse.urlencode(params).encode())
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    if not d.get("ok"):
        raise RuntimeError(f"{method}: {d.get('description')}")
    return d["result"]


def locked_json(path, mutate):
    open(path, "a").close()
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            data = json.loads(f.read() or "{}")
        except ValueError:
            data = {}
        out = mutate(data)
        f.seek(0); f.truncate(); f.write(json.dumps(data, indent=1))
    return out


home = os.path.expanduser("~")
cache = f"{home}/systems/lib/.tg-topics"
tid = locked_json(cache, lambda d: d.get(chat, {}).get(name))
if not tid:
    tid = api("createForumTopic", chat_id=chat, name=name[:128])["message_thread_id"]
    locked_json(cache, lambda d: d.setdefault(chat, {}).__setitem__(name, tid))
    # replies in this topic should dispatch OUR executor, not the default owner
    locked_json(f"{home}/systems/dev-bot/tg_topics.json",
                lambda d: d.setdefault(f"{chat}:{tid}", inst))

chunks, cur = [], ""
for line in text.splitlines(True):
    if len(cur) + len(line) > 4000:
        chunks.append(cur); cur = ""
    while len(line) > 4000:
        chunks.append(line[:4000]); line = line[4000:]
    cur += line
if cur:
    chunks.append(cur)
for n, chunk in enumerate(chunks):
    api("sendMessage", chat_id=chat, message_thread_id=tid, text=chunk)
    print(f"posted {n + 1}/{len(chunks)} topic={name}")
    if n + 1 < len(chunks):
        time.sleep(1)
# archive for agent recall / fresh-session context
os.makedirs(f"{home}/systems/dev-bot/tg_archive", exist_ok=True)
with open(f"{home}/systems/dev-bot/tg_archive/{chat}.jsonl", "a") as f:
    f.write(json.dumps({"ts": int(time.time()), "chat": int(chat), "thread": tid,
                        "mid": 0, "from": f"bot:{inst}", "text": text[:4000],
                        "topic": name}, ensure_ascii=False) + "\n")
PY
