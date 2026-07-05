Operating rules for every fable-window task (binding):
1. Follow ~/.claude/skills/karpathy-guidelines/SKILL.md (surgical, additive, verify before claiming done).
2. NEVER modify live skills, canon, wiki, or memory files. All output goes to ~/fable-window/artifacts/ as new files. Exception: task 06 may install its NEW skill dir under ~/.claude/skills/ (it does not exist yet). Exception: tasks 14 and 15 may create their NEW staging dirs ~/systems/fatigue-sentinel/ and ~/systems/atria-weekly/ (new files only, never enable systemd timers); task 15 may append to the existing Atria swipe JSONL after backing it up to artifacts/. Read-only network access (BQ queries, ClickUp reads, Atria pulls) is allowed where a task says so; the only permitted external writes are the single [TEST] ntfy push in task 14 and the ntfy heartbeat it stages.
3. Every proposed change to an existing file must be delivered as: (a) full replacement file in artifacts/, plus (b) a short CHANGES section listing what changed and why.
4. End your run by appending one summary block to ~/fable-window/artifacts/_ledger.md: task name, what was produced, file paths, open questions.
5. No em dashes in any copy-facing text. Plaintext prose for creative content.
6. Work from what exists on disk; if a referenced input is missing, locate it (find) or degrade gracefully and note it in the ledger. Do not stall.

## Amendments (2026-07-04, night-3)
7. HEADLESS DISCIPLINE: you are a one-shot headless run. Finish everything synchronously in your own process. NEVER spawn background jobs to await later, never wait for notifications or re-invocation - they do not exist. Two agents (07c, 07d) failed exactly this way.
8. Night-3 exceptions to rule 2: task 22 may modify ~/systems/compliance-eval live (git baseline commit first, commit after, scorer must stay 1.0/1.0). Task 20 may run read-only BigQuery queries via the existing SA. Everything else: artifacts only.

## Amendments (2026-07-05, night-4)
9. Night-4 live exceptions to rule 2 (all Tomas-approved 2026-07-05, each with git/file baseline first): task 30 may edit wiki files under ~/brain per the sweep doc; task 34 may apply security-stage Option B rebinds; task 35 may enable the fatigue-sentinel and atria-weekly systemd timers; task 36 may edit skill description frontmatter on box skills; task 37 may replace the launch-autofill script per task-13's artifact. Everything else: artifacts only.
