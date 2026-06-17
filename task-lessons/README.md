# task-lessons

A self-improvement loop for the agent box's crons/skills/agents. Generalizes the
`creative-feedback` loop from creative verdicts to *any* task outcome. After a run,
it captures what happened as a structured gbrain page (with links + tags + timeline,
so the flat brain becomes a graph); before a run, `recall.sh` primes the agent with
its own past lessons (the Reflexion pattern).

## Files
- `capture.py`  — stdin JSON record → append `ledger.jsonl` + write gbrain page (failures/lessons only) + tags + timeline + typed link. gbrain failures never break capture; the ledger is source of truth.
- `lib.sh`      — `lessons_capture` shell fn for cron runners to source. Derives verdict from exit code, summary from log tail.
- `recall.sh`   — `recall.sh <skill> [n]` → "Past lessons" block to inject into a `claude -p` prompt.
- `env.sh`      — PATH + Gemini key (gbrain runs via `~/.bun/bin`, embeddings need the key).
- `config.json` — `stable_threshold` (promotion gate), slug prefix, success-page policy.
- `ledger.jsonl`— append-only record of every captured outcome.

## Capture (in a cron runner)
```bash
START=$SECONDS
if python3 myjob.py; then RC=0; else RC=$?; fi
DUR=$((SECONDS-START))
. "$HOME/sha-systems/task-lessons/lib.sh"
lessons_capture --skill "myjob" --exit "$RC" --duration "$DUR" \
  --log "$LOG" --link "memory/project_myjob" || true
exit "$RC"
```
Plain successes are ledger-only (no brain noise). Failures, and any run with an
explicit `--lesson`, get a full gbrain page. Add `--lesson`/`--how` when you know
the takeaway; otherwise the failed-run log tail becomes the summary.

## Recall (in a claude-headless cron)
```bash
LESSONS="$($HOME/sha-systems/task-lessons/recall.sh myjob 5)"
echo "$LESSONS

$PROMPT" | claude -p ...
```

## Verdicts
`success` | `failed` (auto from exit code) | `fixed` (set explicitly when a run
self-recovered). Tags applied per page: `task-lesson`, `skill:<skill>`, `<verdict>`.

## Wired into
- `bq-clickup-perf`, `launch-autofill` — capture-only (python crons).
- `agents/run_agents.sh` — recall + capture for all 5 claude agents.
- `research-agent/bin/deepdive.sh` — recall + capture (EXIT trap, skill `research-deepdive`).

The two claude-prompt runners also fall back to Hermes on a claude failure
(`../lib/hermes_fallback.sh`); a rescue is captured as verdict `fixed`.

## Phase 2 (not built)
- `run_lessons_synth.sh` weekly cron: cluster lessons, run `gbrain anomalies` /
  contradiction check, draft promotions to canon at `stable_threshold` (≥3), gated
  by human approval — mirror `creative-feedback/run_feedback_synth.sh` + `mark_promoted.py`.
- Recall wired into the `claude -p` crons (research-agent, launch-autofill).

## Known gbrain quirks (learned building this)
- Hand-rolled YAML frontmatter breaks on `: ` in a value (e.g. tracebacks) → page
  silently demotes to `type: concept`. `capture.py` json-quotes the title to avoid it.
- `list --type` and colon-tag indexes lag on just-written pages; `list --tag task-lesson`
  is reliable. `recall.sh` filters the base tag by slug prefix for this reason.
