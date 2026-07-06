# ~/systems — box automation estate

Canonical home for every cron/agent job on the 24/7 agent box (Debian 13,
`systemctl --user`, NOT launchd — ignore Mac-era plist/Google Drive comments
still in some headers). Git repo, pushed to private `Prop-droid/box-systems`.
Edit scripts HERE only; the old `~/sha-systems` two-copy model is retired.

Read this before touching anything. Per-dir READMEs/SETUP.md have depth;
this file is the map.

## Subsystem map

Schedule = live systemd user timer (Europe/Vilnius). "Dry run" = the safe
command to prove a change works before the timer fires.

### Data pipelines (BQ / ClickUp / Atria)

- **bq-clickup-perf/** — nightly BQ ad-performance writeback (ROAS/Spend/Orders/
  Spend30d/LastActive) onto active Creative Strategist ClickUp tasks.
  Schedule: daily 02:30. Entry: `run_perf_writeback.sh` → `bq_to_clickup_perf.py`.
  Dry run: `TOKEN_FILE=~/.config/clickup/pk PERF_DRY_RUN=1 python3 bq_to_clickup_perf.py` (computes + prints, writes nothing; TOKEN_FILE must be set, script defaults to a Mac-era /tmp path).
- **launch-autofill/** — daily pre-fill of empty launch/taxonomy custom fields on
  active CS-list tasks (images inferred from name/desc; videos read script or
  comment-ping Tomas). Entry: `run_autofill.sh` → `autofill.py`.
  Dry run: `AUTOFILL_LINT=1 python3 autofill.py` (or `--lint`).
  Note: the launchd plist here is `.disabled`; scheduling status is whatever
  `systemctl --user list-timers` says (no live timer as of 2026-07-06).
- **winners-refresh/** — weekly refresh of the ClickUp `winners.jsonl` archive
  (discover → enrich → reparse; scripts live in
  `~/brain/projects/2026-05/ClickUp Connection/`). Schedule: Mon 04:00.
  Entry: `run_winners_refresh.sh`. No dry-run; safe-ish (idempotent, ~5 min),
  verify via log line `winners.jsonl N -> M lines`.
- **comments-digest/** — weekly FB ad-comments digest → `out/digest-YYYY-MM-DD.md`
  (CCC serves it at `/api/comments/digest`). Schedule: Tue 04:00.
  Entry: `run_digest.sh`. No flag; a manual run only writes a local md (needs BQ).
  Exits 0 on no data by design (upstream feed was dead; don't "fix" that).
- **fatigue-sentinel/** — daily creative fatigue watch: winning ads whose hook
  rate/ROAS decays vs 7-day baseline → one ntfy alert; Mon heartbeat.
  Schedule: daily 08:30 (enabled 2026-07-05). Entry: `run_sentinel.sh` →
  `fatigue_sentinel.py`. Dry run: `./run_sentinel.sh --dry-run` (prints pushes,
  sends one real `[TEST]` min-priority push as delivery proof).
- **atria-weekly/** — weekly FULL followed-brands Atria swipe pull + headless-claude
  NEW-ads diff (deterministic python diff as fallback). Complementary to the daily
  brand-filtered research-monitor. Schedule: Mon 07:30 (enabled 2026-07-05).
  Entry: `run_atria_weekly.sh`. No dry-run; it's read-only pulls + local files.

### Research agent

- **research-agent/** — three lanes, one dir:
  - `bin/monitor.sh` — daily 01:45, cheap NO-LLM Atria competitor-ad diff into the
    CCC /research feed (brand set in `monitor.conf`). Manual: `bash bin/monitor.sh`.
  - `bin/deepdive.sh` — headless research pass draining one queued question.
    Dry run: `bash bin/deepdive.sh --dry-run`. NOTE: its original timer
    (`research-deepdive.timer`, daily 01:00) was REPURPOSED to the lanes engine —
    deepdive itself is currently manual-only.
  - `lanes/` — research lanes engine (atria + BQ + comments → scored lanes).
    Runs daily 01:00 via `research-deepdive.service` → `bin/run-lanes.sh` (env
    wrapper; reads `~/creative-command-center/.env.local` for BQ_TABLE/BRAND).
    Tests: `node --test lanes/score.test.mjs lanes/tag.test.mjs`.
  - Output data lives in `~/brain/systems/research-agent/output/` (NOT here).

### Reports & synthesis (headless claude)

- **sha-weekly-report/** — Mon 04:45 SHA brand-health report: 6 bq queries →
  prompt template → `claude -p` → `~/brain/projects/<YYYY-MM>/sha-weekly-report-<MON>/report.md`.
  Entry: `run_report.sh [YYYY-MM-DD-of-monday]` (no arg = last Mon–Sun). Manual
  run for a past week is the test; it overwrites only that week's folder.
- **iteration-suggestions/** — Tue+Thu 10:00, drafts creative iteration suggestions
  from the latest weekly report and posts to ClickUp "Tomas Pod" chat.
  Self-disables after 2026-07-17 (END_DATE in `run.sh`). Entry: `run.sh`.
  Dry run: `DRY_RUN=1 bash run.sh` (drafts, resolves links, does not post).
- **agents/** — weekly (Sun 05:30: transcript janitor, memory-hygiene, skill-garden,
  retro) and monthly (1st 06:00: consolidation, token-audit) maintenance agents.
  Prompts in `prompts/<name>.md`, reports in `reports/<name>/YYYY-MM-DD.md`.
  Entry: `run_agents.sh weekly|monthly`. No dry-run flag — agents are read/report
  only; test one prompt by piping it to `claude-max --print` yourself.
- **gbrain-weekly/** — Mon 03:30 gbrain maintenance: embed stale + doctor
  remediate CAPPED AT $5 real spend. Entry: `run_gbrain_weekly.sh`. No dry-run;
  a manual run spends money — prefer `gbrain health` to inspect.

### Feedback / lessons loops (write proposals, never canon)

- **creative-feedback/** — Tue 05:00 synthesis of unpromoted creative feedback +
  decision disagreements → `proposals.jsonl` + `proposals.md`. Promotion is a
  separate human-gated step (`mark_promoted.py`, `keep_best_gate.py`).
  Entry: `run_feedback_synth.sh`. Tests: `python3 test_keep_best_gate.py
  test_decisions_unpromoted.py test_mark_decision_promoted.py` (run each).
- **task-lessons/** — cross-job lesson capture/recall. `lib.sh` is sourced by other
  runners (`lessons_capture` on every exit — best-effort, never changes job rc);
  `recall.sh <skill> N` primes prompts with past lessons. Synthesis Tue 05:30 via
  `run_lessons_synth.sh`. Safe to run manually (idempotent on promoted flag).
- **compliance-eval/** — eval harness for the shameless-script skill; deterministic
  `scorer.py` over `policy.json`, gold set gates the scorer. Not scheduled — run
  around skill/policy changes. Smoke: `python3 test_scorer.py` then
  `python3 run_eval.py --mode generate --limit 3`. Regression gate:
  `run_eval.py --mode generate --compare baseline_YYYYMMDD` (exit 1 = regression).

### Infra / guards

- **watchdog/** — two layers: `box-watchdog.sh` (scheduled, daily 06:30) checks
  timers in its `TIMERS` list + core services + syncthing/tailscale, writes
  `reports/latest.md`, ntfy summary. `run_watchdog.sh [--weekly]` runs the
  modular `checks/*.sh` against `jobs.conf`. Both safe to run manually.
  When you ADD a timer, add it to `box-watchdog.sh` TIMERS and `jobs.conf`.
- **usage-guard/** — every 5 min: ccusage over box+Mac transcripts; at ≥90% of the
  5h Claude window during 08:00–23:00 it creates `~/.claude/PAUSE_CLAUDE_BG` +
  `~/fable-window/PAUSE_90`, ntfy-alerts tablet+phone; clears + resumes on window
  reset. Entry: `guard.sh`; tunables in `config`. Manual run is safe.
  `statusline.sh` composes `· 5h:NN%` around the ORIGINAL statusline — never replace it.
- **fable-resume/** — every 15 min: relaunches the fable-window driver when tasks
  are pending and nothing is running (see cgroup gotcha below). Entry: `resume.sh`.
  Manual run is safe (exits early on STOP/PAUSE/no-pending).
- **fable-window/** — snapshot of the Fable 5 window harness (canonical live dir is
  `~/fable-window/`): `driver.sh` runs `tasks/*.task` as sequential headless claude
  jobs with per-task MODEL/CWD, limit-retry (30 min x16). Controls: `touch
  ~/fable-window/START_NOW` / `STOP`; `PAUSE_90` honored mid-loop.
- **transcript-janitor/** — gzip+archive Claude transcripts >30d (never deletes,
  never touches memory/*.md). Called by agents-weekly; manual: `run_janitor.sh`.
- **md-server/** — always-on read-only markdown browser for `~/brain` on :8092
  (Tailnet/LAN). `md-server.service` (Type=simple, Restart=on-failure).
  Test: `curl -s localhost:8092 | head`.
- **litellm/** — DORMANT metering proxy on 127.0.0.1:4000; no client points at it.
  Confirmed delete-candidate; don't build on it.
- **lib/** — `hermes_fallback.sh`: shared retry-through-Hermes for failed headless
  claude runs (`hermes_fallback <prompt_file> <out> <err>`; spends paid tokens,
  only fires on actual failure).
- **tablet-screen.sh** — `off|on` over adb (tablet 192.168.0.160); scheduled
  23:00/07:00 via tablet-screen-{off,on} units.

## systemd user-unit patterns

- Every cron job = a `Type=oneshot` `.service` + an `OnCalendar` `.timer` with
  `Persistent=true` (catches up after downtime). Always-on services =
  `Type=simple` + `Restart=on-failure` + `WantedBy=default.target`.
- Units use `%h` for $HOME and assume the suite at `~/systems`.
- Deploy flow: edit unit in `systemd/`, run `bash systemd/install.sh`
  (copies to `~/.config/systemd/user/`, daemon-reload, `enable --now` every
  timer). Idempotent. NEVER hand-edit only the live copy — it gets clobbered.
- **Repo vs live drift:** `systemd/` here holds only this suite's units. Live
  `~/.config/systemd/user/` also has units owned elsewhere (usage-guard,
  fable-resume, iteration-suggestions, raw-ingest-scan, qrevo-watch, coach-*,
  tablet-brief, hermes-gateway, camofox, creative-command-center, tablet-dash,
  agentic-bots, litellm, visionclaw-shim). Check `systemctl --user list-timers
  --all` for ground truth, not the README table (e.g. research-deepdive.service
  now runs the lanes engine, not deepdive.sh).
- **Cgroup kill gotcha:** a tmux session / background child spawned directly from
  a oneshot service DIES when the service exits — the whole cgroup is reaped.
  To launch something that outlives the oneshot, detach it into its own
  transient unit:
  `systemd-run --user --unit <name> --collect bash -c '<cmd> >> log 2>&1'`
  (`--collect` garbage-collects the unit after exit so reruns don't hit
  "unit already exists"). This is exactly what `fable-resume/resume.sh` does.
- Guard against double-launch with an ANCHORED pgrep (`pgrep -f "^bash .*driver.sh"`)
  — unanchored patterns false-match stray tmux command strings — plus
  `systemctl --user is-active <unit>`.
- Timers get no login environment: no `~/.local/bin` on PATH, no `~/.hermes/.env`.
  Every runner exports its own PATH and sources its own env. A headless job that
  exits 127 = PATH problem; 203/EXEC = lost exec bit (has happened after repo
  renames — `chmod +x` and commit).
- Timer slots are deliberately staggered through the night (00:30–08:30);
  put new heavy jobs in a free slot, early morning, before the report crons
  that consume their output.

## Headless claude conventions

- Invoke via the wrapper `/usr/local/bin/claude-max` (root-owned; sudo to edit).
  It: exits 0 early if `~/.claude/PAUSE_CLAUDE_BG` exists (usage-guard pause —
  ALL headless claude crons obey it), unsets ANTHROPIC_API_KEY (Max OAuth
  subscription, no per-token cost), sets CLAUDE_CONFIG_DIR, and prepends
  `~/.local/bin` to PATH (claude is a native user-local install; the root npm
  global was removed 2026-06-18).
- Prompt goes via **STDIN**, never as a positional arg after `--allowed-tools`
  (it's variadic and eats the prompt):
  `claude-max --print --model claude-sonnet-4-6 --dangerously-skip-permissions --allowed-tools "Read Write Bash Glob Grep" < prompt.md > out.md`
- Interactive-style runs (fable driver) use `claude -p "$prompt" --model X
  --dangerously-skip-permissions < /dev/null` — the `</dev/null` matters or the
  job can hang on a tty read.
- `--dangerously-skip-permissions` is required headless (no one to approve).
  Bound the blast radius with `--allowed-tools` instead.
- Wrap in `timeout` (1500–3600s). Validate output (non-empty + starts with an
  `# ` H1), retry up to 3x, land atomically from a tmp file. Keep a
  deterministic non-LLM fallback where the artifact MUST land (see
  atria-weekly's python diff), and/or `lib/hermes_fallback.sh`.
- Model discipline: Sonnet (`claude-sonnet-4-6`) for cron agents/reports (cap
  discipline); bigger models only where a human queued the task (fable driver).
- Usage windows are 5h rolling; usage-guard owns the 90% pause. Limit-hit runs
  exit nonzero with "usage limit" in output — treat as transient (retry/sleep),
  not as failure. A `claude -p` run that emits ZERO output with rc 0 is the
  known silent failure mode — that's what the validate-retry loop is for.
- One-shot headless runs must finish synchronously — never background a child
  and "wait for a notification" (there is none; two fable agents died this way).
- Hook opt-out for crons where relevant: `export RTK_HOOK_OFF=1`.
- Best-effort `lessons_capture` (task-lessons/lib.sh) at the end of runners:
  `|| true`, never changes the job's exit code.

## Fleet networking (what code here actually needs)

Full manual = the `fleet-control` skill. Load-bearing subset for this repo:

- **Tailscale IPs, not mDNS.** From the box, `mac`/`*.local` do NOT resolve.
  Mac = `100.68.166.21` (ssh key `~/.ssh/id_ed25519_mac`, user tomas) — used by
  usage-guard rsync/scp. This box = `100.107.26.69` / MagicDNS `tomas-agent-box`.
  Always `-o BatchMode=yes -o ConnectTimeout=5` + `timeout N` around ssh/rsync
  in cron paths, `|| true` if best-effort.
- **Per-host ssh keys/aliases** live in `~/.ssh/config` — use the alias
  (`github-personal`, `nobara`, key-pinned Mac), never assume the default key.
- **Tablet** (Lenovo P11 Pro) is LAN adb at `192.168.0.160` (port rotates across
  reboots — rediscover the serial like `tablet-screen.sh` does).
- **ntfy topics:** tablet/main alerts `tomas-tab-958e4431`, phone usage alerts
  `tomas-usage-guard-7c31`. `curl -s -d "msg" -H "Title: x" [-H "Priority: high"]
  https://ntfy.sh/<topic>` with `-m 10`; min-priority for heartbeats.
- **Creds live OUTSIDE the repo:** BQ SA `~/.config/gcloud/ejam-dwh-sa.json`,
  ClickUp `~/.config/clickup/pk` (600), provider keys `~/.hermes/.env`, Atria
  `~/.config/atria/key`, gbrain `~/.gbrain/.pgurl`. Guard-check them at the top
  of every runner and fail loud. Never commit secrets.

## Git

- Remote: `git@github-personal:Prop-droid/box-systems.git` (private). The
  `github-personal` ssh alias is REQUIRED — plain `github.com` resolves to the
  wrong account's key.
- Commit style: `type(scope): imperative summary` — e.g. `feat(compliance-eval):`,
  `fix(comments-digest):`, `infra:`. Before any risky live change, land a
  `baseline before <thing>` commit; after, the change commit. Keep commits
  scoped per subsystem.
- `.gitignore` keeps run artifacts out; logs go to `~/Library/Logs/<job>/` or
  `<dir>/logs/` (both gitignored patterns) — yes, `~/Library/Logs` on Linux is
  a plain dir kept for Mac-script parity.

## VERIFY

Run the relevant block after touching a subsystem. Green = safe to walk away.

```bash
# scheduling ground truth + anything failed
systemctl --user list-timers --all | grep -v n/a
systemctl --user --failed
journalctl --user -u <job>.service -n 50   # last run's output

# whole-estate health (safe, sends one ntfy)
bash ~/systems/watchdog/box-watchdog.sh

# per-subsystem dry runs
TOKEN_FILE=~/.config/clickup/pk PERF_DRY_RUN=1 python3 ~/systems/bq-clickup-perf/bq_to_clickup_perf.py
AUTOFILL_LINT=1 python3 ~/systems/launch-autofill/autofill.py
~/systems/fatigue-sentinel/run_sentinel.sh --dry-run
DRY_RUN=1 bash ~/systems/iteration-suggestions/run.sh
bash ~/systems/research-agent/bin/deepdive.sh --dry-run
node --test ~/systems/research-agent/lanes/score.test.mjs ~/systems/research-agent/lanes/tag.test.mjs
python3 ~/systems/compliance-eval/test_scorer.py
cd ~/systems/creative-feedback && python3 test_keep_best_gate.py && python3 test_decisions_unpromoted.py
bash ~/systems/usage-guard/guard.sh && cat ~/.claude/usage-window.json
bash ~/systems/fable-resume/resume.sh; echo "rc=$? (0 = no-op or launched)"
curl -s localhost:8092 >/dev/null && echo md-server OK

# headless claude plumbing (cheap end-to-end probe)
echo 'Reply with exactly: OK' | /usr/local/bin/claude-max --print --model claude-sonnet-4-6

# after editing units
bash ~/systems/systemd/install.sh
```

Manual-run cautions: `gbrain-weekly` spends up to $5; `agents/run_agents.sh`
and `sha-weekly-report/run_report.sh` burn Claude window tokens;
`winners-refresh`/`bq-clickup-perf` (without PERF_DRY_RUN) write to ClickUp.
