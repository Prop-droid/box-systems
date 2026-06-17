#!/bin/bash
# CCC steward: probe key API routes when the dev server is up.
# Port is auto-detected (moved 3002 -> 3000 on 2026-06-11 for the Hermes bridge).
# Skips quietly when the server isn't running — it's a dev app, not a daemon.
set -uo pipefail
WD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$WD_DIR/lib/common.sh"

BASE=""
for port in 3000 3002; do
  if curl -s -o /dev/null --max-time 3 "http://localhost:$port/api/cron-status"; then
    BASE="http://localhost:$port"
    break
  fi
done

if [ -z "$BASE" ]; then
  ok "ccc:server" "dev server not running — endpoint probes skipped"
  exit 0
fi

probe() {
  local name=$1 path=$2
  local tmp; tmp=$(mktemp)
  local code
  code=$(curl -s -o "$tmp" -w '%{http_code}' --max-time 30 "$BASE$path")
  local size; size=$(wc -c < "$tmp" | tr -d ' ')
  if [ "$code" = "200" ] && [ "$size" -gt 10 ]; then
    ok "ccc:api-$name" "200, ${size}B"
  elif [ "$code" = "200" ]; then
    warn "ccc:api-$name" "200 but near-empty body (${size}B)"
  else
    local msg; msg=$(head -c 200 "$tmp" | tr '\n' ' ')
    fail "ccc:api-$name" "HTTP $code — $msg"
  fi
  rm -f "$tmp"
}

probe cron-status   /api/cron-status
probe report-latest /api/report/latest
probe research      /api/research/insights
probe winners       /api/winners
probe swipe-atria   /api/swipe/atria
