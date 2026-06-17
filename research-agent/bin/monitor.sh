#!/bin/bash
# Research agent — competitor monitor (Phase 2).
# Cheap, NO-LLM. Pulls active competitor ads via the Atria skill, diffs ad IDs
# against last-seen state, and appends NEW ads to the feed the /research tab reads.
# Also rebuilds watchlist.json from the live followed-brand list.
#
# Manual run:  bash monitor.sh
# Scheduled via ~/Library/LaunchAgents/com.tomas.research-monitor.plist
# See ./README.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive"
CT="/home/tomas/brain"

RESEARCH_DIR="${RESEARCH_DIR:-/home/tomas/brain/systems/research-agent/output}"
ATRIA_SCRIPT="${ATRIA_SCRIPT:-$CT/.claude/skills/atria/scripts/atria_swipe_pull.py}"
ATRIA_OUT_DIR="${ATRIA_OUT_DIR:-$CT/projects/2026-06/competitor-ads-scrape/atria}"
export ATRIA_OUT_DIR

FEED_DIR="$RESEARCH_DIR/feed"
STATE_DIR="$RESEARCH_DIR/state"
LOGDIR="$AGENT_DIR/logs"
mkdir -p "$FEED_DIR" "$STATE_DIR" "$LOGDIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
[ -f "$HOME/.hermes/.env" ] && { set -o allexport; source "$HOME/.hermes/.env"; set +o allexport; }

# Curated brand set lives in monitor.conf (MONITOR_BRAND_IDS). Inline env wins.
if [ -f "$AGENT_DIR/monitor.conf" ]; then
  _env_ids="${MONITOR_BRAND_IDS:-}"
  set -o allexport; source "$AGENT_DIR/monitor.conf"; set +o allexport
  [ -n "$_env_ids" ] && MONITOR_BRAND_IDS="$_env_ids"
fi

TODAY="$(date +%F)"
LOG="$LOGDIR/monitor-$TODAY.log"
exec > >(tee -a "$LOG") 2>&1
TEE_PID=$!
# Close stdout/stderr on exit so tee gets EOF, then wait — otherwise the last
# log lines race the shell exit and vanish from the log.
trap 'exec 1>&- 2>&-; [ -n "${TEE_PID:-}" ] && wait "$TEE_PID" 2>/dev/null || true' EXIT

echo "=================================================="
echo "[$(date)] competitor monitor"
echo "=================================================="

command -v python3 >/dev/null || { echo "FAIL: python3 not on PATH"; exit 2; }
[ -f "$ATRIA_SCRIPT" ] || { echo "FAIL: atria script not found at $ATRIA_SCRIPT"; exit 2; }

# 1) Pull fresh active ads (writes atria-swipe-<date>.jsonl into ATRIA_OUT_DIR).
#    MONITOR_BRAND_IDS = space-separated Atria brand ids to watch ONLY those
#    (e.g. "m107585658730958 m112448499199569"). Unset = all followed brands.
echo ">> atria pull ${MONITOR_BRAND_IDS:+(brands: $MONITOR_BRAND_IDS)} ..."
if ! python3 "$ATRIA_SCRIPT" ${MONITOR_BRAND_IDS:-} >>"$LOG" 2>&1; then
  echo "FAIL: atria pull errored (see log). Aborting without touching state."
  exit 3
fi

# 2) Find the newest swipe JSONL
LATEST="$(ls -t "$ATRIA_OUT_DIR"/atria-swipe-*.jsonl 2>/dev/null | head -1 || true)"
[ -n "${LATEST:-}" ] || { echo "FAIL: no atria-swipe JSONL produced."; exit 3; }
echo "   latest: $(basename "$LATEST")"

# 3) Diff against seen-state, emit NEW ads to feed, rebuild watchlist, update status
python3 - "$LATEST" "$STATE_DIR/atria_seen.json" "$FEED_DIR/$(date +%Y-%m).jsonl" \
         "$RESEARCH_DIR/watchlist.json" "$STATE_DIR/status.json" <<'PY'
import sys, json, os, pathlib
from datetime import datetime, timezone

latest, seen_path, feed_path, watch_path, status_path = sys.argv[1:6]
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

ads = []
for line in open(latest, encoding="utf-8"):
    line = line.strip()
    if line:
        try: ads.append(json.loads(line))
        except Exception: pass

def ad_key(a):
    return a.get("platform_native_id") or a.get("id")

seen = set()
first_run = not os.path.exists(seen_path)
if not first_run:
    try: seen = set(json.load(open(seen_path)))
    except Exception: seen = set()

