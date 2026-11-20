# team-capacity — SHA creative-team weekly capacity report

Spec/plan: `~/brain/projects/2026-10/sha-team-capacity-system/` (Mac). Built 2026-10-27.

- `run_weekly.py` — Saturday 06:00 Vilnius (`team-capacity-weekly.timer`). Window = last run end → now (first run: this ISO week's Monday 00:00).
  Pull ClickUp (list 901110066469, pool of 8) → metrics split VIDEO/IMAGE → ledger JSONL → Mon–Fri spread plan (journal only) → report → deliver.
  Estimates in the report = ORIGINAL estimate (first cut's `est_before_ms` in `ledger/rollover.jsonl`), so carried tasks don't shrink "estimated on finished".
- `send_weekly.py` — Monday 07:00 Vilnius (`team-capacity-send.timer`). Posts `reports/<last_label>.txt` into ClickUp Chat `settings.json` `dm_channel` (Tomas <-> Katherine Guerra DM 8cj5bz5-227631, as Tomas via the pk token; Tomas 2026-11-03 "dm, not email"). Refuses a stale label (no Saturday run) and never double-sends; `--label/--channel/--email/--subject-prefix/--dry-run/--force`. Test target: private 1-member chat channel "team-capacity dry run" 8cj5bz5-380311 (never the Katherine DM).
- `rollover.py --auto` — Monday 07:10 Vilnius (`team-capacity-rollover.timer`), after the report DM (Tomas 2026-11-09). Pool tasks in to do / in progress / needs fixing due before this Monday → same weekday this week (Sat/Sun → Fri, date-only kept); native time estimate minus time tracked since the task's last cut (first cut = all tracked to date), floored at 1h, never raised, blank stays blank. Blocked / backlog / handed-off untouched; no tags, no extra fields. Cuts → `ledger/rollover.jsonl`; every write read back; summary to ops-log. Sat/Sun runs skip. Manual: `python3 rollover.py --target 2026-11-09 [--apply]`.
- `run_gate.py` — every 15 min (`team-capacity-gate.timer`). In-progress task with blank estimate → `to do` + comment. Logs to `gate.log`.
- `settings.json` — `rollover_writes` (true since 2026-11-09), `writes` (estimate gate only; false = log only), `post_team` (false = Tomas-only ops-log preview; true = Discord #creative), `doc_id` (Google Doc to append), `sheet_id` (ledger mirror), `dm_channel` (Monday ClickUp Chat target).
- Rules: finished = FIRST entry into cs review / approved / sent to mb / mb - testing (handoff week; bounce-backs never recount). Backlog never counts. Tracked = timer intervals booked to the week of their start. Output = 🟧 OUTPUT line, else Air unique creatives.
- Replay: `python3 run_weekly.py --dry-run --window 2026-10-19 2026-10-25`
- Tests: `python3 -m unittest discover -s tests -v`
- Go-live: rollover is live (`rollover_writes`). The gate (`writes`) and `post_team` are still off until Tomas flips them.
