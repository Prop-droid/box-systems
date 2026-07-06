# Shameless Static Copywriter Implementation Plan

> **2026-07-04 correction:** "natural appetite suppressant" was banned 2026-06-30 and must be excluded from the monitor tier wherever this plan is re-executed. See wiki compliance-guardrails.
> Open question: verify the generated `shameless-static-copywriter/knowledge/` pack itself (lives outside wiki/) got the same fix.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `shameless-static-copywriter/` distribution folder — a standalone Claude.ai Project deliverable (custom instructions + 6 knowledge files + README) that lets an external teammate generate ranked static-ad headlines from a competitor reference image.

**Architecture:** Pure content/documentation deliverable. No code. All Shameless Snacks data is distilled from the existing wiki (`wiki/*.md`) and raw sources (`raw/brand-context/*.md`) into six self-contained reference markdown files. One top-level custom-instructions file drives the LLM workflow. One README documents install into a Claude.ai Project.

**Tech Stack:** Markdown files only. Target runtime is Claude.ai Projects (Custom Instructions + Project Knowledge). No build step, no dependencies, no tests-as-code.

**Source of truth:** [docs/superpowers/specs/2026-04-20-shameless-static-copywriter-design.md](../specs/2026-04-20-shameless-static-copywriter-design.md)

**Self-containment rule (applies to every knowledge file):** no wikilinks (`[[...]]`), no relative file paths, no "see X" references to files outside this folder. If a teammate's Claude.ai Project Knowledge can't open it, it doesn't belong in a knowledge file.

---

## File Structure

Final deliverable layout (all under project root):

```
shameless-static-copywriter/
├── README.md
├── custom-instructions.md
└── knowledge/
    ├── brand-facts.md
    ├── brand-voice.md
    ├── compliance.md
    ├── icps.md
    ├── hooks-and-patterns.md
    └── angles.md
```

**Responsibility per file:**

| File | Owns |
|---|---|
| `README.md` | Install steps only. No brand content. |
| `custom-instructions.md` | Workflow, image-analysis schema, output formats, hard rules. Paste-into-Project-Instructions payload. |
| `knowledge/brand-facts.md` | Product stats, pricing, offer, flavor lineup, approved phrasings. Read for every run. |
| `knowledge/brand-voice.md` | Voice intensity scale, tone patterns, phrase bank. Read for every run. |
| `knowledge/compliance.md` | Hard stops, monitor tier, exact `⚠` tagging format. Read for every run. |
| `knowledge/icps.md` | 5 personas + inference heuristics table. Read for every run. |
| `knowledge/hooks-and-patterns.md` | 8-pattern hook taxonomy + 5 proven static patterns with full templates + Meta three-field split rules. Read for every run. |
| `knowledge/angles.md` | Fiber-first directive, sub-angles, ICP-to-angle mapping. Read for every run. |

---

### Task 1: Create the distribution folder structure

**Files:**
- Create: `shameless-static-copywriter/` (folder)
- Create: `shameless-static-copywriter/knowledge/` (folder)

- [ ] **Step 1: Create the two folders**

Run:
```bash
mkdir -p "shameless-static-copywriter/knowledge"
```

- [ ] **Step 2: Verify both folders exist**

Run:
```bash
ls -la shameless-static-copywriter/ && ls -la shameless-static-copywriter/knowledge/
```

Expected: both directories listed, `knowledge/` appears inside `shameless-static-copywriter/`, no extra files.

---

### Task 2: Write `knowledge/brand-facts.md`

Responsibility: canonical product facts. Must be usable as the sole reference for any stat phrasing. No wikilinks. Distilled from `wiki/product-facts.md`, `wiki/shameless-snacks.md`, `wiki/pricing-and-offers.md`, `wiki/flavor-strategy.md`.

**Files:**
- Create: `shameless-static-copywriter/knowledge/brand-facts.md`
- Read first: `wiki/product-facts.md`, `wiki/shameless-snacks.md`, `wiki/pricing-and-offers.md`, `wiki/flavor-strategy.md`

- [ ] **Step 1: Read all four source files in full**

Use the Read tool on each of the four source paths above. Do not summarize from memory.

- [ ] **Step 2: Draft the file with these required sections**

Required sections (in this order):

