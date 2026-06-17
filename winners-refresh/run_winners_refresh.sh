#!/bin/bash
# Weekly refresh of winners.jsonl: discover new mb-winners, enrich all, reparse slugs.
# Installed via launchd (see com.tomas.winners-refresh.plist + SETUP.md).
# Token is read from a durable file so the cron authenticates unattended.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

TOKEN_PATH="$HOME/.config/clickup/pk"
CU_DIR="/home/tomas/brain/projects/2026-05/ClickUp Connection"
LOG_DIR="$HOME/Library/Logs/winners-refresh"

mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/$TS.log"
exec >>"$LOG" 2>&1

echo "=== winners refresh $TS ==="

if [ ! -s "$TOKEN_PATH" ]; then
  echo "ERROR: ClickUp token missing/empty at $TOKEN_PATH"
  echo "Store it once with:"
  echo "  mkdir -p \"\$HOME/.config/clickup\" && printf '%s' 'pk_YOURTOKEN' > \"$TOKEN_PATH\" && chmod 600 \"$TOKEN_PATH\""
  exit 1
fi
export TOKEN_FILE="$TOKEN_PATH"

cd "$CU_DIR" || { echo "ERROR: cannot cd to ClickUp Connection folder (is Google Drive mounted?)"; exit 1; }

before=$( [ -f winners.jsonl ] && wc -l < winners.jsonl | tr -d ' ' || echo 0 )

echo "[1/3] discover new winners"; python3 discover_winners.py || { echo "FAILED: discover"; exit 1; }
echo "[2/3] enrich winners";       python3 enrich_v3.py        || { echo "FAILED: enrich";   exit 1; }
echo "[3/3] reparse slugs";        python3 reparse_v3.py       || { echo "FAILED: reparse";  exit 1; }

after=$(wc -l < winners.jsonl | tr -d ' ')
echo "=== done $TS — winners.jsonl ${before} -> ${after} lines ==="
