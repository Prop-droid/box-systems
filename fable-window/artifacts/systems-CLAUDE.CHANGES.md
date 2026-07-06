# CHANGES — systems-CLAUDE.FIXED.md (proposed patch to ~/systems/CLAUDE.md)

Two one-line edits (lines 21 and 244 of the live file). Not applied live — task 96
(verify-dev) has no live-edit exception for `~/systems/CLAUDE.md`; ship as artifact
per RULES rule 3.

## What changed

- Line 21 (bq-clickup-perf subsystem entry) and line 244 (VERIFY block): the
  documented dry-run command `PERF_DRY_RUN=1 python3 bq_to_clickup_perf.py` now
  reads `TOKEN_FILE=~/.config/clickup/pk PERF_DRY_RUN=1 python3 bq_to_clickup_perf.py`.

## Why

Ran the documented command exactly as written during dev-lane verification
(task 96): it crashes —

```
Traceback (most recent call last):
  File ".../bq_to_clickup_perf.py", line 54, in <module>
    TOKEN = open(TOKEN_FILE).read().strip()
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/clickup_pk'
```

`bq_to_clickup_perf.py:40` defaults `TOKEN_FILE` to `/tmp/clickup_pk` (a Mac-era
path) unless the `TOKEN_FILE` env var is set. `run_perf_writeback.sh` (the real
cron entry point) always sets `TOKEN_FILE="$HOME/.config/clickup/pk"` before
calling the script, so the live nightly job is unaffected — only the bare
manual dry-run command as documented in CLAUDE.md was wrong. With the env var
added, the dry run runs clean (verified: "DRY RUN ... would write 5 fields to
175 tasks ... No changes made.").

Not touching `bq_to_clickup_perf.py` itself — its own inline docstring (line 21
of that file) has the same gap, but that file is pre-existing source outside
this task's scope; note only.