1. `# Brand Facts — Shameless Snacks`
2. `## What it is` — one-paragraph product description (low-sugar high-fiber gummy candy).
3. `## Canonical stats` — markdown table: Stat | Exact phrasing | Notes. Include 26g fiber, 3g sugar, 3g net carbs, 70 calories (with "70–90 cal" upper bound rule), plus the rule "never round past 90."
4. `## Ingredients and claims` — keto-friendly, vegan, gluten-free. Sweeteners used. Do not include any medical claims.
5. `## Pricing` — subscription ($2.69/bag), one-time ($3.50/bag), exact offer phrasing "Up to 46% off + 4 free gifts (first order only)."
6. `## Flavor lineup` — current flavors grouped by sourness tier (Super Sour / Sour / Sweet), as listed in the source wiki.
7. `## Approved ad phrasings` — bulleted list of phrases that are always safe to use verbatim (e.g., "26g of gut-loving fiber per bag", "3g sugar, 3g net carbs", "70 calories per bag", "taste just like candy").
8. `## What NOT to claim here` — one-line pointer: "For anything about medical/weight-loss/outcome language, consult `compliance.md`. This file contains only neutral product facts."

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/knowledge/brand-facts.md`.

- [ ] **Step 4: Self-containment check**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/knowledge/brand-facts.md
```

Expected: no matches. If any line matches, rewrite that line to inline the referenced content.

- [ ] **Step 5: Required-sections check**

Run:
```bash
grep -E '^## ' shameless-static-copywriter/knowledge/brand-facts.md
```

Expected: exactly the 7 `##` headings listed in Step 2. Section 1 (`# Brand Facts...`) is the top H1.

---

### Task 3: Write `knowledge/brand-voice.md`

Responsibility: voice, tone, phrase bank. Distilled from `wiki/brand-voice.md` and `raw/brand-context/brand_voice.md`.

**Files:**
- Create: `shameless-static-copywriter/knowledge/brand-voice.md`
- Read first: `wiki/brand-voice.md`, `raw/brand-context/brand_voice.md`

- [ ] **Step 1: Read both source files in full**

- [ ] **Step 2: Draft the file with these required sections**

1. `# Brand Voice — Shameless Snacks`
2. `## Core register` — one-paragraph summary: retro-Americana, self-aware, confidently indulgent, never apologetic.
3. `## Intensity scale (3 tiers)` — table: Tier | Use when | Example line. Tiers: Chill, Medium, Shameless.
4. `## Six tone patterns` — each with a name, one-line description, and one example line. (Pull the exact six from the source wiki.)
5. `## Cadence and rhythm rules` — short sentences beat long ones; parallel three-beats work; avoid corporate softeners.
6. `## Do-say phrase bank` — 20+ bulleted phrases that are squarely in-voice.
7. `## Don't-say phrase bank` — bulleted phrases that break voice (e.g., "wellness journey," "holistic," "plant-powered nutrition," "guilt-free treat for your body"). Each line explains briefly why.
8. `## Stat-led lines` — 5-10 canonical in-voice stat phrasings that combine voice + facts (e.g., "26g of gut-loving fiber in every bag. You read that right.").

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/knowledge/brand-voice.md`.

- [ ] **Step 4: Self-containment check**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/knowledge/brand-voice.md
```

Expected: no matches.

- [ ] **Step 5: Required-sections check**

Run:
```bash
grep -E '^## ' shameless-static-copywriter/knowledge/brand-voice.md
```

Expected: exactly the 7 `##` headings from Step 2.

---

### Task 4: Write `knowledge/compliance.md`

Responsibility: compliance rules + exact `⚠` tagging format. This is the most safety-critical file. Distilled from `wiki/compliance-guardrails.md` and `raw/brand-context/compliance_guide.md`.

**Files:**
- Create: `shameless-static-copywriter/knowledge/compliance.md`
- Read first: `wiki/compliance-guardrails.md`, `raw/brand-context/compliance_guide.md`

- [ ] **Step 1: Read both source files in full**

- [ ] **Step 2: Draft the file with these required sections**

1. `# Compliance — Shameless Snacks`
2. `## How to use this file` — one paragraph: compliance is evaluated per-line on headlines. If a line triggers a hard stop, tag it `⚠` inline and keep it in the ranked output — do not silently drop.
3. `## Tagging format` — show the exact format with a worked example:
   ````
   Format: ⚠ "<violating phrase>" — <stop reason>
   Placement: appended to the end of the Compliance column in the ranking table.

   Example: "Shameless melts the fiber gap fat" — ⚠ "melts ... fat" — fat-burn claim (hard stop).
   ````
