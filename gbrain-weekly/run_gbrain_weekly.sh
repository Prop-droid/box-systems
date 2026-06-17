#!/bin/bash
# Weekly gbrain maintenance: refresh stale embeddings + capped auto-remediation.
# Mondays 10:00 via com.tomas.gbrain-weekly. Autopilot NOT installed by design:
# this brain is DB-only (pglite, no git repo), and autopilot's sync phase needs a repo.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.bun/bin:$HOME/.local/bin:$PATH"
LOG_DIR="$HOME/Library/Logs/gbrain-weekly"
mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
exec >>"$LOG_DIR/$TS.log" 2>&1

echo "=== gbrain weekly $TS ==="
export GEMINI_API_KEY=$(grep -E "^GEMINI_API_KEY=" $HOME/.hermes/.env | cut -d= -f2-); export GOOGLE_API_KEY=$(grep -E "^GOOGLE_API_KEY=" $HOME/.hermes/.env | cut -d= -f2-)
command -v gbrain >/dev/null || { echo "ERROR: gbrain not on PATH"; exit 1; }

echo "--- health before ---"
gbrain health 2>/dev/null | head -20

echo "--- embed stale ---"
gbrain embed --stale 2>&1 | tail -5

echo "--- doctor remediate (capped \$5) ---"
gbrain doctor --remediate --yes --target-score 80 --max-usd 5 2>&1 | tail -20

echo "--- health after ---"
gbrain health 2>/dev/null | head -20
echo "=== done $TS ==="

# keep last 12 logs
ls -t "$LOG_DIR"/*.log | tail -n +13 | xargs rm -f 2>/dev/null || true
