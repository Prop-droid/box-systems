# qa — weekly smoke test of the ~/systems estate

`smoke.sh` runs each subsystem's SAFE dry-run / self-test and asserts an
expected output shape (exit 0, JSON parses, service reachable, expected stdout
marker). It is the first automated test coverage over the cron/agent estate.

- **Source of truth for what to run:** the VERIFY block in `~/systems/CLAUDE.md`.
- **Assertion model:** a check PASSes iff its command exits 0. Shape assertions
  (JSON parse, file existence, service reachable) are baked into each command,
  so exit 0 already means "ran + produced the right shape".
- **Silent when green.** One high-priority ntfy digest is sent only when a check
  FAILs. Always exits 0 — a QA report is informational; regressions surface in
  the report + ntfy, not via unit failure (watchdog tracks liveness separately).
- **Read-only.** Only safe dry-runs run; the sole external write is the failure
  ntfy. Subsystems whose only "dry-run" still writes externally, burns Claude
  tokens, or spends money are SKIPPED and listed as gaps, not run.

## Run

```bash
bash ~/systems/qa/smoke.sh              # normal (ntfy on fail)
NTFY_TOPIC="" bash ~/systems/qa/smoke.sh # silence ntfy (testing)
```

Output: `qa/qa-report.md` (latest report) + `qa/logs/<check>.log` (per-check
captured stdout/stderr for triage).

## Schedule

`qa-smoke.timer` — Sunday 08:00 (Europe/Vilnius), `Persistent=true`. Deploy via
`bash ~/systems/systemd/install.sh`. Registered in `watchdog/box-watchdog.sh`
TIMERS and `watchdog/jobs.conf` (192h staleness).

## Adding a check

Add one `check <id> <label> <timeout> <command>` line. Bake the shape assertion
into the command (e.g. `... && python3 -c 'import json;json.load(open(f))'`).
If a subsystem has no SAFE dry-run, add a `gap <id> <label> <reason>` line
instead — never wire a check that writes to ClickUp/BQ, sends ntfy, burns Claude
window tokens, or spends money.

## Known gaps (no safe dry-run — reported, not run)

winners-refresh, comments-digest, atria-weekly, research-monitor,
sha-weekly-report, agents, gbrain-weekly, fatigue-sentinel (--dry-run sends a
real [TEST] push), box-doctor, watchdog, transcript-janitor, night-queue,
fable-window, task-lessons, headless-claude probe, litellm. See the Gaps section
of `qa-report.md` for the reason on each. Closing a gap = adding a real
`--dry-run`/`--lint` mode to that subsystem, then converting its gap line to a
check.
