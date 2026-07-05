---
name: clickup-task-creator
description: >
  Create or update real ClickUp tasks/briefs on Tomas's Shameless "Creative Strategist List" (901110066469) via the ClickUp MCP — correct naming, the locked 3-block description, the right custom-field UUIDs and value formats, and task-type-aware assignee routing. This is the EXECUTION layer: it actually pushes briefs into ClickUp. Use it whenever Tomas says "create the task(s)", "push this brief to ClickUp", "brief this to [editor]", "make the image-test tasks", "spawn N tasks for [angle]", "create the WL deliverables", "set up the retro", "create the Task Creation task for Aicha/Ana", "duplicate this brief 3× for the editors", or otherwise wants briefs to land in ClickUp. Pairs with creative-brief-builder (which writes the creative CONTENT); this skill takes that content and creates the actual tasks. Do NOT use for analytical questions about existing tasks (use the winners archive) or for writing ad copy/scripts (use shameless-script / creative-brief-builder).
---

# ClickUp Task Creator — Shameless Creative Strategist List

This skill turns a brief into correctly-structured ClickUp tasks **without re-reading the 103-field manual and without any memory recall** — every gotcha that has bitten before is folded in below. The full lookup tables (every field UUID, the complete editor map, naming tokens, LP/FB-page references) are in `references/fields-and-formats.md` — read it only when you need a value not inlined here.

**Boundary:** `creative-brief-builder` / `shameless-script` produce the creative *content* (hooks, copy, script). This skill takes that content and creates the *tasks*. If the user hasn't supplied copy yet and wants it written, do that first (or in chat), then push.

## The five gotchas that keep recurring (read once, they gate everything)

1. **Task Creation tasks must name the right MEDIUM for the assignee.** A "Task Creation" directive assigned to **Aicha/Ayca = IMAGE**; assigned to **Anastasia/Ana = VIDEO**. The directive body must say "image tasks" for Aicha and "video tasks" for Ana. On 2026-07-02 a whole batch shipped saying "video" when image was meant, routed to Aicha — wrong medium, wrong team downstream. Match the noun to the coordinator every time. (See the Task Creation profile below.)
2. **Never use numbered/lettered markdown lists in a description.** ClickUp's MCP collapses `1. 2. 3.` / `A. B.` to just the first item on ANY later re-save — even a field-only update (priority/assignee/estimate) that doesn't touch the description. Use bullets (`- `) only, and **re-verify the description after every `clickup_update_task`**.
3. **Image-test `👤 Responsible` = the Designer team GROUP GUID** `cf65787a-6fe1-4473-8e2a-889720cda89b`, set via `{"add":["<guid>"]}`. The team's integer userid (`75478960`) is silently rejected. Leaving it blank breaks the design team's intake.
4. **Launch tasks (video AND image) always get assignee Alejandra + priority high + a time estimate** (480 min video/CTV, 180 min image). These get dropped on image tasks by default — bake all three in at create time.
5. **`success: true` lies.** The MCP returns success even when a users-field or dropdown value silently failed to save. Always verify with `clickup_get_task detail_level="summary"` after create AND after each patch.

## Safety gate — confirm before writing to ClickUp

Creating tasks is an outward-facing action visible to the whole team and tedious to undo at batch scale. So:

1. **Always show the planned task(s) first** — names, status, assignees, key fields, and the description body — as a compact preview, and get an explicit go-ahead before any `clickup_create_task` call. The one exception is when Tomas has already said "just create them" / "go" in the same turn.
2. After creating, **verify** (see Step 7). Never trust the boolean alone for dropdown or user-type fields.

## Step 1 — Gather inputs

Figure out, from the request or by asking in ONE batched question if genuinely missing:

