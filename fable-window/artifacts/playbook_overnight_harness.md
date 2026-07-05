# Playbook: overnight artifact-queue harness (fable-window pattern, reusable after 2026-07-07)

How to run a queue of headless `claude -p` tasks overnight on the agent box so a scarce resource (a model window, a usage-cap night, a big batch) gets converted into reviewable artifacts, not chat history. Proven across 3 nights, 17/17 tasks exit=0. Sources: ~/fable-window/{RULES.md,driver.sh,run-one.sh,REPORT.md}, project_fable_window, project_system_maintenance_loops, the _ledger.md postmortems (07c/07d background-job failure, night-2 limit collision).

## When NOT to use (kill criteria, check first)

- KILL for tasks needing Tomas's judgment mid-run (LP choices, approvals, taste calls). Queue only tasks with a fully-specified deliverable; ambiguity becomes a wrong artifact by morning.
- KILL for tasks needing interactively-authenticated MCPs (claude.ai connectors like ClickUp/Drive MCC do NOT ride along headless). Headless tasks must use REST tokens on disk (`~/.config/clickup/pk`, BQ SA json) or be rewritten to.
- KILL for live-write side effects unless RULES.md carries an explicit per-task exception (git baseline commit first, verify command named). Default is artifacts-only.
- KILL if the deliverable is < ~15 min of interactive work; harness overhead is not worth it.
- Do NOT start the queue inside an exhausted usage window; headless runs share the session cap with interactive work (resets 19:00 Europe/Vilnius). START_AT=23:00 has worked; night-2's 23:00 start still collided once, which is why driver v2 retries.

## Steps

1. **Directory layout** (new window = new dir, same shape):
   ```
   ~/<window>/
     RULES.md        # binding operating rules, read by every task
     driver.sh       # v2 driver (copy from ~/fable-window/driver.sh)
     run-one.sh      # single-task rerun helper
     tasks/NN-name.task
     logs/           # NN-name.log + NN-name.done markers
     artifacts/      # ALL output, incl. _ledger.md
   ```

2. **Write RULES.md** with at least these rules (all battle-tested):
   - Artifacts-only: never modify live skills/canon/wiki/memory; every exception named per-task, with a git baseline commit and a named verify command that must stay green.
   - Every change to an existing file ships as (a) full replacement file in artifacts/ + (b) a CHANGES section.
   - Every task appends one ledger block to `artifacts/_ledger.md`: task name, what was produced, file paths, open questions.
   - **HEADLESS DISCIPLINE** (rule added after 07c/07d died waiting): each run is one-shot; finish everything synchronously in-process; never spawn background jobs to await later; notifications/re-invocation do not exist headless.
   - Degrade gracefully: if an input is missing, `find` it or note the gap in the ledger; do not stall.
   - No em dashes in copy-facing text. (Scope it explicitly to creative copy, or the verify pass flags every skill doc; this ambiguity cost a review cycle.)

3. **Author task files.** Format is positional and parsed by sed, so exact:
   ```
   MODEL: claude-opus-4-8          <- line 1
   CWD: ~/brain                    <- line 2 (~ is expanded)
                                   <- line 3 blank
   Read ~/<window>/RULES.md and obey it.
   <prompt: exact inputs to load, exact artifact output paths>
   Update the ledger per RULES.
   ```
   - `NN-` prefix = execution order; name the report task `99-report` so it sorts last.
   - **Model routing:** top model for hard synthesis/canon distills, opus for mid authoring/skill rewrites, sonnet for mechanical verify/report tasks.
   - **CWD gates context:** Shameless/Code Things tasks need `CWD: ~/brain` (subagents, wiki CLAUDE.md, project memory are cwd-gated); systems tasks run from their repo dir.
   - Prompts must name exact input files and exact output paths; "study X, produce artifacts/Y" beats open-ended asks.

4. **Driver v2 semantics** (what `driver.sh` gives you; keep them when porting):
   - Sequential loop over `tasks/*.task`; **skips any task with an existing `logs/<name>.done`** = resumable, rerun after any crash.
   - `START_AT=HH:MM` waits until that time; `touch <window>/START_NOW` starts immediately; `touch <window>/STOP` aborts between (and mid-retry of) tasks.
   - Each task: `( cd "$cwd" && timeout 3600 claude -p "$prompt" --model "$model" --dangerously-skip-permissions < /dev/null ) > logs/name.log 2>&1`.
   - **Limit-retry:** on nonzero exit, grep the log for `session limit|usage limit|rate limit|credit balance`; if hit, sleep 1800 and retry, max 16 tries, then write `LIMIT-GAVE-UP` into the `.done` marker. Anything else = write `exit=$rc` and move on (fail forward; the verify pass catches bad output).
   - ntfy push per task start/done/limit to `https://ntfy.sh/tomas-tab-958e4431`.

5. **Launch in tmux** so it survives disconnect:
   ```
   tmux new-session -d -s fable 'START_AT=23:00 ~/<window>/driver.sh >> ~/<window>/logs/driver.console 2>&1'
   ```
   Watch: `tmux attach -t fable` or `tail -f ~/<window>/logs/*.log`. Rerun one task: `~/<window>/run-one.sh NN-name` (delete its `.done` first if re-running via driver).

6. **Headless gotchas to bake into prompts** (each burned a real run):
   - `--allowed-tools` is variadic and swallows a positional prompt; pass the prompt via `-p "$prompt"` or stdin, never positionally after flags.
   - `< /dev/null` on stdin, or claude may hang waiting for input.
   - Never stream output onto a synced/FileProvider path; write local, validate (non-empty, has H1), then copy.
   - A task that spawns subagents must collect them synchronously before exiting (headless discipline).

7. **Queue a verify task late** (sonnet): mechanical checks over artifacts/ - YAML frontmatter parses, JSONL lines valid + schema byte-shape matches the live file, installed files byte-identical to their artifact mirrors, ledger entry per task. Fix trivial mechanical issues in place; FLAG substantive ones, never rewrite content.

8. **Queue `99-report` last** (sonnet): read `logs/*.done`, `logs/*.log` tails, and `_ledger.md`; write `REPORT.md` with: executive summary (N/N tasks, exit codes), what passed verification, what is flagged for a decision, live/authorized writes already applied, and a morning **apply checklist** ordered by risk.

9. **Morning apply pass** (interactive, Mac or box):
   - Read `REPORT.md` first, then diff artifacts against live files before installing anything.
   - Apply order: mechanical/no-risk first; anything touching a live harness re-runs its named verify command after install (e.g. compliance-eval `python3 test_scorer.py` must stay precision=recall=1.0).
   - Skills do NOT sync between machines; scp approved SKILL.md files. Memory dir and ~/brain sync via Syncthing on their own.
   - Unapplied artifacts stay in artifacts/ as the durable record; append the apply decisions to the ledger.

10. **Iterate the queue between nights:** postmortem the `.done` markers + ledger, amend RULES.md (dated amendment block, like the night-3 headless-discipline rule), author the next `tasks/` wave, delete nothing.
