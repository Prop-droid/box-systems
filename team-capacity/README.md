# team-capacity — SHA creative-team weekly capacity report

Spec/plan: `~/brain/projects/2026-10/sha-team-capacity-system/` (Mac). Built 2026-10-27.

- `run_weekly.py` — Saturday 06:00 Vilnius (`team-capacity-weekly.timer`). Window = last run end → now (first run: this ISO week's Monday 00:00).
  Pull ClickUp (list 901110066469, pool of 8) → metrics split VIDEO/IMAGE → ledger JSONL → rollover + Mon–Fri spread plan → report → deliver.
- `run_gate.py` — every 15 min (`team-capacity-gate.timer`). In-progress task with blank estimate → `to do` + comment. Logs to `gate.log`.
- `settings.json` — `writes` (false = plan only, no ClickUp writes), `post_team` (false = Tomas-only ops-log preview; true = Discord #creative), `doc_id` (Google Doc to append), `sheet_id` (ledger mirror).
- Rules: finished = FIRST entry into cs review / approved / sent to mb / mb - testing (handoff week; bounce-backs never recount). Backlog never counts. Tracked = timer intervals booked to the week of their start. Output = 🟧 OUTPUT line, else Air unique creatives.
- Replay: `python3 run_weekly.py --dry-run --window 2026-10-19 2026-10-25`
- Tests: `python3 -m unittest discover -s tests -v`
- Go-live: flip `writes` and `post_team` to true in settings.json after reviewing one preview.
