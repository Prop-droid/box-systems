# box-doctor — daily box self-diagnostic

Daily health sweep over the known failure modes of the agent box. Silent when
green: the ntfy digest (topic `tomas-tab-958e4431`) fires ONLY when a check
fails or warns. Report always lands at `reports/YYYY-MM-DD.md`, with
`doctor-report.md` symlinked to the latest.

- Schedule: daily 08:45 (`box-doctor.timer`, units in `~/systems/systemd/`).
- Entry: `doctor.sh`. Manual run is safe; pure bash, no claude tokens burned.
- Test without pushing: `NTFY_TOPIC="" bash doctor.sh` (curl to empty topic
  no-ops).

## Checks

1. Failed systemd units, user + system scope (`xdg-desktop-portal*` ignored —
   known headless noise).
2. Enabled-but-inactive user timers.
3. Disk `/` usage (warn 80%, fail 90%).
4. MemAvailable < 1GB (warn) + earlyoom kills in last 24h (system journal).
5. Syncthing service active + `*sync-conflict*` files in the unified memory dir.
6. Dead symlinks in `~/.claude/skills`.
7. Tailscale up (fail) + Mac peer online (warn — usage-guard goes blind to Mac
   spend when it's offline).
8. Token telltales: perplexity session token (~30d expiry — warns at 25d of
   `~/.hermes/config.yaml` mtime, fails hard on "anonymous" hits in the
   hermes-gateway journal), google work token (`gws auth status` token_valid).
9. `~/.claude/usage-window.json` freshness (guard writes every 5 min; >30 min
   stale = broken).
10. Git repos with uncommitted/unpushed work: `~/systems`, `~/brain`,
    `~/creative-command-center` (non-repos and missing upstreams are noted,
    not warned — `~/brain` is not a git repo as of 2026-07).
11. Stale cron outputs — newest artifact older than the schedule implies
    (list in `STALE_OUTPUTS` inside `doctor.sh`). comments-digest is
    deliberately NOT listed: its upstream feed is dead and it exits 0 on no
    data by design.

## Auto-fixes (the ONLY two; everything else is report-only)

- Dead skill symlinks pointing into `~/.hermes/skills` — skill-sync pattern:
  relink to the skill's current home (live category dir first, `.archive/`
  fallback), prune if gone. Non-hermes dead links are warned, never touched.
- Stale `usage-window.json` — reruns `~/systems/usage-guard/guard.sh` once and
  rechecks.

Both are recorded under "Auto-fixed" in the report.

## Overlap with box-watchdog

box-watchdog (06:30) checks a fixed timer list + core services and always
pushes a summary. box-doctor is the broader estate diagnostic and is silent
when green. Both existing on purpose; doctor also checks that watchdog's own
report is fresh.
