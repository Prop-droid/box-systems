#!/usr/bin/env bash
# VTT nightly ingest — all lanes, sequentially. One lane failing must not block
# the others; the job is red only if EVERY lane failed. Timers get no login env,
# so export PATH (tw/rdt/yt-dlp live in ~/.local/bin) and VTT_DIR here.
set -uo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/usr/bin:/bin"
export VTT_DIR="${VTT_DIR:-$HOME/brain/projects/2026-08/viral-trend-tracker}"

ok=0
lanes="ingest_tiktok ingest_reddit ingest_x ingest_youtube ingest_ads ingest_trends"
# Amazon lane is MONTHLY (1st of the month): nightly runs (~$0.40 each) ate the
# whole $5 Apify free-tier credit and killed the TikTok lane too (Tomas 2026-09-07).
[ "$(date +%d)" = "01" ] && lanes="$lanes ingest_amazon"
total=$(echo $lanes | wc -w)
for lane in $lanes; do
  echo "== $lane =="
  if timeout 900 python3 "$lane.py"; then
    ok=$((ok + 1))
  else
    echo "$lane FAILED (rc=$?)"
  fi
done
echo "VTT ingest: $ok/$total lanes ok"
[ "$ok" -ge 1 ] && exit 0 || exit 1
