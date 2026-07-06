# naming-lint apply — SUMMARY (task 37)

Date: 2026-07-05. Rule 9 (night-4) live exception: task 37 may replace the
`~/systems/launch-autofill/autofill.py` script per task-13's artifact. Applied.

## What was done

1. **Pre-install verification** — diffed live `autofill.py` (477 lines) against
   `artifacts/autofill.py.replacement` (759 lines). Change is strictly additive:
   the only removed line is the bare `main()` call in `__main__`, replaced with a
   `if LINT_ONLY: run_lint() else: main()` dispatch. All new content is the lint
   docstring, the `LINT_ONLY` flag, and the lint function block (lines 326-589:
   `CANON_ANGLES`, `angle_is_canon`, `task_class`, `name_violations`,
   `required_fields`, `default_violations`, `emdash_fields`, `lint_task`,
   `_table`, `run_lint`). The autofill write path is untouched.
   `python3 -m py_compile` on the replacement: OK.

2. **Backup** — live script copied to
   `artifacts/autofill.py.live-backup-20260705`
   (sha256 `05a5bddf…20a2`, verified equal to the live file at backup time).

3. **Install** — replacement copied over `~/systems/launch-autofill/autofill.py`;
   installed file sha256 `ff6a8cdb…9020`, verified equal to
   `artifacts/autofill.py.replacement`. 759 lines.

4. **One live dry-run** — `AUTOFILL_LINT=1 python3 autofill.py`
   (report-only mode, zero ClickUp writes). Exit 0, empty stderr.

## Dry-run result (sanity confirmed)

```
CONVENTION LINT — 261 tasks in scope (launch 207, brief 52, freeform 2)
297 violations (54 fail, 243 warn) across 209 tasks
by check: defaults=205, req-fields=54, name=20, em-dash=13, list=5
```

Output is sane and consistent with task-13's 2026-07-03 baseline
(309 violations / 214 tasks then; 297 / 209 now). The small drop is expected:
the 30-day lookback window has moved two days, so a handful of older tasks aged
out of scope. Signal is intact:

- **req-fields fails** dominated by the known variety-pack `Product` dropdown
  gap (SH-16419–16430, plus SH-1646x/1648x) — matches memory
  `project_sha_variety_pack_launch_tasks` and the task-13 note.
- **defaults=205** — the launch-defaults (Alejandra + high + type-correct
  estimate) are still routinely unset, exactly the pattern Tomas flagged.
- **em-dash=13** real hits in copy-facing fields (headline/text).
- **name** + **list** warns fire correctly (canon-angle presence, ordered-list
  collapse risk).

Table is sorted fail-first, then by check, then task — as designed.

## Write-safety confirmation

Grep of the lint code path (lines 326-589) for `api(POST/PUT)`, `comment`, or
`requests.post/put`: **zero matches.** `run_lint()` calls only `fetch_tasks()`
and the `GET /list/{id}/field` reader. No POST was issued during the dry-run.
Rule-2/Rule-9 boundary respected: the only live mutation was replacing the
script file itself (explicitly authorized); zero ClickUp writes.

## Status

Applied and verified. No rollback needed. The daily launchd/systemd job
(`run_autofill.sh` → `python3 autofill.py`, no `AUTOFILL_LINT`) continues to run
the unchanged write path; the lint is opt-in via `AUTOFILL_LINT=1` / `--lint`.

## Rollback (if ever needed)

```
cp ~/fable-window/artifacts/autofill.py.live-backup-20260705 \
   ~/systems/launch-autofill/autofill.py
```

## Open questions (carried from task-13, unresolved here)

1. SETUP.md never existed in `~/systems/launch-autofill/`; task-13 used
   `project_launch_autofill_agent.md` + `project_sha_launch_details_fill.md` as
   the setup reference. Confirm that's the intended doc.
2. Whether to wire the lint into a schedule (e.g. weekly report to Tomas Pod) or
   leave it manual-only. Not done here — apply task was install + dry-run only.
3. Task-13's angle-check tightening (exact-slot enforcement) still gated on
   task-name format standardization.
