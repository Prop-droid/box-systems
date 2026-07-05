# Verification pass — 2026-07-03

Scope: everything in `~/fable-window/artifacts/`, per the 4 checks requested + RULES.md compliance. Trivial mechanical problems fixed in place (listed below); substantive issues flagged, not rewritten.

## 1. `*.SKILL.md` frontmatter + content checks

| File | YAML valid | name matches dir | desc < 1024 | no em/en dash | no unresolved placeholders | Verdict |
|---|---|---|---|---|---|---|
| clickup-task-creator.SKILL.md | PASS | PASS (`clickup-task-creator`) | PASS (974) | **FAIL (57 em-dash)** | PASS | FAIL |
| dr-script.SKILL.md | **FIXED → PASS** | PASS (`dr-script`) | PASS (916) | **FAIL (41 em-dash)** | PASS | FAIL |
| email-copy.SKILL.md | **FIXED → PASS** | PASS (`email-copy`) | PASS (865) | **FAIL (21 em-dash)** | PASS | FAIL |
| landing-page-copy.SKILL.md | **FIXED → PASS** | PASS (`landing-page-copy`) | PASS (888) | **FAIL (50 em-dash)** | PASS | FAIL |
| micro-scripts.SKILL.md | **FIXED → PASS** | PASS (`micro-scripts`) | PASS (786) | **FAIL (37 em-dash)** | PASS | FAIL |
| shameless-script.SKILL.md | PASS | PASS (`shameless-script`) | PASS (949) | **FAIL (21 em-dash)** | PASS | FAIL |
| system-control.SKILL.md | PASS | PASS (`system-control`) | PASS (959) | **FAIL (32 em-dash)** | PASS | FAIL |

**Mechanical fix applied (frontmatter syntax):** `dr-script.SKILL.md`, `email-copy.SKILL.md`, `landing-page-copy.SKILL.md`, `micro-scripts.SKILL.md` had single-line plain-scalar `description:` values containing an unescaped `word: word` pattern (e.g. `Does NOT fire for: Shameless Snacks...`, `hand-off shape: 5 numbered...`). A plain YAML scalar cannot contain `": "` — parsing (checked with js-yaml, a spec-compliant parser) threw `incomplete explicit mapping pair` on all four. Fixed by switching `description:` to the folded block-scalar form (`description: >` + indented body), the same style already used successfully in `clickup-task-creator.SKILL.md`. No wording changed — confirmed byte-identical description text before/after, re-verified all 7 files now parse clean with matching name/description/desc_len.

**Substantive issue flagged, NOT auto-fixed — em dashes in SKILL.md body/description text:**
All 7 files contain em dashes throughout (21–57 each, ~276 total), in both the frontmatter `description:` field and body prose. This task's instruction (1) says "no em dashes anywhere" for every `*.SKILL.md`. However, `_ledger.md` shows the authors of 3 of these files (clickup-task-creator, system-control, context-audit) made an explicit, stated scoping call: RULES.md #5 ("no em dashes in copy-facing text") was read as applying only to Shameless/DR *creative* output, not to skill *documentation* prose, and em dashes were deliberately kept for readability in operational docs. That's a defensible reading of RULES.md #5 in isolation, but it conflicts with this verification task's literal instruction. Removing ~276 em dashes across 7 files by hand is not a mechanical find/replace — each one needs a human judgment call (comma, period, parenthetical, or restructure) to avoid mangling sentences, so it is out of scope for an in-place "trivial fix" here.
**Flag for Tomas:** either (a) confirm the "operational docs are exempt from the em-dash rule" reading and I'll drop this criterion from future verify passes, or (b) say the word and I'll run a real editing pass (not a blind strip) on all 7 files.

No unresolved TODO/TKTK/FIXME markers found. The `<...>` tokens present (e.g. `<PROD>_<CanonAngle>_<ScriptName>`, `<userid_int>`, `<unit>`) are all intentional naming-template placeholders documented as such, not leftover drafting markers — not a defect.

## 2. compliance-eval new cases + gold

| Check | Result |
|---|---|
| `compliance-eval.new_cases.jsonl` — every line parses as JSON | PASS (20/20 lines, ids n01–n20) |
| Field set matches `~/systems/compliance-eval/prompts.jsonl` (`{prompt, angle, id, format}`) | PASS (exact match, no extra/missing keys, all 20 rows) |
| `compliance-eval.new_gold.json` parses | PASS (valid JSON, dict) |
| Covers every new case id | PASS — keys are `_doc` + `n01.txt`…`n20.txt`; cross-checked against the 20 case ids, zero missing, zero extra |

Note (not a failure): `new_gold.json` entries carry extra fields (`bait`, `why`) beyond the live `gold_labels.json` convention (`hard`, `warn_includes`). Ledger already documents this is deliberate and inert to the harness, and that this file is explicitly not meant to be merged into the live `gold_labels.json`. No action needed.

## 3. `feedback_winner_patterns_2026H1.md` memory frontmatter

| Check | Result |
|---|---|
| Valid YAML | PASS |
| `name` present | PASS (`feedback_winner_patterns_2026H1`) |
| `description` present | PASS |
| `metadata.type` present | PASS (`feedback`) |

**Observation (flag, not fixed):** an identical copy of this file already exists live at `/home/tomas/.claude/projects/-home-tomas/memory/feedback_winner_patterns_2026H1.md` and is indexed in the live `MEMORY.md`. RULES.md #2 restricts fable-window writes outside `artifacts/` to the task-06 skill-install exception only — this memory file's promotion to live memory isn't covered by that exception. Did not touch the live file (RULES #2: never modify live memory), just noting it's already there, presumably promoted deliberately in a prior session dated 2026-07-02 (the artifact's own header date). Worth confirming that promotion was intentional.

## 4. Task 06 — system-control skill install

| Check | Result |
|---|---|
| `~/.claude/skills/system-control/SKILL.md` exists | PASS |
| Byte-identical to `~/fable-window/artifacts/system-control.SKILL.md` | PASS (`diff` clean) |

No action needed — confirmed correctly installed.

## Summary

- 4/7 SKILL.md files had a real YAML bug (invalid plain-scalar colon usage) — fixed in place, frontmatter now parses clean on all 7.
- All 7 SKILL.md files fail the "no em dashes anywhere" criterion as literally stated in this task — flagged as a policy conflict with a prior deliberate scoping decision recorded in the ledger, not silently rewritten.
- compliance-eval new cases/gold: clean, full coverage, no fixes needed.
- Memory frontmatter: clean; flagged that the file is already live (likely intentional, not this task's job to adjudicate).
- Task 06 install: confirmed correct.