4. `## Hard stops (auto-tag, never rescue)` — bulleted list with each stop phrase + 1-line rationale. Must include at minimum: drug names (Ozempic/Wegovy used as "alternative"), "cure/treat/fix/heal", "regulates blood sugar", "lowers cholesterol", "melts/burns fat", "detox/cleanse/skinny", body shaming, before/after transformation.
5. `## Monitor tier (allowed with fiber-grounded body)` — bulleted: "natural appetite suppressant", "kills cravings", "keeps you full", "no sugar spike", "weight loss" (as audience framing, not outcome promise), "Ozempic/GLP-1" (as audience context, not alternative).
6. `## Script-level filter principle` — one paragraph: hooks get latitude; the body must deliver fiber/audience/mechanism framing. A provocative headline paired with a compliant body is compliant. But a hard-stop phrase in the headline is still a hard stop.
7. `## Decision tree` — numbered short algorithm the LLM runs on each headline:
   ```
   1. Does the line contain any hard-stop phrase?
      → Yes: tag ⚠ <phrase> — <stop reason>. Keep in list.
      → No: continue.
   2. Does the line contain a monitor-tier phrase?
      → Yes: acceptable in the headline context. Do not tag.
      → No: continue.
   3. Any surprising or borderline claim not covered above?
      → Tag ⚠ <phrase> — needs review.
   4. Otherwise: Compliance column = "✓ clean".
   ```

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/knowledge/compliance.md`.

- [ ] **Step 4: Self-containment check**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/knowledge/compliance.md
```

Expected: no matches.

- [ ] **Step 5: `⚠` format present**

Run:
```bash
grep -c '⚠' shameless-static-copywriter/knowledge/compliance.md
```

Expected: at least 3 occurrences (format example + hard-stop illustrations + decision tree).

- [ ] **Step 6: Required-sections check**

Run:
```bash
grep -E '^## ' shameless-static-copywriter/knowledge/compliance.md
```

Expected: exactly the 6 `##` headings from Step 2.

---

### Task 5: Write `knowledge/icps.md`

Responsibility: 5 personas + inference heuristics for auto-detecting ICP from a reference image. Distilled from `wiki/customer-segments.md` and `wiki/icp-creative-matrix.md`.

**Files:**
- Create: `shameless-static-copywriter/knowledge/icps.md`
- Read first: `wiki/customer-segments.md`, `wiki/icp-creative-matrix.md`

- [ ] **Step 1: Read both source files in full**

- [ ] **Step 2: Draft the file with these required sections**

1. `# ICPs — Shameless Snacks`
2. `## How to use this file` — one paragraph: the skill auto-infers ICP from the reference image using the heuristics table in section 4, then generates all 20 headlines for that one ICP.
3. `## The five ICPs` — one sub-section per ICP. Each sub-section has this exact structure:

   ```
   ### <Name> — <one-line tag>

   - Demographics:
   - Primary motivation:
   - Top triggers:
   - Top objections:
   - Preferred hook patterns (in order):
   - Voice intensity that lands best:
   - Typical reference-image signals that map here:
   ```

   The five ICPs and their one-line tags:
   - **Maggie** — core fiber-health buyer, 55+ female Facebook-mobile
   - **Kevin** — GLP-1 / weight-loss audience
   - **Linda** — keto / low-sugar lifestyle
   - **Mike** — diabetic or pre-diabetic seeking sugar-free
   - **Bariatric-Parent** — post-bariatric patients and parents of kids needing low-sugar snacks

4. `## Inference heuristics (reference-image → ICP)` — table with columns: If the reference shows … | Map to … | Confidence. Populate with at least 10 rows covering: weight-loss/GLP-1 visuals, keto imagery, parent-and-kids scenes, senior demographics, diabetic education tone, gut-health/fiber imagery, comparison with competitors, pure flavor/indulgence focus, before/after style (flag as Maggie with compliance risk), and generic candy-swap framing (default → Maggie).

5. `## Tie-breaker rule` — one paragraph: when the image is ambiguous, default to Maggie (highest buyer match in actual spend data). Always announce the inferred ICP to the user with the override instruction: *"Reference reads as [ICP] — proceeding. Say 'use [other-ICP]' to switch."*

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/knowledge/icps.md`.

- [ ] **Step 4: Self-containment check**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/knowledge/icps.md
```

