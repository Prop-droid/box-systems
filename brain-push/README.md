# brain-push — wiki -> eJam Company Brain, behind a hard gate

One write path into the company brain: write the page in `~/brain/wiki`, then
this job pushes it. Timer: Tue 08:30 (`brain-push.timer`). Manual:
`systemctl --user start brain-push.service` (or `bash run_brain_push.sh`).

Flow: `test_gate.py` -> `prepare.py` (export; `gate.py` stops pages) ->
`push.py` (create/update, then archive pages deleted from the wiki).
`prepare.py` and `push.py` live in `~/brain/exports/2026-07_ejam-brain-wiki-push/`.

## Hard rules (Tomas, 2026-11-12)

1. **One write path.** No direct `mcp__brain__*` writes from sessions.
   `direct_write_guard.py` (PreToolUse hook in `~/.claude/settings.json`) blocks
   them. Unlock only after Tomas says "push to brain" for that content:
   `touch ~/.cache/brain-direct-write.ok` (valid 30 min).
2. **A page is not pushed if it contains** a key or token, an email address
   outside `@ejam.com` / `@eatshameless.com`, a personal-side marker
   (`account-firewall/rules.json`), a local path (`/Users/`, `/home/`, `~/`,
   cloud-storage mount), a box hostname or tailnet address, a ClickUp user ID,
   or a statement that a named person left.
3. **Folder allowlist** (`gate_config.json`). A wiki folder that is not in
   `allow_folders` is not pushed and #dev gets an alert. `hold_folders`
   (hypotheses, plans) stay on the box on purpose, with no alert.
4. **Sources must be openable by a teammate.** Local paths are blocked (rule 2).
   `raw/` references are a warning only: 34 pages carried them on 2026-11-12.
5. **Deleted wiki page = archived brain entry** (`push.py` pass 3). More than 5
   in one run stops with a FAIL and archives nothing.
6. **Loud failure.** A failed run or a blocked page posts to Discord #dev.
   HTTP 401 starts `reauth_brain_mcp.py` and posts the one sign-in URL.

Not hard rules, by decision or by evidence:
- **Compliance terms = warning.** A hard block stopped 50 of 149 pages, because
  canon pages name banned terms as rules and examples.
- **Decided by Tomas, 2026-11-12:** staff can see CPA and ROAS, so
  `account/performance` stays on the allowlist; customer handles in
  customer-voice pages stay.
- **Archived 2026-11-12:** the 3 held pages and 12 `shameless-snacks` entries
  that had no wiki source. Copies: `~/Downloads/wiki-backups/2026-11-12-brain-gate/`.
- **Not ours, do not touch:** 10 `company-wide` entries have no wiki source
  because other people own them (COO compliance policy, Brain Organization
  Policy, Brand Codes, Goal Pacing definitions, persona template, and others).
  "No wiki source" does not mean "written by the box".

## Change the gate

- Add or hold a folder: edit `gate_config.json`, on Tomas's word only.
- New pattern: edit `gate.py`, add a case to `test_gate.py`.
- Dry report for the current wiki, no push: `python3 gate.py`.
- Tests: `python3 test_gate.py` (the runner executes it before each push).
- Last result: `last_run.log`; stopped pages: `gate_report.json` in the export dir.

Public share links on the box funnel (`https://<box>.ts.net:8443/...`) pass the
host rule: they are made for teammates.