new_ads = [a for a in ads if ad_key(a) and ad_key(a) not in seen]

# --- emit feed entries ---
def feed_item(a):
    media = a.get("media_urls") or []
    title = (a.get("title") or a.get("body") or "").strip()[:120] or "(no copy)"
    angles = ", ".join(a.get("angles") or []) or "untagged"
    return {
        "id": f"atria-{ad_key(a)}",
        "date": now,
        "source": f"atria:{(a.get('brand_name') or 'brand').lower().replace(' ','-')}",
        "type": "new_ad",
        "severity": "notable" if a.get("winning_lane") else "info",
        "title": f"New {a.get('brand_name','competitor')} ad: {title}",
        "summary": f"Angles: {angles}. Running {a.get('variant_count',1)} creator/code variant(s). Format {a.get('format','?')}.",
        "url": a.get("ad_library_url") or a.get("link_url") or "",
        "thumbnail": media[0] if media else "",
    }

emitted = 0
with open(feed_path, "a", encoding="utf-8") as f:
    if first_run:
        # Baseline: don't flood the feed with every active ad. One summary note.
        brands = sorted({a.get("brand_name") for a in ads if a.get("brand_name")})
        f.write(json.dumps({
            "id": f"monitor-baseline-{now}", "date": now, "source": "monitor",
            "type": "note", "severity": "info",
            "title": f"Monitor baseline set: {len(ads)} active ads across {len(brands)} brands",
            "summary": "First monitor run. Recorded current ads as the baseline. From now on only NEW ads are reported. Brands: " + ", ".join(brands),
            "url": "", "thumbnail": "",
        }, ensure_ascii=False) + "\n")
        emitted = 1
    else:
        # Per-brand flood guard: a brand arriving with a pile of "new" ads is
        # either newly added to the monitor or mass-launching — both read better
        # as one summary item than as dozens of cards.
        PER_BRAND_CAP = 5
        by_brand = {}
        for a in new_ads:
            by_brand.setdefault(a.get("brand_name") or "?", []).append(a)
        for bname, group in by_brand.items():
            if len(group) > PER_BRAND_CAP:
                winning = sum(1 for a in group if a.get("winning_lane"))
                f.write(json.dumps({
                    "id": f"atria-bulk-{bname.lower().replace(' ','-')}-{now}",
                    "date": now, "source": f"atria:{bname.lower().replace(' ','-')}",
                    "type": "note", "severity": "notable" if winning else "info",
                    "title": f"{bname}: {len(group)} new ads in one day",
                    "summary": f"Bulk arrival ({winning} in winning lanes) — newly monitored brand or a mass launch. See the swipe tab for the full set.",
                    "url": "", "thumbnail": "",
                }, ensure_ascii=False) + "\n")
                emitted += 1
            else:
                for a in group:
                    f.write(json.dumps(feed_item(a), ensure_ascii=False) + "\n")
                    emitted += 1

# --- update seen state (all current keys) ---
all_keys = sorted({ad_key(a) for a in ads if ad_key(a)})
def write_atomic(path, obj, **kw):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, **kw)
    os.replace(tmp, path)
write_atomic(seen_path, all_keys)

# --- rebuild watchlist.json from live brands ---
from collections import Counter, defaultdict
brand_counts = Counter(a.get("brand_name") for a in ads if a.get("brand_name"))
brand_new = Counter(a.get("brand_name") for a in new_ads if a.get("brand_name"))
watch = []
for bname, n in sorted(brand_counts.items(), key=lambda x: -x[1]):
    nn = brand_new.get(bname, 0)
    if first_run:
        result = f"{n} active (baseline)"
    elif nn:
        result = f"{nn} new"
    else:
        result = f"{n} active, no change"
    watch.append({
        "source": f"atria:{bname.lower().replace(' ','-')}",
        "label": f"{bname} (Atria)", "type": "competitor-ads",
        "cadence": "daily", "enabled": True, "last_checked": now,
        "last_result": result,
    })
write_atomic(watch_path, watch, ensure_ascii=False, indent=2)

# --- update status.json ---
status = {}
if os.path.exists(status_path):
    try: status = json.load(open(status_path))
    except Exception: status = {}
status["last_monitor_run"] = now
status["monitors_ok"] = True
status.pop("note", None)
write_atomic(status_path, status, indent=2)

print(f"ads={len(ads)} new={len(new_ads)} emitted_feed={emitted} first_run={first_run}")
PY

echo "[$(date)] monitor DONE"
