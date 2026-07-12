#!/usr/bin/env bash
# box-doctor — daily self-diagnostic for the agent box (task 51, wave-5).
# Checks known failure modes across the estate; ntfy digest ONLY when something
# is wrong (silent when green); writes reports/YYYY-MM-DD.md + doctor-report.md.
# Auto-fixes ONLY: dead hermes skill symlinks (skill-sync pattern) and a stale
# usage-window.json (reruns usage-guard once). Everything else is report-only.
set -uo pipefail
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

NTFY_TOPIC="${NTFY_TOPIC:-tomas-tab-958e4431}"
DOC_DIR="$HOME/systems/box-doctor"
MEM_DIR="$HOME/.claude/projects/-home-tomas/memory"
SKILLS_DIR="$HOME/.claude/skills"
HERMES_SKILLS="$HOME/.hermes/skills"
MAC_TS_IP="100.68.166.21"
DISK_WARN=80; DISK_FAIL=90
MEM_AVAIL_WARN_MB=1024
USAGE_WINDOW_MAX_MIN=30            # guard writes every 5 min; >30 min = broken
PPLX_TOKEN_WARN_DAYS=25            # session token expires ~30d
IGNORE_FAILED_UNITS='xdg-desktop-portal'  # known headless-box noise
GIT_REPOS="$HOME/systems $HOME/brain $HOME/creative-command-center"