Expected: no matches.

- [ ] **Step 5: All five ICPs present**

Run:
```bash
grep -E '^### (Maggie|Kevin|Linda|Mike|Bariatric-Parent) ' shameless-static-copywriter/knowledge/icps.md
```

Expected: 5 matches, one per ICP.

- [ ] **Step 6: Heuristics table has enough rows**

Run:
```bash
awk '/## Inference heuristics/,/## Tie-breaker rule/' shameless-static-copywriter/knowledge/icps.md | grep -c '^|'
```

Expected: at least 12 matches (1 header + 1 separator + at least 10 data rows).

---

### Task 6: Write `knowledge/hooks-and-patterns.md`

Responsibility: 8-pattern hook taxonomy + 5 proven static patterns with full templates + Meta three-field split rules. Distilled from `wiki/hook-framework.md` and `wiki/ad-copy-patterns.md`.

**Files:**
- Create: `shameless-static-copywriter/knowledge/hooks-and-patterns.md`
- Read first: `wiki/hook-framework.md`, `wiki/ad-copy-patterns.md`

- [ ] **Step 1: Read both source files in full**

- [ ] **Step 2: Draft the file with these required sections**

1. `# Hooks and Patterns — Shameless Snacks`
2. `## Meta three-field split` — short paragraph + table: Field | Job | Shameless Pattern. Fields: Primary Text, Headline, Description. Include the rule: "Headline stops the scroll. Primary text converts. Description closes."
3. `## Hook taxonomy (8 patterns)` — sub-sections for each of these 8 named patterns, each with a one-line description and 2 Shameless-voiced example headlines:
   - Stat Shock
   - Demographic Callout
   - Confession
   - BTS / POV
   - Comment Reply
   - Lifestyle
   - Disbelief
   - Urgency
4. `## Five proven static patterns` — sub-sections for each, with full copy templates (Headline / Primary / Description). Reproduce the templates verbatim from the wiki source, using current stat values (3g sugar, not 8g):
   - Stat Lead + Benefit Stack (cold prospecting)
   - Problem / Solution Lead (prospecting)
   - Social Proof Headline + Comparison Body (retargeting)
   - Urgency Letter (promo windows only)
   - Benefit Trio (mobile-first scroll)

   Each pattern must show a complete template block like:
   ````
   ```
   Headline: ...
   Primary:
   ...
   ```
   ````
5. `## Headline generation rules for this skill` — bulleted rules used when generating the 20 headlines:
   - Max 10 words per headline.
   - Each headline uses at least one approved stat phrase from `brand-facts.md` OR an approved in-voice phrase from `brand-voice.md`.
   - Across the 20 headlines, all 8 hook patterns should appear at least once.
   - The top 5 (highest fidelity) must collectively use 5 different proven static patterns when expanded into full copy — one pattern per ad.
6. `## Which pattern fits which audience` — short table: Audience | Format | Best hook type. Cover cold prospecting, retargeting warm, lookalikes.

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/knowledge/hooks-and-patterns.md`.

- [ ] **Step 4: Self-containment check**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/knowledge/hooks-and-patterns.md
```

Expected: no matches.

- [ ] **Step 5: All 8 hook patterns present**

Run:
```bash
grep -E '^### (Stat Shock|Demographic Callout|Confession|BTS|Comment Reply|Lifestyle|Disbelief|Urgency)' shameless-static-copywriter/knowledge/hooks-and-patterns.md
```

Expected: 8 matches.

- [ ] **Step 6: All 5 static patterns present**

Run:
```bash
grep -cE '^### (Stat Lead|Problem / Solution|Social Proof|Urgency Letter|Benefit Trio)' shameless-static-copywriter/knowledge/hooks-and-patterns.md
```

Expected: 5 matches.

- [ ] **Step 7: Current stats (no stale 8g)**

Run:
```bash
grep -cE '8g (net carbs|sugar)' shameless-static-copywriter/knowledge/hooks-and-patterns.md
```

Expected: 0 matches. If > 0, the stale 8g phrasing sneaked in from an older template — rewrite to 3g.

---

### Task 7: Write `knowledge/angles.md`

Responsibility: fiber-first directive + sub-angles + ICP-to-angle mapping. Distilled from `wiki/creative-angles.md` and `wiki/fiber-first-positioning.md`.

