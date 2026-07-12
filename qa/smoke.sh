#!/usr/bin/env bash
# qa/smoke.sh — weekly safe smoke test of the ~/systems cron/agent estate (task 53).
#
# Runs each subsystem's SAFE dry-run / self-test (the VERIFY block in
# ~/systems/CLAUDE.md is the source of truth), asserts an expected output shape
# (exit 0, JSON parses, file created, expected stdout marker), and writes
# qa/qa-report.md. Subsystems with NO safe dry-run mode (or a dry-run that still
# writes externally / burns tokens / spends money) are SKIPPED and listed as
# gaps, not run.
#
# Silent when green; sends ONE ntfy digest only when a check FAILS. Always exits
# 0 (a QA report is informational — regressions surface in the report + ntfy, not
# via unit failure). Runs read-only dry-runs only; the only external write is the
# optional ntfy digest on failure.
#
# Manual: bash ~/systems/qa/smoke.sh   (silence ntfy: NTFY_TOPIC="" bash ...)
set -uo pipefail

# Timers get no login environment — export our own PATH + creds like every runner.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/ejam-dwh-sa.json}"
export RTK_HOOK_OFF=1

# ${VAR-default} (not :-) so NTFY_TOPIC="" is an explicit silence-for-testing override.
NTFY_TOPIC="${NTFY_TOPIC-tomas-tab-958e4431}"

SYS="$HOME/systems"
QA="$SYS/qa"
LOGDIR="$QA/logs"
REPORT="$QA/qa-report.md"
mkdir -p "$LOGDIR"
NOW="$(date '+%Y-%m-%d %H:%M:%S %Z')"
DAY="$(date '+%Y-%m-%d')"

PASS=(); FAIL=(); GAPS=()

# check <id> <label> <timeout-sec> <command>
# PASS = command exits 0 (shape assertions are baked into the command itself:
# JSON parse via python, file existence via test -f, stdout markers via grep).
check() {
  local id="$1" label="$2" tmo="$3" cmd="$4"
  local log="$LOGDIR/$id.log" out rc
  out="$(cd "$SYS" && timeout "$tmo" bash -c "$cmd" 2>&1)"; rc=$?
  printf '%s\n' "$out" > "$log"
  if [ "$rc" -eq 0 ]; then
    PASS+=("$id|$label")
    printf '  PASS  %-22s %s\n' "$id" "$label"
  else
    local tail1
    tail1="$(printf '%s\n' "$out" | grep -vE '^\s*$' | tail -1 | cut -c1-160)"
    [ "$rc" -eq 124 ] && tail1="TIMEOUT after ${tmo}s. ${tail1}"
    FAIL+=("$id|$label|rc=$rc|$tail1")
    printf '  FAIL  %-22s %s (rc=%s)\n' "$id" "$label" "$rc"
  fi
}

# gap <id> <label> <reason>  — subsystem with no safe dry-run; listed, not run.
gap() { GAPS+=("$1|$2|$3"); }

echo "qa smoke — $NOW"
echo "--- running safe checks ---"

# ---- Safe dry-runs / self-tests (assertion = exit 0 + baked shape check) ----

# Pure unit tests (no network, deterministic) --------------------------------
check research-lanes   "research-agent lanes unit tests" 90 \
  'node --test research-agent/lanes/score.test.mjs research-agent/lanes/tag.test.mjs'
check compliance-eval  "compliance-eval scorer test" 90 \
  'python3 compliance-eval/test_scorer.py'
check creative-feedback "creative-feedback gate/promote tests" 90 \
  'cd creative-feedback && python3 test_keep_best_gate.py && python3 test_decisions_unpromoted.py && python3 test_mark_decision_promoted.py && python3 test_render_proposals_md.py'

# Local self-tests / probes (no external writes) ------------------------------
check usage-guard      "usage-guard run + window JSON parses" 120 \
  'bash usage-guard/guard.sh >/dev/null 2>&1; python3 -c "import json,os;d=json.load(open(os.path.expanduser(chr(126)+\"/.claude/usage-window.json\")));assert isinstance(d,dict)"'
check fable-resume     "fable-resume no-op / launch" 60 \
  'bash fable-resume/resume.sh >/dev/null 2>&1'
check md-server        "md-server serving :8092" 15 \
  'curl -sf localhost:8092 >/dev/null 2>&1 || { a=$(ss -ltnH "sport = :8092" 2>/dev/null | awk "{print \$4}" | head -1); [ -n "$a" ] && curl -sf "http://$a" >/dev/null 2>&1; }'

