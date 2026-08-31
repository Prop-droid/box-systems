#!/usr/bin/env bash
# Post markdown to a Discord channel as one of the fleet bots (chunked at 1900).
# Usage: discord-post.sh <channel_id> <TOKEN_VAR> [file]   (stdin if no file)
# TOKEN_VAR = env var name in ~/agentic-os/discord/bots.env (e.g. CREATIVE_TOKEN,
# DEV_TOKEN). Unlike discord-notify.sh (webhook -> #ops-log alerts), this speaks
# AS a bot into working channels, so replies land where the channel agent reads.
set -uo pipefail
CH="${1:?channel id}"; VAR="${2:?token var}"; FILE="${3:-}"
BOTS_ENV="$HOME/agentic-os/discord/bots.env"
[ -f "$BOTS_ENV" ] || { echo "discord-post: $BOTS_ENV missing" >&2; exit 2; }
# Buffer stdin to a file: the python heredoc below owns the real stdin.
TMP=""
if [ -z "$FILE" ]; then
  TMP="$(mktemp)"; cat > "$TMP"; FILE="$TMP"
fi
trap '[ -n "$TMP" ] && rm -f "$TMP"' EXIT

CH="$CH" VAR="$VAR" FILE="$FILE" BOTS_ENV="$BOTS_ENV" python3 - <<'PY'
import json, os, re, sys, time, urllib.request
m = re.search(rf"^{os.environ['VAR']}=(\S+)", open(os.environ["BOTS_ENV"]).read(), re.M)
if not m or not m.group(1):
    print(f"discord-post: {os.environ['VAR']} not set in bots.env", file=sys.stderr); sys.exit(2)
tok, ch = m.group(1), os.environ["CH"]
text = open(os.environ["FILE"]).read().strip()
if not text:
    print("discord-post: empty body", file=sys.stderr); sys.exit(2)
chunks, cur = [], ""
for line in text.splitlines(True):
    if len(cur) + len(line) > 1900:
        chunks.append(cur); cur = ""
    cur += line
chunks.append(cur)
for n, chunk in enumerate(chunks):
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{ch}/messages",
        data=json.dumps({"content": chunk}).encode(), method="POST",
        headers={"Authorization": f"Bot {tok}", "Content-Type": "application/json",
                 # Discord 403s the default Python-urllib UA
                 "User-Agent": "box-discord-post/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode() or "{}")
    print(f"posted {n+1}/{len(chunks)} id={d.get('id')}")
    if n + 1 < len(chunks):
        time.sleep(1)
PY