- **Task type** (drives almost everything — see Step 2): image-test / retro / iteration · **Task Creation directive** (coordinator fans out children) · whitelisting (WL) video · general video ad · relaunch / asset-handoff · launch.
- **Count & batch shape**: how many tasks; is it the same brief in parallel for several editors (A/B/C test), or distinct briefs?
- **Naming inputs**: sprint number (S##, ISO week — *always ask, don't derive from a calendar guess*), product (OG/AS/CC), **canon angle** (see Step 3 — angle names are a FIXED vocabulary, never invent one), script-name token (for video), variant, test-type.
- **Landing page** — ALWAYS ASK Tomas which LP the test routes to. Never auto-pick from the angle (e.g. Fiber angle ≠ Fiber First LP by default). LP choice changes per funnel stage / offer era / sprint test. Common choices: Fiber First (`/gummies/meta/fiber-packed/trw-gifts/`), GLP-1 (`/gummies/meta/fiber-packed/glp-1/`), Swap, Carnaval-Goli, or new. Set both `FB Ad3 - LP` and `Landing Page Link` (mirror).
- **Copy**: headline + body for the FB fields, or the 3-block description content. If iterating a winner, the source filename.
- **Editor**: which editor code (AYC / JDC / FER / etc.) — this drives the task name suffix, the `👤 Designer` field value, AND the top-level task **assignee**. CRITICAL: set the assignee to the designer too. The `👤 Designer` custom field alone does NOT assign the task.
- **Reference image** (if adapting a competitor or prior ad): the local file path or URL. The image gets BOTH embedded inline in the INSTRUCTIONS via markdown `![]()` AND attached via `clickup_attach_task_file` so designers see it without expiring CDN URLs.

If something non-derivable is missing, ask once using the batched-question style — single message covering LP, sprint #, product, canon angle, editor, output-count deviation. Don't iterate question-by-question.

## Step 2 — Pick the task-type profile

Each profile sets naming tail, Deliverable Type, the `👤 Responsible` routing, priority, and description shape. These differ in ways that have bitten before — get the profile right first.

| Profile | Naming tail | Deliverable Type | `👤 Responsible` group | Priority | Description |
|---|---|---|---|---|---|
| **Image-test / retro / iteration** (most common) | ends at `_Tom` (no editor code — Alejandra assigns) | Product Image (or Advertorial Image / CTV Image) | **Designer** group GUID `cf65787a-6fe1-4473-8e2a-889720cda89b` | normal (unless launch) | 3-block (Step 4) |
| **Task Creation directive** (coordinator fans out N child tasks) | `[Concept] Image Task Creation Ayca` / `[Concept] Video Task Creation Ana` | n/a — the CHILDREN get types | n/a — assign the coordinator | normal | plain directive (Step 4b) — NOT the 3-block template |
| **Whitelisting (WL) video** | `SHA_YYYY_S##_Creator#_CAMPAIGN_TOM_` (uppercase `TOM_`, no WL token, no editor code) | WhiteListing | **Video Editor** group GUID `1a5392c6-9f0d-4ccd-8c4d-5dde128c1d62` | **high** (usage-term expiry) | 🟧 OUTPUT + 🟦 INSTRUCTIONS only, NO 🟥 COPY; copy goes in FB fields; link to parent creator via `clickup_add_task_link` |
| **General video ad** | `SHA_YYYY_S##_<PROD>_<CanonAngle>_<ScriptName>_<Style>_<Type>_Tom` | Video - Intro (or specific `Video - *`) | Video Editor group | normal | 3-block or short brief |
| **Relaunch / asset-handoff** (Aicha pulls finished assets from Air) | per slug, ends `_Aicha` | (often Product Image) | n/a — assign Aicha directly | normal | lighter Air-links body (references §9) |
| **Launch** (video OR image, going live) | per the underlying profile | per content | per content | **high** + assignee Alejandra + estimate (see Step 5b) | per content |

**WL note:** for whitelisting, also set `📱 Influencer Name`, `🚨 Channel` = Facebook, `✨ Product`, and link back to the parent in the Influencer Whitelisting folder. Assignee = Alejandra only; leave `👤 Video Editor` EMPTY (she routes editing). Full WL field set in references §10.

### Task Creation profile — the medium-match rule (the 2026-07-02 lesson)

A "Task Creation" task is a **directive**, not a creative deliverable: Tomas writes the concept once, assigns it to a coordinator, and the coordinator spawns the individual per-designer/editor child tasks. Get these right:

- **Task type** = `Deliverable` (custom_item_id 1013), **status** `to do`.
- **Assignee routes the medium — and the body noun MUST match it:**
  - **Aicha / Ayca (`81523925`) → IMAGE.** Name: `[Concept] Image Task Creation Ayca`. Body says "create N **image** tasks".
  - **Anastasia / Ana (`81523938`) → VIDEO.** Name: `[Concept] Video Task Creation Ana`. Body says "create N **video** tasks".
  - Do not write "video" in a task going to Aicha or "image" in one going to Ana. This exact mismatch shipped a whole batch wrong on 2026-07-02. If Tomas hands you a concept without naming the coordinator, infer from the medium (image concept → Aicha; video concept → Ana) and confirm in the preview.
- **Spelling in prose:** write **"Aicha"** everywhere (briefs, chat, docs). "Ayca" is only her ClickUp username display string; use it solely in the task-name slot to match house pattern. `AYC` / `AYCA` / `AICHA` all map to id `81523925`.
- **Description = the plain directive (Step 4b)**, not the 3-block colored-square template.
- The **child tasks** the coordinator later creates follow the normal image/video brief conventions in this skill.

## Step 3 — Build the name

Active 2026 pattern:
`SHA_<YYYY>_S<SPRINT#>_<PRODUCT>_<CanonAngle>_[<ScriptName>_]<VARIANT>_<TEST_TYPE>_Tom[_<EDITOR_CODE>]`

- **Angle names are CANON — never invent one.** Use the existing token (`Fiber`, `GLP1`, `GutHealth`, `Weightloss`, `Bloodsugar`, `Keto`, `LowCal`, `Menopause`, `DadBod`, `LastCall`, `10Reasons`, `Retention`, etc.). "DailyFiber" was rejected and corrected to `Fiber`. When unsure, pull the token from existing task names — do not coin a variant.
- **Video tasks need a SCRIPT-NAME token** — a short handle identifying the specific script, e.g. `SHA_2026_S25_OG_Fiber_EasiestFix_UGC_CTV_Tom`. This makes each script traceable.
- Match the existing convention exactly; mirror sibling tasks in the batch.
- Image/retro/iteration tasks **end at `_Tom`** (the trailing `_EDITOR` slot is no longer filled by CS as of 2026-05-28 — Alejandra fills the designer code when she assigns).
- `CTV` = the internal image-creation platform (NOT "Connected TV", NOT an angle) — a production-format token paired with Deliverable Type `CTV Image`/`CTV Video`.
- Honor whatever Tomas specifies even if it breaks the 3-letter convention (he sometimes puts a role label like `GraphicDesigner` in the editor slot).
- Product/angle/variant/test-type/format tokens → references §6.

## Step 4 — Write the description (3-block format)

For image-test / retro / iteration briefs, the description uses this exact format. **Send it via `markdown_description`** (not `description`) so bold + emoji render:

```
🟧 **OUTPUT:** <N images / videos — usually 10; **15 = 5 concepts × 3 stat-lead variants** when both image and copy are new (competitor-swap / cold reverse-engineer)>

🟦 **INSTRUCTIONS:**
- <swap-level instruction — say what gets swapped to what, e.g. "Instead of the offer percentage write 'X'">
- If reference image is supplied: embed it inline with `![Source ad](<url>)` after the instruction bullets, AND attach it via `clickup_attach_task_file`.
- Create new variations based on given image (<source-filename>).

🟥 **COPY:**
<new copy, verbatim, one line per element>
```

Rules that matter:
- **BULLETS ONLY — never `1. 2. 3.` or `A. B.` numbered/lettered lists.** ClickUp's MCP collapses ordered lists to their first item on any later re-save (even a field-only update), silently dropping hooks 2–N. Render hook lists and variant lists as bullets. Re-verify the description after every subsequent `update_task`.
- **OUTPUT line = just the count** ("10 images" / "10 videos" / "10 edits"). Put style/length/format ("UGC talking-head, ~20–30s") in 🟦 INSTRUCTIONS, not OUTPUT.
- Be explicit at the swap level. The designer should never have to infer what changes. "Iterate on this image" alone is a failure.
- Put the source image filename in parentheses on the final INSTRUCTIONS bullet.
- 🟧 = OUTPUT, 🟦 = INSTRUCTIONS, 🟥 = COPY. Emoji squares, not rich-text highlight or 🎯/📋/✍️. ClickUp markdown only supports `==yellow==`; blue/red `<span>` becomes literal text.
- **Keep OUT of the description**: performance stats ($ spend, ROAS, days running), strategist rationale ("before fatigue kills it", "only 2× winner"), why-this-brief justification, cross-references to other SH-#### beyond the source filename. That context goes in chat/Slack, not the canonical record.
- All copy follows brand voice + canon (no em dashes; 26g fiber / 70 cal / 3g sugar / 3g net carbs; daily-fiber CTA). Run it through `shameless-script` / `compliance-checker` if it isn't already vetted. (Em dashes inside operational INSTRUCTIONS are fine; the ban is on copy-facing text.)

### Step 4b — Task Creation directive body (plain, NOT 3-block)

For a Task Creation directive, the body is a plain directive. Confirmed shape (2026-07-02):

```
Hey, you need to create three image tasks based on this topic below.
Also, research reference examples and formats to guide the copywriting and the image tasks.

**Angle:** <canon angle>

**Topic: <name>**
- Trigger: <...>
- Visual: <...>
- Headline: <...>
- Hypothesis: <...>
**Compliance:** <fix/flag, only where the concept carries one>
```

- Swap "image" → "video" and "Ayca" → "Ana" when the coordinator is Anastasia. The medium noun must match the assignee (gotcha #1).
- The count ("three") is tunable — Tomas has scaled it between three and five.
- Still bullets only, no numbered lists.

## Step 5 — Universal defaults (every new CS task)

- **List:** `901110066469` · **Task type:** Deliverable (`custom_item_id 1013`)
- **Status:** `to do`
- **Due date:** next week's Friday from creation date (PMs reassign)
- **Tags:** none (tags don't matter on this list)
- **`✨ Brand`** → Shameless · **`👤 Project Manager`** → Alejandra Beauchamp (`114210317`) · **`👤 Creative Strategist`** → Tomas (`81523916`)
- **`👤 Designer`** (id `71125236-4e60-4363-9d04-e64780b2d8f2`) → the actual designer userid matching the editor code in the name (AYC → Aicha `81523925`, JDC → `81523933`, FER → `81523931`). Fill this — don't leave for Alejandra.
- **`👤 Responsible`** (id `a81df287-335f-493b-adb8-b7ac2bcbc581`) → the group GUID per profile: Designer `cf65787a-6fe1-4473-8e2a-889720cda89b` (image) / Video Editor `1a5392c6-9f0d-4ccd-8c4d-5dde128c1d62` (WL/video). GROUP GUID string, never the team userid.
- **`💎 Deliverable Type`** → per profile (Step 2) · **`💎 Project Type`** → Proven for most image-test work · **`🚨 Channel`** → Facebook (option UUID `b5d2e5be-5720-4429-9040-db8396aa250c`).
- **`✨ Product`** → match the bag (OG / Carnival / Lollipop / All Stars / Super Variety — orderindex in references §3).
- FB fields → `FB Ad3 - LP` (LP confirmed in Step 1), `FB Ad4 - FB Page` (format `"<Page Name> (<page_id>)"` — default `Shameless Snacks (114450944603601)`), `FB Ad6 - Headline`, `FB Ad7 - Text`, `FB Ad8 - Description`. Mirror `Landing Page Link` to `FB Ad3 - LP`.
- **Skip** (media buyer fills later): `FB Ad1/Ad2/Ad5`, and `FB Ad9 - Headline Injection` if the LP URL already carries `?headline=`. Don't touch the other ~95 legacy fields.
- **Assignee**: the actual editor as a task assignee (e.g. Aicha `81523925`) — the Designer team can't be a task assignee (only a user-field value); ClickUp returns "All assignees must have access to this task" if you try.

### Step 5b — Launch-task defaults (video AND image)

When the task is a **launch** (going live), set ALL THREE on every task at create time — these get forgotten on image tasks:

- **Assignee = Alejandra Beauchamp (`114210317`)** as the task assignee (in addition to her `👤 Project Manager` field).
- **Priority = high.**
- **Time estimate** by type: **video/CTV = 8h (480 min)**, **image-test = 3h (180 min)**. (Image was corrected down from 8h on 2026-06-26.)

The image-test `_Tom` naming (empty designer slot, Designer team Responsible) still holds for a launch image task — `_Tom` governs the NAME/designer routing only; the task is still assigned to Alejandra, high priority, with the estimate. Don't let "image-test default = normal priority" override this.

## Step 6 — Create, then patch the stubborn fields

The MCP's `clickup_create_task` does NOT reliably set group-enabled user fields, and dropdowns need a specific value format. So:

1. **Create** the task with: name, `markdown_description`, status, due date, list, task type, and the *simple* fields (FB text fields; plain dropdowns).
2. **Custom-field value formats** (verified 2026-06-03 — the gotchas that cost a patch-and-verify loop):
   - **Dropdowns** (`✨ Brand`, `✨ Product`, `💎 Deliverable Type`, `💎 Project Type`): pass the **orderindex int** (safest default per the WL build); fall back to the option UUID string only if orderindex fails on verify. (e.g. Brand Shameless = orderindex `1` / UUID `4c3f72cf-9bc9-464a-b9a4-2371852849f6`.)
   - **Label fields** (e.g. `🚨 Channel`): array of **[option UUID strings]**, e.g. `["b5d2e5be-5720-4429-9040-db8396aa250c"]` for Facebook.
   - **Plain user fields — real human** (`👤 Creative Strategist`, `👤 Project Manager`, `👤 Designer`, `👤 Copy Lead`): `{"add": [<userid_int>]}`. Integer userid inside the add object. A bare array `["81523916"]` or `[81523916]` returns `success: true` but does NOT persist — always verify.
   - **Group/team user fields** (`👤 Responsible`, `👤 Video Editor`, `👤 Project Manager` when group-enabled): `{"add": ["<group-GUID-string>"]}` via `clickup_update_task` (not reliably in create). The team's userid (e.g. `75478960` for Designer) is silently rejected — must use the workspace group GUID. Designer = `cf65787a-6fe1-4473-8e2a-889720cda89b`, Video Editor = `1a5392c6-9f0d-4ccd-8c4d-5dde128c1d62`.
   - **Tags** — `clickup_update_task` does NOT accept a tags param. Use `clickup_remove_tag_from_task` per tag for cleanup.
3. **Patch** group-user fields and any field that silently failed via `clickup_update_task` using the add/rem format. Plain user fields usually take on create; group-user fields almost always need a follow-up patch.
4. **After ANY field-only patch (priority/assignee/estimate), re-read the description** — a re-save can collapse a numbered list. This is why the description must be bullets-only.

## Step 7 — Verify (don't trust `success: true`)

After create + patch, confirm the fields that silently fail:

- Read the task back with `clickup_get_task` using **`detail_level="summary"`** — the full 103-field payload can hit ~4MB and break the response (it auto-saves to a file you can `jq` if needed).
- Confirm: status, due date, Brand, Deliverable Type, **Responsible group**, priority + assignee + estimate (on launch tasks), and the FB copy fields actually persisted.
- **Confirm the description body is intact** — that hooks 2–N and any lower blocks survived (the ordered-list collapse silently truncates).
- If a users-type or dropdown field didn't stick, re-patch with the alternate format (add/rem for users; orderindex-vs-UUID for dropdowns) and re-verify.

Report back a tight summary: created task IDs/names + a one-line "verified: Brand✓ Responsible✓ copy✓ body✓" so Tomas can trust it landed.

## Batch rules

- **Parallel briefs on one angle** = a real A/B/C test only if differentiated. Give each a distinct **sub-angle** (stat-led / outcome-led / comparison-led / etc.) unless Tomas says "duplicates" or "identical". "Brief 6 concepts × 3 editors" = 18 task creations.
- **Aicha (`81523925`) creates INDIVIDUAL tasks, not subtasks.** When briefing image variations for her, spawn one sibling task per variation in the list — never nest under a parent Deliverable. Group visually with a shared SHA name prefix.
- Create the batch, then verify a sample (first + last) at minimum; verify all if the batch is small.
- Scope everything to the **Tomas | Creative Strategist List (`901110066469`)** unless Tomas says otherwise (e.g. "the CRO list" → `901111997698`). Never team-wide.

## MCP tools

`clickup_create_task`, `clickup_update_task`, `clickup_get_task` (summary), `clickup_resolve_assignees` (codes/names → IDs when uncertain), `clickup_attach_task_file`, `clickup_add_task_link` (WL → parent), `clickup_filter_tasks` (find siblings to mirror). Load via ToolSearch if not already available. Draft from local docs first; only hit the MCP at the create step.

## Common failure modes (read if something looks off)

- **Task Creation medium mismatch** → body says "video" on a task assigned to Aicha (image) or vice-versa → coordinator spawns the wrong deliverable type for the whole batch (happened 2026-07-02). Match the noun to the coordinator: Aicha=image, Ana=video.
- **Numbered list in a description** → collapses to item 1 on the next `update_task`, dropping hooks 2–N and lower blocks → use bullets, re-verify body after every patch.
- **Wrong Responsible group** → JDC's design team never picks up the work. Image/retro = Designer group GUID; WL/video = Video Editor group GUID. Never the team userid.
- **Bare user array** `["81523916"]` "succeeds" but field is empty on reload → use `{"add":[<int>]}` for humans, `{"add":["<guid>"]}` for groups.
- **Team userid passed for a group field** (e.g. `75478960` for Designer) → silent miss → use the workspace group GUID.
- **Designer team set as task assignee** → API returns "All assignees must have access to this task" → use the specific designer human as assignee; the team goes in `👤 Responsible` only.
- **Launch task with normal priority / no assignee / no estimate** → forgotten on image tasks → bake Alejandra + high + estimate (480 video / 180 image) into the create call.
- **Wrong emoji squares** (🎯/📋/✍️) → not canon → must be 🟧/🟦/🟥.
- **`description` instead of `markdown_description`** → emoji squares + bold render as literal text.
- **Strategist notes leaking into the description** → strip them; canonical record stays clean.
- **Nesting Aicha's variations as subtasks** → breaks her intake; spawn siblings.
- **LP auto-picked from angle** → Tomas calls the LP per test; always ask in Step 1.
- **Trusting `success: true`** → verify every users/dropdown field and the description body with `clickup_get_task detail_level="summary"`.