# Read-only dry-runs that touch BQ/ClickUp (no writes) ------------------------
check bq-clickup-perf  "bq-clickup-perf PERF_DRY_RUN (writes nothing)" 240 \
  'TOKEN_FILE="$HOME/.config/clickup/pk" PERF_DRY_RUN=1 python3 bq-clickup-perf/bq_to_clickup_perf.py'
check launch-autofill  "launch-autofill convention lint (reads only)" 240 \
  'AUTOFILL_LINT=1 python3 launch-autofill/autofill.py'
check iteration-sugg   "iteration-suggestions DRY_RUN (no post)" 240 \
  'DRY_RUN=1 bash iteration-suggestions/run.sh'
check research-deepdive "research-agent deepdive --dry-run" 90 \
  'bash research-agent/bin/deepdive.sh --dry-run'

# ---- Gaps: no safe dry-run (unsafe side effects / tokens / money) -----------
gap winners-refresh   "winners-refresh"    "no dry-run; writes to ClickUp (idempotent but real)"
gap comments-digest   "comments-digest"    "no flag; needs BQ + writes digest md (exits 0 on no data by design)"
gap atria-weekly      "atria-weekly"       "no dry-run; live Atria swipe pulls"
gap research-monitor  "research-agent monitor.sh" "no dry-run; writes real competitor diff into /research feed"
gap sha-weekly-report "sha-weekly-report"  "no dry-run; burns Claude window tokens"
gap agents            "agents (weekly/monthly)" "no dry-run; each agent burns Claude window tokens"
gap gbrain-weekly     "gbrain-weekly"      "no dry-run; spends up to \$5 real embedding/doctor budget"
gap fatigue-sentinel  "fatigue-sentinel"   "--dry-run exists but sends a real [TEST] ntfy push (side effect)"
gap box-doctor        "box-doctor"         "no dry-run; auto-fixes symlinks + reruns guard + sends ntfy (is itself a diagnostic)"
gap watchdog          "watchdog"           "no dry-run; sends ntfy summary on every run"
gap transcript-janitor "transcript-janitor" "no dry-run; gzips/archives transcript files"
gap night-queue       "night-queue"        "driver executes real queued headless jobs"
gap fable-window      "fable-window"       "driver executes real headless claude jobs"
gap task-lessons      "task-lessons synth" "no dry-run; recall.sh is safe but not a schedulable job"
gap claude-plumbing   "headless claude probe" "consumes Claude window tokens; run manually via VERIFY block, not weekly"
gap litellm           "litellm"            "dormant proxy; nothing points at it (delete candidate)"

# ---- Write report ----------------------------------------------------------
{
  echo "# ~/systems QA smoke report"
  echo
  echo "- Run: $NOW"
  echo "- Host: $(hostname 2>/dev/null || echo '?')"
  echo "- Checks: ${#PASS[@]} pass, ${#FAIL[@]} fail, ${#GAPS[@]} gaps (no safe dry-run)"
  echo
  if [ "${#FAIL[@]}" -gt 0 ]; then
    echo "## FAIL — subsystem findings (report, not auto-fixed)"
    echo
    for f in "${FAIL[@]}"; do
      IFS='|' read -r id label rc tail1 <<<"$f"
      echo "- **$id** — $label ($rc)"
      echo "  - \`$tail1\`"
      echo "  - log: \`qa/logs/$id.log\`"
    done
    echo
  fi
  echo "## PASS"
  echo
  if [ "${#PASS[@]}" -gt 0 ]; then
    for p in "${PASS[@]}"; do IFS='|' read -r id label <<<"$p"; echo "- $id — $label"; done
  else
    echo "- (none)"
  fi
  echo
  echo "## Gaps — no safe dry-run mode (not run)"
  echo
  for g in "${GAPS[@]}"; do
    IFS='|' read -r id label reason <<<"$g"
    echo "- **$label** — $reason"
  done
  echo
  echo "_Generated by qa/smoke.sh. Silent when green; ntfy digest sent only on FAIL._"
} > "$REPORT"

echo "--- report written: $REPORT ---"
echo "summary: ${#PASS[@]} pass / ${#FAIL[@]} fail / ${#GAPS[@]} gaps"

# ---- ntfy digest only on failure -------------------------------------------
if [ "${#FAIL[@]}" -gt 0 ] && [ -n "$NTFY_TOPIC" ]; then
  msg="QA smoke: ${#FAIL[@]} failing —"
  for f in "${FAIL[@]}"; do IFS='|' read -r id _ _ _ <<<"$f"; msg+=" $id"; done
  curl -s -m 10 -H "Title: systems QA smoke" -H "Priority: high" \
    -d "$msg (see qa/qa-report.md)" "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1 || true
fi

exit 0