**Files:**
- Create: `shameless-static-copywriter/knowledge/angles.md`
- Read first: `wiki/creative-angles.md`, `wiki/fiber-first-positioning.md`

- [ ] **Step 1: Read both source files in full**

- [ ] **Step 2: Draft the file with these required sections**

1. `# Angles — Shameless Snacks`
2. `## The primary directive: fiber-first` — one paragraph: the 26g-fiber stat is the hero. Every ad — regardless of ICP — routes through fiber as the mechanism, even when the surface angle is weight-loss, cravings, or keto. The fiber framing is what keeps the copy compliant and differentiated.
3. `## Sub-angles` — sub-section per sub-angle, each with: one-line description, when to use it, example surface hook, fiber-grounded body snippet. Cover: gut-health, cravings/sweet-tooth, GLP-1 fiber-gap, keto fiber-gap, bariatric, comparison (vs. SmartSweets/Haribo/Joyride), price/value, indulgence-without-guilt.
4. `## Angle-to-ICP routing` — table: ICP | Primary sub-angle | Secondary sub-angle | Notes. Populate for all five ICPs from `icps.md` (Maggie, Kevin, Linda, Mike, Bariatric-Parent).
5. `## Angle-to-reference-image matching rule` — one paragraph: after the image analysis (step 3 of the workflow), pick the sub-angle that most closely matches the reference's detected angle, while still routing through fiber in the body. If the reference's angle conflicts with the inferred ICP's primary sub-angle, prefer the reference's angle but note the mismatch in the Fidelity Notes column.

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/knowledge/angles.md`.

- [ ] **Step 4: Self-containment check**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/knowledge/angles.md
```

Expected: no matches.

- [ ] **Step 5: Required-sections check**

Run:
```bash
grep -E '^## ' shameless-static-copywriter/knowledge/angles.md
```

Expected: exactly the 4 `##` headings from Step 2 (fiber-first, Sub-angles, Angle-to-ICP routing, Angle-to-reference-image matching rule).

- [ ] **Step 6: All five ICPs appear in the routing table**

Run:
```bash
awk '/## Angle-to-ICP routing/,/## Angle-to-reference-image matching rule/' shameless-static-copywriter/knowledge/angles.md | grep -cE '(Maggie|Kevin|Linda|Mike|Bariatric-Parent)'
```

Expected: at least 5 matches.

---

### Task 8: Write `custom-instructions.md`

Responsibility: the full payload the teammate pastes into the Claude.ai Project Custom Instructions field. Drives the 10-step workflow end to end. All 12 required sections from the spec.

**Files:**
- Create: `shameless-static-copywriter/custom-instructions.md`
- Read first: the design spec at `docs/superpowers/specs/2026-04-20-shameless-static-copywriter-design.md` (for section 5, 6, 8, 11 details)

- [ ] **Step 1: Read the design spec in full**

- [ ] **Step 2: Draft the file with these 12 required sections, in this exact order**

1. `# Shameless Snacks Static Copywriter — Custom Instructions`

2. `## Role`
   One paragraph: *"You are a direct-response static-ad copywriter for Shameless Snacks. You reverse-engineer competitor reference images into ranked Shameless-voice headlines and full Meta three-field ads. You follow the workflow in this document literally, read the knowledge files before every run, and never invent facts that aren't in `brand-facts.md`."*

3. `## Mandatory first step — read the knowledge files`
   Explicit instruction: *"Before any analysis or generation, read all six Project Knowledge files in full: `brand-facts.md`, `brand-voice.md`, `compliance.md`, `icps.md`, `hooks-and-patterns.md`, `angles.md`. Do not rely on memory from previous runs."*

4. `## Input protocol`
   *"Require a reference image attachment. If the user sends a message without an attached image, reply: 'Please attach a reference image from the competitor ad you want me to analyze.' Then stop until an image is provided."*

5. `## The 10-step workflow`
   Reproduce verbatim the 10 steps from Section 5 of the design spec (the reordered version where Step 2 is 'Read all 6 knowledge files'). Each step is a numbered list item with 1-2 sentences.

