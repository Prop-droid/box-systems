# Playbook: SHA image-test batch (angle idea -> N ClickUp image-test tasks)

Deterministic sequence for turning one angle/concept into a correctly-fielded batch of image-test tasks on the Tomas | Creative Strategist List (`901110066469`, team `9011638245`). Sources: clickup-task-creator skill (live + upgraded artifact), sha-image-test-task-convention, image-task-responsible-designer, clickup-task-creation-task-type, aicha-spelling-and-workflow, feedback_image_brief_format_menu, clickup-markdown-ordered-list-collapse.

## When NOT to use (kill criteria, check first)

- KILL if the question is analytical ("which image tests won?") - use the winners archive, not this.
- KILL if no LP is confirmed and Tomas is unreachable - never auto-pick the landing page from the angle. Park the batch.
- KILL if the angle token is not in canon (`Fiber`, `GLP1`, `GutHealth`, `Weightloss`, `Bloodsugar`, `Keto`, `LowCal`, `Menopause`, `DadBod`, `LastCall`, `10Reasons`, `Retention`, ...). Never coin one ("DailyFiber" was rejected -> `Fiber`). Pull the token from existing task names or ask.
- KILL if the only reference is a video frame/screenshot - an image test needs a designed STATIC reference. Find a matching designed static in the Atria/Apify swipe cache (`format=="image"`) instead; if none exists, flag it, do not ship a video grab.
- KILL if the concept is a body before/after - compliance hard stop. Reframe to habit/intake timeline (Day 1 vs Day 30) or fiber-math, or drop it.
- KILL any write outside list `901110066469` unless Tomas explicitly named another list.

## Steps

1. **Invoke the `clickup-task-creator` skill first** (Step-0 discipline). Improvising the template is the root cause of every multi-round brief iteration loop. Optionally pull ONE recent same-type task via `clickup_get_task detail_level="summary"` to confirm current field shape.

