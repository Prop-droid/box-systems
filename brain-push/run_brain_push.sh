#!/bin/bash
# Weekly wiki -> eJam Company Brain sync.
# gate self-test -> prepare.py (rebuilds the export; gate.py stops pages that
# break a hard rule) -> push.py (idempotent create/update, archives pages
# deleted from the wiki). Rules: README.md in this dir.
# Alerts: a failed run or a gate-blocked page posts to Discord #dev (and ntfy
# for failures). HTTP 401 = token lapsed: starts the re-auth unit and posts
# the ONE sign-in URL; re-auth restarts this service when Tomas has signed in.
set -uo pipefail
PKG="$HOME/brain/exports/2026-07_ejam-brain-wiki-push"
DIR="$HOME/systems/brain-push"
LOG="$DIR/last_run.log"
NTFY_TOPIC="tomas-ph-1ea8ac8e"
DEV_CH="1531564369672929290"

post_dev() {  # stdin = message body
  bash "$HOME/systems/lib/discord-post.sh" "$DEV_CH" DEV_TOKEN >/dev/null 2>&1 || true
}

{
  echo "=== brain-push $(date -Is) ==="
  cd "$PKG" || exit 1
  python3 "$DIR/test_gate.py" && python3 prepare.py && python3 push.py
} >"$LOG" 2>&1
rc=$?

if [ $rc -ne 0 ] || grep -qE "FAIL|NO WRITE GRANT" "$LOG"; then
  FAIL_LOG="${LOG%.log}-fail-$(date +%F).log"
  cp "$LOG" "$FAIL_LOG"   # next run overwrites $LOG; keep the forensics
  tail -5 "$LOG" | curl -s -H "Title: brain-push failed" -d @- "https://ntfy.sh/$NTFY_TOPIC" >/dev/null
  if grep -q "HTTP Error 401" "$LOG"; then
    if ! systemctl --user is-active --quiet brain-reauth.service; then
      systemd-run --user --unit brain-reauth --collect \
        python3 "$DIR/reauth_brain_mcp.py" >/dev/null 2>&1 || true
    fi
    for _ in $(seq 30); do [ -s "$DIR/reauth-url.txt" ] && break; sleep 1; done
    {
      echo "🔑 **brain-push: the company brain token expired (HTTP 401). Nothing was pushed.**"
      if [ -s "$DIR/reauth-url.txt" ]; then
        echo "Sign in with the ejam account from a Tailscale device. The push then runs again by itself:"
        cat "$DIR/reauth-url.txt"
      else
        echo "The re-auth unit gave no URL. Check: journalctl --user -u brain-reauth -n 30"
      fi
    } | post_dev
  else
    {
      echo "❌ **brain-push failed (rc=$rc).** Log: \`$FAIL_LOG\`"
      echo '```'
      grep -E "FAIL|NO WRITE GRANT|Error" "$LOG" | tail -6 | cut -c1-300
      echo '```'
    } | post_dev
  fi
  echo "brain-push FAILED (rc=$rc) — see $FAIL_LOG"
  exit 1
fi

if grep -q "GATE-BLOCK" "$LOG"; then
  {
    echo "🚧 **brain-push gate: $(grep -c 'GATE-BLOCK' "$LOG") page(s) NOT pushed.** Correct the wiki page, then run \`bash ~/systems/brain-push/run_brain_push.sh\`."
    grep "GATE-BLOCK" "$LOG" | sed 's/^ *GATE-BLOCK /- /' | cut -c1-350 | head -12
  } | post_dev
fi
echo "brain-push ok — $(grep -oE 'pass 1: [0-9]+ ok, [0-9]+ failed' "$LOG" | tail -1); $(grep -oE 'GATE: .*' "$LOG" | tail -1)"
