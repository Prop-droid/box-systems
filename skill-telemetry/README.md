# skill-telemetry

Deterministic usage telemetry from Claude Code transcripts (box + staged Mac).
Answers "what actually fires" so "optimised for my usage" has data behind it.

Per 30-day window it counts, from every transcript:
- **tool mix + per-tool error rate** (errors attributed by joining `tool_result.is_error`
  back to the `tool_use` name within each session)
- **skill invocations** per skill, with week-over-week deltas
- **never-used local skills** — catalog skills that load into the listing every
  session but never fired (dead always-on context; token-audit flagged the
  catalog at ~16k chars)

## Files
- `telemetry.py` — scan + render; writes `reports/<date>.md`, persists `stats.json` for deltas.
- `run_telemetry.sh` — weekly runner; refreshes staged Mac transcripts via
  correction-capture's `pull_mac.sh`, then runs the scan.
- `test_telemetry.py` — unit tests for error-attribution + delta (no transcripts).

## Schedule
`skill-telemetry.timer` Sun 04:00 → `reports/<date>.md`. The self-improve digest
(Tue 06:30) reads the newest report as a source block, so unused-skill and
error-rate findings reach Discord with the other proposals. Registered in
`watchdog/box-watchdog.sh` TIMERS + `jobs.conf` (192h).

## Manual
```bash
python3 telemetry.py --days 30            # print + write report + update stats.json
python3 telemetry.py --days 7 --no-save   # ad-hoc window, don't touch the delta baseline
python3 test_telemetry.py                 # 4 tests
```

## Interpreting
- A skill in "never-used" for several consecutive weeks is a prune candidate
  (remove from `~/.claude/skills` or route it behind find-skills instead of the
  always-loaded catalog).
- A tool >=15% error over >=10 calls gets its own "high error-rate" section —
  usually a flaky MCP server or a wrong-usage pattern worth a memory rule.
