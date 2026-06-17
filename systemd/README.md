# systemd units (the box's schedule)

Source of truth for how the suite is scheduled on the agent box. The box runs
**systemd user timers** (`~/.config/systemd/user/`), not launchd — ignore the
Mac-era launchd/plist comments still in some scripts.

## Install / refresh
```bash
bash systemd/install.sh      # copies units, daemon-reload, enable --now every timer
```
Edit a `.service`/`.timer` here, re-run `install.sh`. Idempotent.

## Schedule (OnCalendar)
| Timer | When | Runs |
|---|---|---|
| bq-clickup-perf | daily 02:30 | BQ perf writeback to ClickUp |
| research-deepdive | daily 01:00 | drain one research question |
| research-monitor | daily 01:45 | research feed monitor |
| raw-ingest-scan* | daily 00:30 | (separate project) |
| box-watchdog | daily 06:30 | system health checks |
| agents-weekly | Sun 05:30 | memory-hygiene, skill-garden, retro |
| gbrain-weekly | Mon 03:30 | embed stale + capped doctor remediate |
| winners-refresh | Mon 04:00 | refresh winners archive |
| sha-weekly-report | Mon 04:45 | brand-health weekly report |
| comments-digest | Tue 04:00 | FB comment digest |
| creative-feedback-synth | Tue 05:00 | creative loop synthesis |
| task-lessons-synth | Tue 05:30 | task-lessons synthesis |
| agents-monthly | 1st of month 06:00 | consolidation, token-audit |

Prereqs: the suite is deployed at `~/sha-systems` and per-job credentials exist
outside the repo (`~/.config/clickup/pk`, `~/.config/gcloud/*.json`, `~/.hermes/.env`).
