# night-queue — permanent generic overnight headless-claude queue

Generic successor to the ad-hoc `~/fable-window/` harness (driver v2 → v3).
Queue task files, each one becomes a sequential headless `claude -p` run with
its own MODEL/CWD/TIMEOUT; limit hits pause-and-retry; artifacts land on disk
and auto-commit. Proven pattern: 17/17 fable-window tasks exit=0 across 3
nights (see `~/brain/projects/2026-07/fable-window/playbook_overnight_harness.md`).

## Layout

```
night-queue/
  queue.sh      driver v3 (sequential loop over queue/tasks/*.task)
  resume.sh     relauncher (detached transient unit; used by the timer)
  nq            CLI: add | list | status | stop | release
  systemd/      night-queue-resume.{service,timer} — STAGED, not enabled (see below)
  queue/
    tasks/      NN-name.task (committed — the queue definition)
    logs/       NN-name.log + NN-name.done markers (gitignored via **/logs/)
    artifacts/  ALL task output (committed by the auto-commit step)
```

`NQ_DIR=/path/to/other/queue` points every script at a different queue dir
(e.g. a one-off window dir); default is `queue/` here.

## Task file format (v3 — keyed headers, any order, then blank line, then prompt)

```
MODEL: claude-sonnet-4-6
CWD: ~/brain
TIMEOUT: 1800

Read <rules file> and obey it.
<prompt: exact inputs to load, exact artifact output paths>
```

- MODEL default `claude-sonnet-4-6`, CWD default `~` (CWD gates project
  context — Shameless/Code Things tasks need `CWD: ~/brain`), TIMEOUT default
  3600s.
- `NN-` prefix = execution order; name a report task `99-report` so it sorts last.
- Prompts must name exact input files and exact output paths under
  `queue/artifacts/`.

## Usage

```bash
nq add 10-my-task --model claude-opus-4-8 --cwd '~/brain' --file prompt.md
nq list                    # per-task done/pending/GAVE-UP
nq status                  # driver state, counts, flags, last log tail
bash queue.sh              # run the queue now, foreground
START_AT=23:00 bash queue.sh   # wait until 23:00 (touch queue/START_NOW to skip wait)
nq stop                    # STOP flag: abort before next task (--now kills current)
nq release                 # clear STOP/PAUSE and relaunch via resume.sh
```

Overnight launch (detached, survives disconnect, correct cgroup):

```bash
systemd-run --user --unit night-queue-driver --collect \
  bash -c 'START_AT=23:00 bash ~/systems/night-queue/queue.sh >> ~/systems/night-queue/queue/logs/driver.console 2>&1'
```

## Driver semantics (v3)

- Sequential over `tasks/*.task`; skips any task with an existing
  `logs/<name>.done` → resumable after any crash. Delete the `.done` to rerun.
- **Limit-retry:** nonzero exit + log matching the limit regex (session/usage/
  rate limit, credit balance, 5-hour/weekly limit, Fable wording, "resets at
  HH") → sleep 30 min, retry, max 16 tries, then `LIMIT-GAVE-UP` in the marker.
  resume.sh clears GAVE-UP markers so they get another shot next tick.
- **Pause:** waits while `~/.claude/PAUSE_CLAUDE_BG` (usage-guard 90% flag) or
  queue-local `PAUSE`/`PAUSE_90` exists; checked before each task and honored
  by resume.sh.
- Each run: `(cd $CWD && timeout $TIMEOUT claude -p "$prompt" --model $MODEL
  --dangerously-skip-permissions < /dev/null)` → `logs/name.log`.
- ntfy per task done/limit/gave-up + queue start/complete to
  `tomas-tab-958e4431` (override: `NQ_NTFY=<topic>`).
- On completion: auto `git commit` of `queue/artifacts/` + `queue/tasks/`
  (only if the queue dir is inside a git repo; logs stay out via .gitignore).

## Enabling the resume timer (not yet enabled — deliberate)

Wave-5 task 50 authorized creating this dir only; enabling the timer is a
separate approval. When approved:

```bash
cp ~/systems/night-queue/systemd/night-queue-resume.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now night-queue-resume.timer
```

Then per CLAUDE.md: add `night-queue-resume` to `watchdog/box-watchdog.sh`
TIMERS and `watchdog/jobs.conf`, and consider moving the units into
`~/systems/systemd/` so `install.sh` owns them. The timer fires at `*:2/15`
(offset from fable-resume's `*:0/15` so both never launch claude in the same
minute). usage-guard already gates everything via `PAUSE_CLAUDE_BG`; on window
reset it only kicks `fable-resume` explicitly, but this timer's next 15-min
tick picks pending work up on its own.

## Authoring rules for queued tasks (battle-tested, from the playbook)

- Only queue tasks with a fully-specified deliverable; ambiguity becomes a
  wrong artifact by morning.
- Headless runs cannot use interactively-authenticated MCPs (claude.ai
  connectors); use REST tokens on disk.
- HEADLESS DISCIPLINE in every prompt's rules file: one-shot run, finish
  synchronously, never spawn background jobs to await later.
- Artifacts-only by default; live writes need an explicit per-task exception
  with a git baseline and a named verify command.
- Queue a mechanical verify task late and a `99-report` task last.

## Smoke test

`queue/tasks/10-smoke-hello.task` + `20-smoke-chain.task` (claude-haiku, cheap)
prove the loop end-to-end: task 2 reads task 1's artifact, so a green run
shows sequencing, artifact landing, `.done` markers, and the auto-commit.
Rerun anytime: `rm queue/logs/*smoke*.done && bash queue.sh`.
