# task-lessons shell helpers. Source me at the end of a cron runner.
#   . "$HOME/sha-systems/task-lessons/lib.sh"
# Then capture an outcome:
#   lessons_capture --skill bq-clickup-perf --exit "$RC" --duration "$DUR" \
#                   --summary "..." --log "$LOG" --link memory/project_x
# Never fails the calling job (all paths return 0).

_TL_DIR="$HOME/sha-systems/task-lessons"
# shellcheck source=/dev/null
[ -f "$_TL_DIR/env.sh" ] && . "$_TL_DIR/env.sh"

lessons_capture() {
  local skill="" exit_code="0" duration="" summary="" lesson="" how="" context="" log="" verdict_override=""
  local -a links=() tags=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --skill)    skill="$2"; shift 2 ;;
      --exit)     exit_code="$2"; shift 2 ;;
      --duration) duration="$2"; shift 2 ;;
      --summary)  summary="$2"; shift 2 ;;
      --lesson)   lesson="$2"; shift 2 ;;
      --how)      how="$2"; shift 2 ;;
      --context)  context="$2"; shift 2 ;;
      --log)      log="$2"; shift 2 ;;
      --link)     links+=("$2"); shift 2 ;;
      --tag)      tags+=("$2"); shift 2 ;;
      --verdict)  verdict_override="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  [ -n "$skill" ] || { echo "lessons_capture: --skill required" >&2; return 0; }

  local verdict="success"
  [ "$exit_code" = "0" ] || verdict="failed"
  [ -n "$verdict_override" ] && verdict="$verdict_override"

  # Derive a summary from the log tail when not given (the useful bit on failure).
  if [ -z "$summary" ]; then
    if [ "$verdict" = "failed" ] && [ -n "$log" ] && [ -s "$log" ]; then
      summary="$(grep -iE 'error|fail|traceback|exception' "$log" 2>/dev/null | tail -3 | tr '\n' ' ' | cut -c1-300)"
      [ -n "$summary" ] || summary="$(tail -3 "$log" 2>/dev/null | tr '\n' ' ' | cut -c1-300)"
    fi
    [ -n "$summary" ] || summary="run ${verdict} (exit ${exit_code})"
  fi

  # Build the JSON record with python (safe quoting) and pipe to capture.py.
  TL_SKILL="$skill" TL_VERDICT="$verdict" TL_SUMMARY="$summary" \
  TL_LESSON="$lesson" TL_HOW="$how" TL_CONTEXT="$context" \
  TL_EXIT="$exit_code" TL_DURATION="$duration" \
  TL_TAGS="$(printf '%s\n' "${tags[@]}")" \
  TL_LINKS="$(printf '%s\n' "${links[@]}")" \
  python3 - <<'PY' | python3 "$_TL_DIR/capture.py"
import json, os
def lst(v):
    return [x for x in (os.environ.get(v, "") or "").splitlines() if x]
rec = {
    "skill": os.environ["TL_SKILL"],
    "verdict": os.environ["TL_VERDICT"],
    "summary": os.environ["TL_SUMMARY"],
}
for k_env, k in (("TL_LESSON","lesson"),("TL_HOW","how_to_apply"),("TL_CONTEXT","context")):
    if os.environ.get(k_env): rec[k] = os.environ[k_env]
if os.environ.get("TL_EXIT") != "": rec["exit_code"] = int(os.environ["TL_EXIT"])
if os.environ.get("TL_DURATION"): rec["duration_s"] = float(os.environ["TL_DURATION"])
if lst("TL_TAGS"):  rec["tags"] = lst("TL_TAGS")
if lst("TL_LINKS"): rec["link_to"] = lst("TL_LINKS")
print(json.dumps(rec))
PY
  return 0
}