6. `## Image analysis schema`
   Reproduce verbatim the 8-field block from the design spec Section 6:
   ```
   Headline:         <text from image>
   Body:             <text from image or "none visible">
   CTA:              <button/text CTA or "none visible">
   Visual format:    <product hero | lifestyle | testimonial | urgency banner | comparison | other>
   Palette:          <short description>
   Hook pattern:     <Stat Shock | Demographic Callout | Social Proof | Urgency | Comparison | Confession | Disbelief | other>
   Angle:            <fiber | weight-loss | keto | cravings | GLP-1 | comparison | price | other>
   Awareness level:  <unaware | problem-aware | solution-aware | product-aware | most-aware>
   ```
   Instruction: *"Fill this block in and show it to the user before announcing the ICP."*

7. `## ICP inference rule`
   *"Use the heuristics table in `icps.md` to map the image analysis to one of five ICPs. Announce in one line: 'Reference reads as [ICP] — proceeding. Say \"use [other-ICP]\" to switch.' If the user sends 'use [other-ICP]' at any point before headline output, switch immediately."*

8. `## Headline generation rules`
   Bulleted:
   - Generate exactly 20 headlines.
   - ≤10 words each.
   - Each headline uses at least one approved stat phrase from `brand-facts.md` OR an approved in-voice phrase from `brand-voice.md`.
   - Across the 20, all 8 hook patterns from `hooks-and-patterns.md` must appear at least once.
   - All 20 must target the inferred ICP (or user-overridden ICP).
   - Mirror the reference's angle and energy as close as possible within brand voice.

9. `## Compliance tagging format`
   Show the exact format with one example:
   ```
   Format: ⚠ "<violating phrase>" — <stop reason>
   Where it goes: in the "Compliance" column of the ranking table.

   Compliant example: "✓ clean"
   Violating example: ⚠ "melts ... fat" — fat-burn claim (hard stop)
   ```
   Rule: *"Do not drop violating headlines. Keep them in the ranked list with the tag. If the whole line would be unacceptable even with a fix, still include it, tag it, and let the user decide."*

10. `## Ranking output format`
    Exact table spec:
    ```
    | # | Headline | Hook Pattern | Compliance | Fidelity Notes |
    |---|----------|--------------|------------|----------------|
    ```
    Sort: best fidelity at top (`#1`), worst at bottom (`#20`). After the table, ask: *"Want full copy for the top 5?"*

11. `## Full-copy output format (only on confirmation)`
    On user "yes" / "go" / "sure":
    ```
    ### Ad 1 — <Pattern Name>
    Headline: ...
    Primary Text:
    ...
    Description: ...
    ```
    Produce 5 ads using 5 *different* proven static patterns (from `hooks-and-patterns.md`), each built around one of the top-5 ranked headlines.

12. `## Hard rules`
    Bulleted:
    - No file saves or writes.
    - No visual/image generation.
    - No claims not in `brand-facts.md`.
    - No more than 5 full ads per run unless the user asks explicitly for more.
    - No video scripts, landing pages, checkout copy, comment replies — those are out of scope for this project.
    - Do not reference the Shameless wiki, Google Drive paths, or any external source — the 6 knowledge files are the only ground truth.

- [ ] **Step 3: Write the file**

Use the Write tool to save to `shameless-static-copywriter/custom-instructions.md`.

- [ ] **Step 4: All 12 sections present**

Run:
```bash
grep -cE '^## ' shameless-static-copywriter/custom-instructions.md
```

Expected: 11 matches (the H1 `#` is section 1; sections 2-12 are `##` → 11 matches).

- [ ] **Step 5: No external references**

Run:
```bash
grep -E '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/custom-instructions.md
```

Expected: no matches.

- [ ] **Step 6: All 6 knowledge filenames referenced**

Run:
```bash
for f in brand-facts brand-voice compliance icps hooks-and-patterns angles; do
  grep -q "$f\.md" shameless-static-copywriter/custom-instructions.md && echo "OK: $f" || echo "MISSING: $f"
done
```

Expected: 6 lines, all starting "OK:".

- [ ] **Step 7: `⚠` format example present**

Run:
```bash
grep -c '⚠' shameless-static-copywriter/custom-instructions.md
```

Expected: at least 2.

---

### Task 9: Write `README.md`

Responsibility: 5-step install guide for a Claude.ai teammate. No brand content.

**Files:**
- Create: `shameless-static-copywriter/README.md`

- [ ] **Step 1: Draft with these required sections**

