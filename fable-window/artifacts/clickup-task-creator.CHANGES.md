# clickup-task-creator SKILL.md — CHANGES

Full replacement for `~/.claude/skills/clickup-task-creator/SKILL.md`. Goal: fold every recurring ClickUp gotcha into the skill body so a future session needs zero memory recall to avoid them. `references/fields-and-formats.md` is unchanged (still the long-tail lookup).

## What changed and why

1. **New "five gotchas" preamble** (top of skill). One scannable block that names the five things that keep recurring, each with the failure it prevents. Puts the load-bearing rules where they can't be missed. Source: the six memory files this task folds in.

2. **NEW Task Creation profile + medium-match rule** (Step 2 row + dedicated subsection + Step 4b body template). The old skill had NO coverage of Task Creation directive tasks at all — they were memory-only. Added:
   - Aicha/Ayca (`81523925`) = IMAGE, Anastasia/Ana (`81523938`) = VIDEO, and the hard rule that the **body noun must match the assignee**. This is the 2026-07-02 lesson: a whole batch shipped saying "video" when routed to Aicha (image).
   - The plain directive body shape (2-line intro + Angle + Topic block), explicitly NOT the 3-block colored-square template.
   - Aicha-vs-Ayca spelling rule (prose = "Aicha"; "Ayca" only in the task-name slot).
   - Source: `feedback_clickup_task_creation_tasks.md`, `project_aicha_workflow.md`.

3. **Numbered-list collapse rule promoted to a hard rule** (gotcha #2, Step 4 "BULLETS ONLY", Step 6.4, Step 7, failure modes). Old skill never mentioned it. Now: bullets only, re-verify the description body after every `update_task` (even field-only patches collapse ordered lists). Source: `clickup-markdown-ordered-list-collapse.md`.

4. **Designer-team GROUP GUID hardened** (gotcha #3, Step 5 defaults, Step 6.2). Old skill had the GUID but not the crisp "team userid `75478960` is silently rejected" framing at the point of use. Now stated as a gotcha and repeated at the create/patch step. Source: `feedback_image_task_responsible_designer.md`.

5. **NEW launch-task defaults** (gotcha #4, Step 2 Launch row, Step 5b). Old skill had no launch profile. Added: assignee Alejandra + priority high + time estimate (480 min video/CTV, 180 min image) on EVERY launch task, with the explicit note that `_Tom` naming does not override the Alejandra-assignee/high-priority rule. Source: `feedback_launch_task_defaults.md`.

6. **Angle-canon + script-name naming folded into Step 3.** Old skill said "match the convention"; now names the canon-angle vocabulary explicitly ("never invent — DailyFiber was rejected → Fiber"), requires a script-name token for video tasks, and states OUTPUT = count only. Source: `feedback_sha_task_angle_canon_naming.md`.

7. **Verify discipline strengthened** (Step 7). Added an explicit "confirm the description body is intact" check (for the ordered-list collapse) and launch-field verification (priority/assignee/estimate). Report line now includes `body✓`.

8. **Dropdown format corrected to orderindex-first.** The old SKILL.md said "pass the option UUID as a string" for dropdowns; `references/fields-and-formats.md` §2/§3 says the WL build verified `create_task` wants the **orderindex int**, UUID as fallback. Aligned the skill to the reference (orderindex default, UUID fallback) to remove the internal contradiction.

9. **WL naming corrected** in the Step 2 table to the 2026-06-12 spec (`SHA_YYYY_S##_Creator#_CAMPAIGN_TOM_`, no WL token, no editor code) and WL copy-placement note (no 🟥 COPY block). Old skill still showed the outdated `..._WL_..._Tom_` pattern. Source: references §10.

10. **Description updated** to mention the Task Creation trigger phrases so the skill fires on "create the Task Creation task for Aicha/Ana".

## Not changed
- Custom-field UUIDs, editor-code map, LP list, FB-page IDs — unchanged; still in `references/fields-and-formats.md`.
- The 3-block image-brief template semantics (🟧/🟦/🟥, 10-vs-15 rule, swap-level explicitness) — preserved verbatim.
- Safety gate (preview-before-create) — preserved.

## Install note
Drop-in replacement for the SKILL.md only; references dir stays as-is. Per RULES this artifact is NOT installed live — it sits in `~/fable-window/artifacts/` for Tomas to review and copy over.
