#!/usr/bin/env bash
# Pull Wispr Flow call text from the Mac to the box. Read-only on the Mac. No audio.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RAW="${WISPR_CALLS_DIR:-$HOME/.local/share/wispr-calls}/raw"
mkdir -p "$RAW"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
ssh -o ConnectTimeout=8 -o BatchMode=yes mac 'python3 -' < "$HERE/export_mac.py" > "$TMP"
python3 -I - "$TMP" "$RAW" <<'PY'
import sys, json, os
src, raw = sys.argv[1], sys.argv[2]
n = new = 0
for line in open(src, encoding="utf-8"):
    m = json.loads(line); n += 1
    p = os.path.join(raw, m["id"] + ".json")
    body = json.dumps(m, ensure_ascii=False, indent=1)
    if not os.path.exists(p) or open(p, encoding="utf-8").read() != body:
        open(p, "w", encoding="utf-8").write(body); new += 1
print(f"calls={n} written={new} dir={raw}")
PY