# Stale cron outputs: newest match of glob older than max_age_hours = the job
# "succeeded" without landing its artifact (the silent zero-output mode).
# comments-digest is deliberately absent: its upstream feed is dead and it
# exits 0 on no data BY DESIGN (see ~/systems/CLAUDE.md).
STALE_OUTPUTS=$(cat <<'EOF'
$HOME/systems/watchdog/reports/latest.md|26|box-watchdog report
$HOME/brain/projects/*/sha-weekly-report/*/report.md|200|sha-weekly-report
$HOME/brain/systems/research-agent/output/state/status.json|26|research-monitor feed
$HOME/brain/projects/2026-05/ClickUp Connection/winners.jsonl|200|winners archive
$HOME/systems/agents/reports/retro/*.md|200|agents-weekly retro
EOF
)

fails=(); warns=(); fixed=(); infos=()
fail() { fails+=("$1"); }
warn() { warns+=("$1"); }
fix()  { fixed+=("$1"); }
info() { infos+=("$1"); }

# --- 1. failed systemd units (user + system) --------------------------------
for scope in "--user" "--system"; do
  while IFS= read -r u; do
    [ -n "$u" ] || continue
    echo "$u" | grep -qE "$IGNORE_FAILED_UNITS" && continue
    fail "failed unit (${scope#--}): $u"
  done < <(systemctl $scope --failed --plain --no-legend 2>/dev/null | sed 's/^[●× ]*//' | awk '{print $1}')
done

# --- 2. enabled-but-inactive user timers -------------------------------------
while IFS= read -r t; do
  t="$(basename "$t")"
  state="$(systemctl --user is-enabled "$t" 2>/dev/null || true)"
  [ "$state" = "enabled" ] || continue
  systemctl --user is-active "$t" >/dev/null 2>&1 || fail "timer enabled but INACTIVE: $t"
done < <(ls "$HOME/.config/systemd/user/"*.timer 2>/dev/null)

# --- 3. disk ------------------------------------------------------------------
duse="$(df --output=pcent / 2>/dev/null | tail -1 | tr -dc '0-9')"
if [ -n "$duse" ]; then
  if   [ "$duse" -ge "$DISK_FAIL" ]; then fail "disk / at ${duse}%"
  elif [ "$duse" -ge "$DISK_WARN" ]; then warn "disk / at ${duse}%"; fi
else warn "disk check: df failed"; fi

# --- 4. memory + earlyoom kills ------------------------------------------------
avail_mb=$(( $(awk '/MemAvailable/{print $2}' /proc/meminfo) / 1024 ))
[ "$avail_mb" -lt "$MEM_AVAIL_WARN_MB" ] && warn "low memory: ${avail_mb}MB available"
kills="$(timeout 15 journalctl -u earlyoom --since "24 hours ago" -q --no-pager 2>/dev/null | grep -ciE 'sending SIG' || true)"
[ -n "$kills" ] && [ "$kills" -gt 0 ] && warn "earlyoom killed $kills process(es) in last 24h"

# --- 5. syncthing service + conflict files in memory dir ----------------------
systemctl --user is-active syncthing.service >/dev/null 2>&1 || fail "syncthing.service INACTIVE"
while IFS= read -r c; do
  [ -n "$c" ] && warn "syncthing conflict file: ${c#$HOME/}"
done < <(find "$MEM_DIR" -name '*sync-conflict*' 2>/dev/null)

# --- 6. dead symlinks in ~/.claude/skills (AUTO-FIX for hermes-sourced) --------
# skill-sync pattern: relink to live category dir first, .archive/ fallback,
# else prune. Only touches links pointing into ~/.hermes/skills; anything else
# dead is report-only.
for l in "$SKILLS_DIR"/*; do
  [ -L "$l" ] && [ ! -e "$l" ] || continue
  name="$(basename "$l")"
  target="$(readlink "$l")"
  case "$target" in
    "$HERMES_SKILLS"/*)
      new="$(find "$HERMES_SKILLS" -maxdepth 2 -type d -name "$name" -not -path '*/.archive/*' 2>/dev/null | head -1)"
      [ -n "$new" ] || new="$(find "$HERMES_SKILLS/.archive" -maxdepth 3 -type d -name "$name" 2>/dev/null | head -1)"
      if [ -n "$new" ] && [ -f "$new/SKILL.md" ]; then
        ln -sfn "$new" "$l" && fix "skill symlink relinked: $name -> ${new#$HOME/}"
      else
        rm "$l" && fix "dead skill symlink pruned: $name (was ${target#$HOME/})"
      fi ;;
    *) warn "dead skill symlink (non-hermes, left alone): $name -> $target" ;;
  esac
done

# --- 7. tailscale --------------------------------------------------------------
if ! timeout 15 tailscale status >/dev/null 2>&1; then
  fail "tailscale DOWN"
elif timeout 15 tailscale status 2>/dev/null | grep "^$MAC_TS_IP" | grep -q offline; then
  warn "Mac tailscale peer offline (usage-guard blind to Mac spend)"
fi

# --- 8. expired-token telltales -------------------------------------------------
# Perplexity: session token lives in ~/.hermes/config.yaml, expires ~30d; the
# live telltale is the gateway logging anonymous-mode searches.
hc="$HOME/.hermes/config.yaml"
if [ -f "$hc" ]; then
  age_d=$(( ($(date +%s) - $(stat -c %Y "$hc")) / 86400 ))
  [ "$age_d" -ge "$PPLX_TOKEN_WARN_DAYS" ] && warn "perplexity session token likely expiring: hermes config.yaml untouched ${age_d}d (~30d limit)"
fi
anon="$(timeout 15 journalctl --user -u hermes-gateway --since "24 hours ago" --no-pager 2>/dev/null | grep -ci 'anonymous' || true)"
[ -n "$anon" ] && [ "$anon" -gt 0 ] && warn "perplexity in anonymous mode ($anon hits in gateway log 24h) — session token expired, re-copy from Mac Chrome"
# Google: gws token cache (work account) — token_valid from auth status.
if command -v gws >/dev/null 2>&1; then
  tv="$(timeout 20 gws auth status 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("token_valid"))' 2>/dev/null || echo err)"
  [ "$tv" = "True" ] || warn "google token: gws auth status token_valid=$tv"
fi

# --- 9. usage-guard state freshness (AUTO-FIX: rerun guard once) ----------------
uw="$HOME/.claude/usage-window.json"
uw_age_min() { echo $(( ($(date +%s) - $(stat -c %Y "$uw" 2>/dev/null || echo 0)) / 60 )); }
if [ ! -f "$uw" ] || [ "$(uw_age_min)" -gt "$USAGE_WINDOW_MAX_MIN" ]; then
  timeout 300 bash "$HOME/systems/usage-guard/guard.sh" >/dev/null 2>&1 || true
  if [ -f "$uw" ] && [ "$(uw_age_min)" -le "$USAGE_WINDOW_MAX_MIN" ]; then
    fix "usage-window.json was stale — guard.sh rerun, now fresh"
  else
    fail "usage-window.json stale (>${USAGE_WINDOW_MAX_MIN}min) and guard.sh rerun did not refresh it"
  fi
fi

# --- 10. git repos: uncommitted / unpushed --------------------------------------
for r in $GIT_REPOS; do
  n="$(basename "$r")"
  git -C "$r" rev-parse --git-dir >/dev/null 2>&1 || { info "$n: not a git repo, skipped"; continue; }
  dirty="$(git -C "$r" status --porcelain 2>/dev/null | wc -l)"
  ahead="$(git -C "$r" rev-list --count @{u}..HEAD 2>/dev/null || echo "")"
  msg=""
  [ "$dirty" -gt 0 ] && msg="$dirty uncommitted file(s)"
  [ -n "$ahead" ] && [ "$ahead" -gt 0 ] && msg="${msg:+$msg, }$ahead unpushed commit(s)"
  [ -z "$ahead" ] && info "$n: no upstream configured (unpushed check skipped)"
  [ -n "$msg" ] && warn "git $n: $msg"
done

# --- 11. stale cron outputs ------------------------------------------------------
while IFS='|' read -r glob hours label; do
  [ -n "$glob" ] || continue
  glob="${glob/\$HOME/$HOME}"
  # compgen+xargs -r: glob expansion that survives spaces in paths
  newest="$(compgen -G "$glob" | xargs -d '\n' -r ls -t 2>/dev/null | head -1)"
  if [ -z "$newest" ]; then warn "stale output: $label — no files match"; continue; fi
  age_h=$(( ($(date +%s) - $(stat -c %Y "$newest")) / 3600 ))
  [ "$age_h" -gt "$hours" ] && warn "stale output: $label — newest is ${age_h}h old (max ${hours}h): ${newest#$HOME/}"
done <<< "$STALE_OUTPUTS"

# --- report ---------------------------------------------------------------------
mkdir -p "$DOC_DIR/reports"
TS="$(date '+%Y-%m-%d %H:%M')"
REPORT="$DOC_DIR/reports/$(date +%Y-%m-%d).md"
n_bad=$(( ${#fails[@]} + ${#warns[@]} ))
{ echo "# Box Doctor — $TS"
  echo
  if [ "$n_bad" -eq 0 ]; then echo "**Status: OK** — all checks green (${#fixed[@]} auto-fix(es) applied)"
  else echo "**Status: ${#fails[@]} FAIL / ${#warns[@]} WARN** (${#fixed[@]} auto-fixed)"; fi
  [ ${#fails[@]} -gt 0 ] && { echo; echo "## FAIL"; printf -- "- 🔴 %s\n" "${fails[@]}"; }
  [ ${#warns[@]} -gt 0 ] && { echo; echo "## WARN"; printf -- "- 🟡 %s\n" "${warns[@]}"; }
  [ ${#fixed[@]} -gt 0 ] && { echo; echo "## Auto-fixed"; printf -- "- 🔧 %s\n" "${fixed[@]}"; }
  [ ${#infos[@]} -gt 0 ] && { echo; echo "## Notes"; printf -- "- %s\n" "${infos[@]}"; }
  echo
  echo "Checks: failed-units, timers, disk, memory/earlyoom, syncthing+conflicts, skill-symlinks, tailscale, tokens (pplx/google), usage-guard, git repos, stale-outputs"
} > "$REPORT"
ln -sf "$REPORT" "$DOC_DIR/doctor-report.md"

# --- ntfy: ONLY when something is wrong -------------------------------------------
if [ "$n_bad" -gt 0 ]; then
  prio="default"; [ ${#fails[@]} -gt 0 ] && prio="high"
  body="$(printf "%s\n" "${fails[@]/#/FAIL: }" "${warns[@]/#/WARN: }" 2>/dev/null | grep . | head -20)"
  curl -fsS -m 10 -H "Title: Box doctor: ${#fails[@]} fail, ${#warns[@]} warn" -H "Priority: $prio" \
    -d "$body" "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1 || true
fi

echo "box-doctor: ${#fails[@]} fail, ${#warns[@]} warn, ${#fixed[@]} fixed -> $REPORT"