2. **Gather inputs in ONE batched question** (never question-by-question):
   - **LP** (always ask; fills both `FB Ad3 - LP` and `Landing Page Link`; use the clean base URL, e.g. `https://snacks.eatshameless.com/gummies/meta/fiber-packed/swap/`; never copy another task's `?headline=...&lpv=...` params)
   - **Sprint #** (S##; ask, never derive from a calendar guess)
   - **Product** (OG / All Stars / Carnival / Lollipop / Super Variety)
   - **Canon angle** + concept name
   - **Count** (default 10; see step 6) and whether parallel briefs are distinct sub-angles or literal duplicates
   - **Muse/reference image** (ask if there is a source before drafting; local path or URL)

3. **Pick the route** - direct tasks vs Task Creation directive:
   - Tomas hands finished concepts/copy per task -> **create the N image-test tasks yourself** (steps 4-9).
   - Tomas hands a topic for the team to develop -> **ONE Task Creation directive to Aicha** who fans out the children (step 10).

4. **Name each task** (canon pattern, ends at `_Tom`, NO designer initials):
   `SHA_<YYYY>_S<##>_<product-or-angle>_<format>_<concept-name>_ImageTest_Tom`
   e.g. `SHA_2026_S25_Flavor-Variety_Static_Favorite-Flavors_ImageTest_Tom`
   - Format slot = `Static` (or `Carousel` for carousels). Use a 16-family format token where it fits (`ProductHero`, `HeroClaim`, `Comparison`, `Testimonial`, `Founder`, `IngredientPanel`, `Listicle`, `OfferPromo`, ...). Adapt competitor concepts to Shameless; drop competitor names from the title.
   - Every wave should include 1-2 under-run gap families (Testimonial / Founder / Lifestyle / Explainer...), not all proven clones.

5. **Write the description** via `markdown_description` (NOT `description`), exact 3-block shape:
   ```
   🟧 **OUTPUT:** 10 images

   🟦 **INSTRUCTIONS:**
   - <swap-level instruction: what changes to what>
   - ![Source ad](<url>)   <- reference embedded inline, AND attached via clickup_attach_task_file
   - Create new variations based on given image (<source-filename>).

   🟥 **COPY:**
   <copy lines, one per element>
   ```
   Hard rules: **bullets only, never `1. 2. 3.` or `A. B.`** (ClickUp MCP collapses ordered lists to item 1 on ANY later re-save, even field-only updates). OUTPUT line = count only; style/format detail goes in INSTRUCTIONS. Copy heading inside the body, if used, is `Copywriting:` (never "COPY (locked)"). No strategist notes, no ROAS/spend, no sourcing pointers in the description. On-image headlines (the test variants) stay in the description; FB ad copy goes in custom fields. No em dashes in copy.

6. **Output count rule:** standard = **10 images**. New image + new copy (full reverse-engineer / competitor swap) = **15 images = 5 concepts x 3 stat-lead variants**, and lead INSTRUCTIONS with "Create 5 image concepts based on the reference."

7. **Set fields** (create with the simple ones, then patch the stubborn ones):
   - List `901110066469`, task type Deliverable (`custom_item_id 1013`), status `to do`, due date next week's Friday.
   - `✨ Brand` -> Shameless (orderindex 1 / UUID `4c3f72cf-9bc9-464a-b9a4-2371852849f6`)
   - `💎 Deliverable Type` -> Product Image (or Advertorial/CTV Image) · `💎 Project Type` -> Proven (usual)
   - `🚨 Channel` -> Facebook, label field = array of UUID strings `["b5d2e5be-5720-4429-9040-db8396aa250c"]`
   - `✨ Product` -> match the bag
   - `👤 Project Manager` (Alejandra) `{"add":[114210317]}` · `👤 Creative Strategist` (Tomas) `{"add":[81523916]}`
   - `👤 Responsible` (id `a81df287-335f-493b-adb8-b7ac2bcbc581`) -> **Designer team GROUP GUID** `{"add":["cf65787a-6fe1-4473-8e2a-889720cda89b"]}` via `clickup_update_task` (create call is unreliable for group fields). The team userid `75478960` is SILENTLY rejected.
   - `👤 Designer` (id `71125236-4e60-4363-9d04-e64780b2d8f2`) -> **leave empty** on image tests; Alejandra picks the designer. (To remove a user later: `{"add":[],"rem":[81523925]}` - numeric id; string rem is silently ignored.)
   - FB fields: `FB Ad3 - LP` (`7eca3451-c4df-4897-a543-c92a3d04ede6`) + mirror `Landing Page Link` (`ee82257f-f430-4137-9d3a-54e40bc31ab4`); `FB Ad4 - FB Page` (`77e384fd-202e-47cf-9ef6-5b9b2d7aa36f`) = `Shameless Snacks (114450944603601)` default; `FB Ad6 - Headline` (`5a13da3d-3644-44d5-bf25-2af39ee2b661`); `FB Ad7 - Text` (`580b7f41-99f5-4c9f-a721-d59f6d2c4e48`). Skip FB Ad1/Ad2/Ad5/Ad9 and the other ~95 legacy fields.
   - Value formats: humans `{"add":[<int>]}`; groups `{"add":["<guid>"]}`; dropdowns orderindex int (UUID string fallback); label fields `["<uuid>"]`. Bare arrays return `success: true` and do NOT persist.
   - If it is also a **launch** image task: assignee Alejandra + priority high + 180 min estimate (see playbook_sha_launch_fill.md).

8. **Preview before writing.** Show names + key fields + body to Tomas and get a go-ahead, unless he already said "just create them" this turn.

9. **Verify after every write** (`success: true` lies):
   - `clickup_get_task detail_level="summary"` after create AND after each patch.
   - Confirm: Brand, Deliverable Type, **Responsible = Designer group**, FB fields, and that the **description body is intact** (hooks/variants 2-N survived).
   - Re-patch with the alternate format on any silent miss, re-verify.
   - Batch: verify first + last at minimum; all if the batch is small.
   - Report one line per task: `SH-#### verified: Brand✓ Responsible✓ copy✓ body✓`.

10. **Task Creation directive route (IMAGE vs VIDEO wording - the 2026-07-02 lesson):**
    - ONE task, type Deliverable 1013, status `to do`, assignee = coordinator: **Aicha/Ayca `81523925` = IMAGE**, **Anastasia/Ana `81523938` = VIDEO**.
    - Name: `[Concept] Image Task Creation Ayca` (or `[Concept] Video Task Creation Ana`). "Ayca" only in the name slot; write "Aicha" in all prose.
    - Body = plain directive, NOT the 3-block template:
      ```
      Hey, you need to create three image tasks based on this topic below.
      Also, research reference examples and formats to guide the copywriting and the image tasks.

      **Angle:** <canon angle>

      **Topic: <name>**
      - Trigger: <...>
      - Visual: <...>
      - Headline: <...>
      - Hypothesis: <...>
      **Compliance:** <only where the concept carries a fix/flag>
      ```
    - **The medium noun MUST match the assignee.** Never "video tasks" in a task assigned to Aicha or "image tasks" in one assigned to Ana (a whole batch shipped wrong on 2026-07-02). Count ("three") is tunable, 3-5.
    - Aicha then creates INDIVIDUAL sibling tasks, never subtasks. If you create variations for her directly, same rule: flat siblings with a shared name prefix.
