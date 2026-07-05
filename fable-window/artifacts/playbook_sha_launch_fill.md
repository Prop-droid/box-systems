# Playbook: SHA launch-fill (approved video/image -> launch-ready task)

Deterministic sequence for filling launch details on an approved SHA creative task on list `901110066469`. Two triggers: (a) a media buyer (Ryan Salud) comments "can we please have the launch details" on an approved task; (b) Tomas asks to prep launch tasks for a batch. Sources: project_sha_launch_details_fill, feedback_launch_task_defaults, project_launch_autofill_agent, clickup-task-creator skill, clickup-markdown-ordered-list-collapse.

## When NOT to use (kill criteria, check first)

- KILL if no real script/copy source loads (Script Link field empty, no linked Doc, no inline script). **Never invent headline/text from task-name tokens** - that exact failure shipped from the autofill cron's gws bug. Ping Tomas on the task instead.
- KILL (hold LP + mirror only, fill the rest) if the task matches an LP-hold concept: founder/Giancarlo, All-Stars launch, Berry Blast launch were waiting on new LP URLs (2026-06-11). Verify the hold is still current before honoring it.
- KILL if the task is a ClickBot channel-distribution subtask ("Applovin - CPP", "TikTok", "Facebook - LC Scaling/Retargeting"). Parents only. (Talent THT subtasks `[Creator] - SHA_..._THT_..._TOM` are legitimate fill targets when explicitly asked.)
- KILL if unsure which LP or FB page and Tomas is unreachable - both are per-task calls, never auto-picked (the autofill cron's auto-by-angle rule was a one-job override, not a general license).
- NEVER overwrite an already-set field. Fill only empties.

## Steps

1. **Read the task**: `clickup_get_task detail_level="summary"` (the full payload can hit ~4MB). Confirm it is a parent task on `901110066469`, status approved / cs review, and note the type (video/CTV vs image) - it changes the estimate.

2. **The 4 launch fields** (this is what "launch details" means, exactly):
   - `FB Ad3 - LP` (id `7eca3451-c4df-4897-a543-c92a3d04ede6`) + **mirror the same URL into** `Landing Page Link` (id `ee82257f-f430-4137-9d3a-54e40bc31ab4`)
   - `FB Ad4 - FB Page` (id `77e384fd-202e-47cf-9ef6-5b9b2d7aa36f`), format `Name (page_id)` - e.g. `Shameless Snacks (114450944603601)` or `Better For You Food (102895552862171)`
   - `FB Ad6 - Headline` (id `5a13da3d-3644-44d5-bf25-2af39ee2b661`)
   - `FB Ad7 - Text` (id `580b7f41-99f5-4c9f-a721-d59f6d2c4e48`)
   - **Skip** `FB Ad9 - Headline Injection` when the LP URL already carries `?headline=`. Leave FB Ad1/Ad2/Ad5 for the media buyer.

3. **Ask LP + FB page** (one batched question): LP is a per-task call and the page is NOT always Shameless main (the Goodbye Letter batch launched on Better For You Food). For siblings of an already-launched concept, reuse the launched sibling's fill (e.g. SH-15468: Swap LP + Better For You Food + "I broke up with my fiber powder 💔"), varying headline per talent only if asked.

4. **Source the copy**, in this order:
   - `📽️ Script Link` custom field (id `d921663d-4b21-4c11-8670-bf37ad4c409d`) - the PRIMARY video-script source
   - Google Doc linked in the description (`gws drive files export -o doc.txt` with cwd inside the temp dir, then READ THE FILE - stdout is only JSON metadata)
   - inline description script
   - precedent style: `~/brain/projects/2026-05/ClickUp Connection/tasks_since_2025-09-30.jsonl`, jq the `.fb_ad` fields
   - nothing loads -> kill criterion 1: ping, do not invent.

5. **Compliance pass on headline/text**:
   - **No competitor or supplement brand names in paid FB text** even when the video hooks name them - genericize ("fiber powder", "gut health capsule"). Tomas approved this call.
   - Canon stats only (26g fiber / 70 cal / 3g sugar / 3g net carbs), daily-fiber CTA, no em dashes, banned-language list per shameless_compliance_language.

6. **Launch defaults - set ALL THREE on EVERY launch task, video AND image** (the thing that keeps getting forgotten on images):
   - Assignee = **Alejandra Beauchamp** (`114210317`) as task assignee (in addition to her `👤 Project Manager` field value)
   - Priority = **high**
   - Time estimate: **video/CTV = 480 min (8h), image-test = 180 min (3h)** (image corrected down from 8h on 2026-06-26)
   - The image `_Tom` naming + Designer-team Responsible still hold; they govern design routing only and do not exempt the task from these three.

7. **Write** via `clickup_update_task`. Field-value formats: text fields plain strings; users `{"add":[<int>]}`. Fill empties only.

8. **Verify after write** (`success: true` lies):
   - Re-read with `clickup_get_task detail_level="summary"`; confirm all 4 fields + assignee + priority + estimate persisted.
   - **Re-check the description body is intact** - a field-only update (priority/assignee/estimate) can collapse a numbered list in the description to its first item, silently dropping hooks 2-N (seen on SH-16451). If the body used ordered lists, restore as bullets.
   - Report per task: `SH-#### launch-filled: LP✓ mirror✓ page✓ headline✓ text✓ Alejandra✓ high✓ 480/180✓ body✓`.

9. **Batch note**: when one concept has talent siblings (e.g. SH-15467/68/69), fill each as it reaches approved; do not pre-fill unapproved siblings.