1. `# Shameless Static Copywriter — Install Guide`
2. One paragraph: what this is ("A Claude.ai Project that turns competitor reference images into 20 ranked Shameless Snacks static-ad headlines, then expands the top 5 into complete Meta three-field ads on request.").
3. `## Prerequisites` — a Claude.ai account with Projects enabled.
4. `## Install` — the 5-step list:
   1. Open Claude.ai → Projects → **New Project** → name it "Shameless Static Copywriter."
   2. Open `custom-instructions.md`, copy its full contents, paste into the project's **Custom Instructions** field, save.
   3. In the project, click **Add Knowledge** and upload all six files from the `knowledge/` folder.
   4. Start a new chat inside the project. Attach a competitor reference image. Type anything (e.g., "go"). The project handles the rest.
   5. To update brand data, re-upload the affected knowledge file(s).
5. `## Folder contents` — a code-fenced tree of what's in the distribution folder.
6. `## Troubleshooting` — two entries minimum:
   - "The project replies without reading the knowledge files." → Ensure all 6 files are uploaded to Project Knowledge, not attached as chat files.
   - "Compliance tags aren't showing." → Confirm `compliance.md` uploaded successfully; the `⚠` format is defined there.

- [ ] **Step 2: Write the file**

Use the Write tool to save to `shameless-static-copywriter/README.md`.

- [ ] **Step 3: Step count check**

Run:
```bash
awk '/^## Install/,/^## Folder contents/' shameless-static-copywriter/README.md | grep -cE '^[0-9]+\. '
```

Expected: exactly 5 matches.

- [ ] **Step 4: All six knowledge filenames referenced**

Run:
```bash
for f in brand-facts brand-voice compliance icps hooks-and-patterns angles; do
  grep -q "$f\.md" shameless-static-copywriter/README.md && echo "OK: $f" || echo "MISSING: $f"
done
```

Expected: 6 lines, all starting "OK:".

---

### Task 10: End-to-end verification

Responsibility: final checks that the full deliverable is coherent and shippable.

**Files:** (all read-only verification of prior tasks)

- [ ] **Step 1: All 9 expected files exist**

Run:
```bash
ls shameless-static-copywriter/ shameless-static-copywriter/knowledge/
```

Expected list: `README.md`, `custom-instructions.md`, `knowledge/` (in top folder); `brand-facts.md`, `brand-voice.md`, `compliance.md`, `icps.md`, `hooks-and-patterns.md`, `angles.md` (in `knowledge/`).

- [ ] **Step 2: No broken cross-references across the whole bundle**

Run:
```bash
grep -rE '\[\[|raw/|wiki/|G:/' shameless-static-copywriter/
```

Expected: no matches anywhere.

- [ ] **Step 3: All knowledge filenames referenced in custom-instructions.md are spelled correctly**

Run:
```bash
for f in brand-facts brand-voice compliance icps hooks-and-patterns angles; do
  test -f "shameless-static-copywriter/knowledge/$f.md" || echo "MISSING file: $f.md"
done
```

Expected: no output (all files exist with correct names).

- [ ] **Step 4: Sanity-check combined size fits Claude.ai Project Knowledge limits**

Run:
```bash
wc -l shameless-static-copywriter/knowledge/*.md shameless-static-copywriter/custom-instructions.md
```

Expected: each file under ~400 lines; total under ~2000 lines. If any single file is much larger, review whether it's bloated.

- [ ] **Step 5: Read-through review**

Use the Read tool on each of the 8 content files (`README.md`, `custom-instructions.md`, and the 6 knowledge files). Skim for:
- Any "TBD," "TODO," "fill in," or placeholder leftover.
- Inconsistent stat phrasings (e.g., "8g net carbs" vs. "3g net carbs" — must always be 3g).
- Contradictions between files (e.g., brand-voice.md's don't-say phrases appearing in hooks-and-patterns.md templates).
- Missing the `⚠` format example in `compliance.md` and `custom-instructions.md`.

If any issue found, fix inline and re-run the relevant task's step checks.

- [ ] **Step 6: Final deliverable announcement**

Print to the user:
```
Deliverable ready at: shameless-static-copywriter/

Folder contents:
├── README.md
├── custom-instructions.md
└── knowledge/
    ├── brand-facts.md
    ├── brand-voice.md
    ├── compliance.md
    ├── icps.md
    ├── hooks-and-patterns.md
    └── angles.md

To share: zip the folder and send to the teammate. They follow README.md to set up their Claude.ai Project.
```
