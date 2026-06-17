#!/bin/bash
# memguard: every 15 min, watch total node-family memory; notify on WARN,
# reap ORPHANED claude/MCP session processes on KILL threshold.
# Born from the 2026-06-11 double system crash: 70 node procs / 27 GB on 18 GB RAM
# (parallel claude sessions + MCP sidecars during ClickUp autofill work).
# Installed via launchd (com.tomas.memguard.plist, StartInterval 900).
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

WARN_GB="${MEMGUARD_WARN_GB:-8}"     # notify above this total
KILL_GB="${MEMGUARD_KILL_GB:-12}"    # reap orphans above this total
LOG_DIR="$HOME/Library/Logs/memguard"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/memguard.log"

# node-family processes: node binaries + claude-agent-sdk 'claude' binary
# Excludes Electron helpers (Claude.app / Chrome) — they're managed by their apps.
snapshot() {
  ps -axo pid,ppid,rss,etime,command \
    | grep -E '([ /])node( |$)|claude-agent-sdk[^ ]*/claude' \
    | grep -vE 'Helper|Chrome|\.app/|grep -E' || true
}

SNAP="$(snapshot)"
COUNT=$(printf '%s\n' "$SNAP" | grep -c . || true)
TOTAL_KB=$(printf '%s\n' "$SNAP" | awk '{s+=$3} END{print s+0}')
TOTAL_GB=$(awk -v k="$TOTAL_KB" 'BEGIN{printf "%.1f", k/1048576}')

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >>"$LOG"; }

over() { awk -v t="$TOTAL_GB" -v l="$1" 'BEGIN{exit !(t+0 > l+0)}'; }

if ! over "$WARN_GB"; then
  # healthy — log a heartbeat line only (keeps watchdog freshness check happy)
  log "OK node=$COUNT total=${TOTAL_GB}GB"
  # trim log to last 2000 lines
  tail -n 2000 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  exit 0
fi

log "WARN node=$COUNT total=${TOTAL_GB}GB (warn>${WARN_GB})"
osascript -e "display notification \"$COUNT node procs using ${TOTAL_GB} GB\" with title \"memguard: high node memory\" sound name \"Basso\"" 2>/dev/null || true

if over "$KILL_GB"; then
  # Reap ORPHANS only: ppid=1 claude-session trees whose parent terminal/session
  # died. Never touch: happy daemon, hermes gateway/bridge, anything non-orphan.
  REAPED=0
  while read -r pid ppid rss _etime cmd; do
    [ "$ppid" = "1" ] || continue
    case "$cmd" in
      *"daemon start-sync"*|*hermes*|*whatsapp-bridge*) continue ;;
      *claude_local_launcher*|*claude-agent-sdk*|*"happy/dist/index.mjs claude"*|*actors-mcp-server*|*perplexity-user-mcp*|*"codex mcp-server"*)
        log "KILL pid=$pid rss=$((rss/1024))MB cmd=${cmd:0:120}"
        kill "$pid" 2>/dev/null && REAPED=$((REAPED+1))
        ;;
    esac
  done <<<"$SNAP"
  sleep 5
  SNAP2="$(snapshot)"
  TOTAL2=$(printf '%s\n' "$SNAP2" | awk '{s+=$3} END{printf "%.1f", (s+0)/1048576}')
  log "REAPED $REAPED orphans; total now ${TOTAL2}GB"
  osascript -e "display notification \"reaped $REAPED orphans, ${TOTAL2} GB now (was ${TOTAL_GB})\" with title \"memguard: reaper ran\" sound name \"Basso\"" 2>/dev/null || true
fi
exit 0
