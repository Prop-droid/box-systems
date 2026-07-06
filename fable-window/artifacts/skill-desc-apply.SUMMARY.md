# Task 36 — Apply trimmed skill descriptions to box skills

Ran under RULES.md rule 9 (box skill-frontmatter edits permitted for this task). Applied the 15
trimmed skill descriptions from `skill-descriptions.trimmed.md` — this is exactly Opportunities 1
(8 mega descriptions) + 2 (1 firecrawl umbrella) + 4 (6 more long descriptions) = 15. The doc's
"Section 4 - routing-accuracy fixes" (maintain, claude-code, creative-ideation, humanizer, and the
claude-heavy-lifting append / delegate-to-claude no-change notes) is a separate category and was
NOT part of the 15 — left untouched, as scoped.

## Drift check

Compared each live description's character count against the doc's stated "CURRENT chars" before
touching anything. All 15 matched (folded/literal block descriptions needed a lenient parser since
several already contain unescaped colons that break strict `yaml.safe_load` but parse fine under
Claude Code's actual frontmatter reader — this is a pre-existing pattern, e.g. fleet-control's live
description already had this before any edit today). No skill was skipped for drift.

## Applied (15/15)

| Skill | Style | Backup | Result |
|---|---|---|---|
| system-control | plain | SKILL.md.bak-2026-07-05 | applied |
| clickup-task-creator | folded (`>`) | SKILL.md.bak-2026-07-05 | applied |
| shameless-script | plain | SKILL.md.bak-2026-07-05 | applied |
| fleet-control | plain | SKILL.md.bak-2026-07-05 | applied |
| dr-script | folded (`>`) | SKILL.md.bak-2026-07-05 | applied |
| landing-page-copy | folded (`>`) | SKILL.md.bak-2026-07-05 | applied |
| gbrain-tag-audit | plain | SKILL.md.bak-2026-07-05 | applied |
| email-copy | folded (`>`) | SKILL.md.bak-2026-07-05 | applied |
| firecrawl | literal (`\|`) | SKILL.md.bak-2026-07-05 | applied (dir is a symlink to ~/.agents/skills/firecrawl) |
| micro-scripts | folded (`>`) | SKILL.md.bak-2026-07-05 | applied |
| script-critique | plain | SKILL.md.bak-2026-07-05 | applied |
| interrogate | plain | SKILL.md.bak-2026-07-05 | applied |
| lt-marketplace-search | plain | SKILL.md.bak-2026-07-05 | applied |
| share-to-phone | plain | SKILL.md.bak-2026-07-05 | applied |
| firecrawl-interact | literal (`\|`) | SKILL.md.bak-2026-07-05 | applied (dir is a symlink to ~/.agents/skills/firecrawl-interact) |

Skipped: none (0/15). Every `name:` field verified byte-identical before/after. Every file's body
(everything after the closing `---`) verified byte-identical before/after — only the `description:`
field changed.

## Verification method

For each file: (1) `name:` line compared old vs new — unchanged; (2) description value extracted
and compared against the exact trim-doc text — exact match; (3) frontmatter structure checked
(opens with `---`, has exactly one closing `---`, no stray blank line inserted); (4) full markdown
body after the closing `---` diffed byte-for-byte against the pre-edit version — unchanged.

## Self-inflicted bug caught and fixed mid-task (full disclosure)

My first apply script had a reconstruction bug: for `plain`/`literal`-style descriptions it inserted
one spurious blank line right before the closing `---` (folded-style ones were unaffected because
their parser logic happened to consume the trailing blank marker already). I caught this via a
line-count diff, rewrote 10 files with a byte-precise regex-splice fix, and reverified — no bug.

While writing a *second* verification pass, an errant `from apply_skill_descs import ...` re-executed
that first (buggy) script's whole module body as a side effect, silently re-corrupting the same 10
files AND overwriting their `.bak-2026-07-05` originals with the (buggy) new-description state,
losing the true pre-edit backup for those 10 plus clickup-task-creator, firecrawl, firecrawl-interact
(11 of 15 backups clobbered in total). I:
1. Deleted both transient scripts immediately so this can't recur.
2. Re-confirmed the actual live description text was still correct (only whitespace structure was
   wrong) for the 10 broken files, and did a minimal single-line-delete surgical fix (no full rewrite).
3. Recovered the TRUE original text for 11 of the 15 skills from this conversation's own earlier
   tool output (a `grep` run before any edits captured 8 full plain-style descriptions verbatim; a
   `diff` run captured clickup-task-creator's full original; and firecrawl / firecrawl-interact were
   recovered from a byte-length-verified match against `~/.hermes/skills/openclaw-imports/`, an
   untouched external copy — every recovered string's length matches the trim doc's stated
   "CURRENT chars" exactly, so I'm confident these are byte-accurate). Rebuilt those 11 `.bak-2026-07-05`
   files to hold the true pristine original again.
4. Could **not** recover the true original for 4 skills: **dr-script, landing-page-copy, email-copy,
   micro-scripts**. No other copy of these existed anywhere on disk and I never printed their full
   original text earlier in this session. Their **live SKILL.md is correct** (verified: new
   description applied cleanly, body untouched, no structural bug — these 4 were never actually
   hit by the whitespace bug in the first place). Only their `.bak-2026-07-05` safety copy is not a
   true pre-edit snapshot — it currently holds the same (correct) new-description state as the live
   file, so it would not help a rollback. Flagging this explicitly per RULES #6 (note gaps, don't stall).

Net result: all 15 live files are correct and verified. 11/15 backups are true pristine originals;
4/15 backups (dr-script, landing-page-copy, email-copy, micro-scripts) are not true rollback points
(this is the only known gap from the whole run).

## Exact list for the Mac session to mirror

Apply these same 15 `description:` field replacements to the equivalent Mac `~/.claude/skills/<name>/SKILL.md`
files, preserving each file's existing YAML style (plain/folded/literal) and touching nothing else.
Back up first to `SKILL.md.bak-2026-07-05` before editing (recommend: verify byte-count of the backup
matches the pre-edit live file before overwriting, to sidestep the accidental-reimport class of bug
above — do NOT `import` an apply script as a library, only ever run it once via `python3 script.py`).

1. system-control
2. clickup-task-creator
3. shameless-script
4. fleet-control
5. dr-script
6. landing-page-copy
7. gbrain-tag-audit
8. email-copy
9. firecrawl
10. micro-scripts
11. script-critique
12. interrogate
13. lt-marketplace-search
14. share-to-phone
15. firecrawl-interact

New description text for each is verbatim in `skill-descriptions.trimmed.md` (Opportunities 1, 2, 4).
Do NOT apply the Section 4 routing-fix entries (maintain, claude-code, creative-ideation, humanizer)
under this task — those were intentionally out of scope for "the 15."
