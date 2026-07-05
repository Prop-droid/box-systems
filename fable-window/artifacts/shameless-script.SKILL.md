---
name: shameless-script
description: Write Shameless Snacks ad/video/UGC/founder/narrator/RD scripts in the canonical hand-off shape (5 numbered hooks, blank line, one continuous prose script) with brand canon (26g fiber / 70 cal / 3g sugar / 3g net carbs), the allowed-language list (prebiotic fiber, food noise, pooping every day), a hard compliance gate, daily-fiber CTA, and trim-defaults baked in. Runs the senior-strategist critique INTERNALLY and ships only the corrected output. On approval, saves into the canonical SHA Google Doc template (2-table layout, sprint-numbered title). Use whenever the user asks for a Shameless script, ad, UGC, founder confession, narrator + B-roll, RD-style, hook batch, script adaptation, or revision. Phrases like "write a Shameless script", "Shameless ad", "Shameless UGC", "Shameless founder", "narrator B-roll for the bag", "9pm cravings angle", "fiber-deficiency angle", "eat the whole bag", "rewrite this hook", "adapt this for Shameless".
---

# Shameless Script

How to draft a Shameless Snacks ad/video script the user will actually approve, in the exact deliverable shape he's asked for repeatedly. The skill bakes in every brand rule that has been corrected at least once so they don't drift on the next draft.

## When to invoke

Any creative writing task for Shameless Snacks: UGC scripts, founder confessions, narrator + B-roll, RD-style, hook batches, script adaptations, single-element rewrites, post-approval revisions. Includes Atria-derived ad re-versioning ("adapt this competitor ad for Shameless"). Combine with the `micro-scripts` skill for hook craft.

## Intake — ask BEFORE drafting (do not skip)

Most Shameless tasks are re-versions of an existing winner, not net-new invention. Before generating any hooks or script, ask:

> **Is there a muse (reference video / competitor ad / winning creative) or an existing script these new tasks should be based on?**

- If **yes** → get the muse link or script first, transcribe/read the actual hook and structure, and build the new tasks off that source's shape, beats, and angle. Do not invent a fresh angle when the user wants a re-version.
- If **no / "your call"** → then generate net-new from brand canon and angle strategy as below.

This applies even when the request looks self-contained (e.g. "make briefs for the new flavors"). Only skip the question when the user has already named the muse/source in the same request, or explicitly said it's net-new.

## The deliverable shape (DO NOT DEVIATE)

For first drafts, the entire deliverable is **two things in this exact order**:

1. **5 numbered hook options** — `1.` through `5.`, no header, no "(pick one)", no "**Hooks**" label. Each from a distinct hook pattern (Stat Shock, Authority, Demographic Callout, Unexpected Comparison, Confession/Subverted, Disbelief, etc.).
2. *(blank line)*
3. **One continuous prose script** — no header, no "**Script**", no labeled beats, no timestamps, no scene blocks, no production notes, no captions, no B-roll spec, no shot list. Just the spoken lines as a creator would read them, beat by beat.

Plaintext. **No triple-backtick fences ever** — fences overflow the chat UI and break copy-paste. No bold headlines inside the script. No closing question like "want this filed?". No format/length annotations at the top.

If the user asks for a "brief" instead of a script, add only Persona (short paragraph) and The angle (short paragraph) before the hooks + script. Drop everything else (timestamps, checklists, voice rules, objection anchors, offer/LP, compliance locks, references, success metrics, B-roll spec, format classification) **unless the user explicitly asks**.

When the hooks land in a ClickUp brief/task body (not chat), label them "Hooks (one variation each):" — the Video Editor builds one cut per hook. Never "pick one."

## Brand canon — bake into every script

Non-negotiable. Don't re-derive.

**Drift guard:** source of truth is the memory pair `shameless_brand_canon.md` + `shameless_compliance_language.md` (plus the `shameless-compliance-guardrails` KB concept). If those say something newer than this file, memory wins, and update this section in the same session.

### Per-bag stats (every SKU, including Allstars)

- **Fiber:** 26g (the "29g for some Allstars" exception is stale, never use it)
- **Calories:** 70. "Only 70 calories" as a single-SKU lead claim; **"70-90 calories/bag" is also allowed** (varies by SKU, Tomas 2026-06-18). Don't flag 70-90 as a violation.
- **Sugar:** 3g. In hooks/headlines prefer **"Only 3g of sugar"** (the *only* is the voice lever). Bare "3g sugar" fine as a noun phrase.
- **Net carbs:** 3g

**Offer ceiling:** Meta advertorial funnel tops at 46% off + free shipping, sub-gated. Never quote "up to 58% off" (ad-spy marketing math). Offers stay off the spoken CTA anyway (see CTA section).

**Sweetener reality (corrected 2026-06-30):** the formulation is **sucralose + erythritol**, NOT allulose as older docs said. This makes every clean-sweetener claim factually false, not just unsupported.

## COMPLIANCE GATE — hard, runs before anything ships

Scan every hook and every script line against these lists. **Any BANNED hit = the draft does not print. Rewrite the line, rescan, then continue.** This is a gate, not a critique lens. Machine-checkable mirror: `~/systems/compliance-eval/policy.json` (the scorer reads it as data). Known staleness: that policy's allow-list (2026-06-20) still whitelists "appetite suppressant"; that entry is superseded by the 2026-06-30 ban below. Memory wins.

### BANNED — kill on sight

- **Drug names:** Ozempic, Wegovy, Zepbound, Mounjaro, semaglutide, tirzepatide, metformin. Also equivalence framing: "natural Ozempic," "GLP-1 alternative," "replace your shot," "skip the injection." Ride the audience by symptom, never the drug. Bare "GLP-1" = review-flag, keep it out of first drafts.
- **Fat/weight clinical claims:** melts/burns fat, fat-burning, guaranteed weight loss, "lose 10 lbs," makes you lose weight, shrink your waist. (Narrative weight loss is allowed, see below.)
- **Medical-cure verbs with a condition object:** cures/treats/heals/reverses/fixes + IBS, constipation, gut, digestion, disease, diabetes; "boosts immunity."
- **Blood-sugar medical claims:** lowers blood sugar/cholesterol, won't spike your blood sugar, safe for diabetics. Even bare "blood sugar"/"glucose"/"insulin" needs review plus the structure-function disclaimer.
- **Detox/cleanse** in any form.
- **Clean-label claims — ALL false given sucralose + erythritol:** "no artificial colors/flavors/sweeteners/dyes," "no added sugar," "naturally flavored," "natural colors," "dye-free," "all natural." The variety packs do use natural colors/flavors but the claims are still not sayable (citric + malic acid disqualify them). No color/dye/natural-flavor claim, period.
- **"Real fruit" / "real fruit flavor"** — no fruit in the formula (banned 2026-06-30).
- **Appetite-suppressant framing** — "appetite suppressant," "fills me up so I can't eat more" (banned 2026-06-30, found on Amazon A+). The product is a snack, not an appetite-control supplement. Personal craving narrative is fine; product-as-appetite-drug positioning is not.
- **"Made in USA" / US-manufacturing claims** — manufactured abroad, packed in US. Allowed form: "Packed in the US in an FDA-registered, GMP-certified facility."
- **Named-competitor opinion attacks** — competitor mentions are facts-only (numbers, ingredients). Never "SmartSweets is junk."
- **Telling anyone with distress to keep eating** ("keep eating the whole bag" to a complaint).
- Body-transformation before/after framing, literal or implied.

### ALLOWED — do not self-flag these

- **prebiotic fiber** ✅ intentional differentiator
- **food noise** ✅ but it's the highest-risk approved term (GLP-1-conversation vocabulary Meta polices). Max ~one use per script, fiber-routed, never near drug talk.
- **pooping every day / "I'm regular now"** ✅ approved for Shameless paid Meta at account level (2026-05-06)
- **eat the whole bag** ✅ brand canon
- **kills/curbs cravings, keeps you full** ✅ as first-person narrative, not appetite-control positioning
- **narrative weight loss** ✅ "I've been trying to lose weight," "jeans fit better," "shedding pounds"
- **keto-friendly, 3g net carbs** ✅ (never "keeps you in ketosis")
- **Plant-based, no gelatin** ✅ the approved clean-label contrast vs competitor gelatin & glucose syrup

### Meta 2026 (MARS) guardrails — judgment calls, not greps

- **No personal-attribute "you" framing, even indirect.** "For people managing X," "if your digestion has slowed" flag the same as direct claims. Describe the snack + situation, not the viewer's condition.
- **No implied transformation.** Product beside a fit body, or a "journey" testimonial, trips review even with clean copy.
- **Structure-function disclaimer** ("not intended to diagnose, treat, cure, or prevent any disease") must ride in the ad copy on any benefit-mechanism creative (satiety/regularity/fullness). It goes in the brief/Doc notes for the editor, never in the spoken script.
- "It got approved before" is not a defense; Meta re-audits retroactively.

## Hook craft

Lean on `micro-scripts` for compression. Five hooks span distinct patterns, never five variants of one opener: **Stat Shock** ("26 grams of fiber in a bag of candy."), **Authority** ("My GI doctor told me the only fix was..."), **Demographic Callout**, **Confession/Subverted** ("I eat candy every night. My fiber went up."), **Disbelief**, **Unexpected Comparison** ("more fiber than a bowl of oatmeal"), **Pattern Interrupt**. Visual hook direction only if requested. For N parallel briefs on one angle, differentiate each with a distinct sub-angle (stat-led vs outcome-led vs comparison-led); identical clones only when Tomas says "duplicates."

## CTA — daily fiber driver, not sales

Every script CTA pushes the **daily-fiber habit**, never an offer, discount, or urgency. Use: "Make it your daily fiber." / "One bag a day, fiber handled." / "Your daily fiber, without the supplement." / "Replace the powder. Eat the candy." / "One bag a day on subscribe" (habit-enabler framing, not discount). Never lead the spoken CTA with 46% off, free gifts, limited time, or save-money phrasing; offer badges live on the LP only. When in doubt: the CTA answers "how do I get my fiber every day?" not "why buy right now?"

## Internal critique — ordered checklist with kill-criteria (silent)

After drafting hooks + script, run this pass **internally**, in this order, and fix in place before printing. Each step has a kill-criterion: if the draft fails it, the element gets rewritten (not annotated, not shipped with a caveat).

0. **Compliance gate** (section above). KILL: any banned hit anywhere = full stop, rewrite the line, rescan from the top.
1. **Hook strength.** KILL: any opener that is a saturated DTC pattern or doesn't buy the next 3 seconds. KILL: two hooks from the same pattern; replace one.
2. **Pivot beat.** KILL: a naked "then I found/tried Shameless" pivot. The discovery must be motivated (someone/something specific led there) or disguised.
3. **Second surprise.** KILL: a body that flatlines into stat recitation after 0:30. It must re-earn attention with a new beat (taste flip, eat-the-whole-bag math, an unexpected admission).
4. **Permission/emotional close.** KILL: the CTA as climax. The emotional payoff lands first; the CTA is the exhale after it.
5. **Voice authenticity.** KILL: any em dash, any triple-dot dramatic build past one, "Here's the thing"-type openers, adverb pileups, three paragraphs opening the same way. Contractions always. Would a specific person say this out loud?
6. **Brand canon coverage.** KILL: any stat off 26/70/3/3, a missing "Only" where it lands, an offer-led close, an allowed term flagged out or a banned term smuggled in.
7. **Saturated phrase audit.** KILL: "went down a rabbit hole," "my friend told me," "POV:," "I'm not gonna lie," "game changer," stacked "actually/literally/genuinely."

Ship only the post-correction artifact. **Print the critique only when:** the user asks ("critique this," "strategist pass," "what's wrong"), audit/review mode, post-approval revision pass, or "give me everything" (then add ICP fit, channel fit, offer mechanics, A/B hypothesis, predicted hook-rate band). **Skip critique when:** "no critique" / "just the script," or single-element iteration (critique only that element). Printed format: 5-7 numbered problems prioritized by spend cost, one line each with the fix, plus one trailing "Don't touch in next pass:" line.

**Performance beats heuristics:** the Steph Joplin All-Stars car-line UGC (SH-13646-1) graduated to performer while breaking rules 2-4. When critiquing whitelisted-creator material with real performance data, weight the numbers over the structure. Kill-criteria are defaults, not laws.

## Failure modes — real past mistakes, do not repeat

1. **Brief-builder bloat** (corrected twice 2026-05-06). Defaulted to a full strategy doc with checklists and metrics when "script" was asked. The default is hooks + script, nothing else. Resist the creative-brief-builder reflex.
2. **Wrapper text creep** (2026-05-06). "Hooks (pick one)," "**Script**," "want this filed?" Zero instruction-wrapper text; the shape is the whole spec.
3. **Skipped the muse question** (2026-06-26 variety-pack briefs). Generated polished net-new scripts when Tomas expected re-versions of a source. Ask the muse question first, every time.
4. **Offer-led CTA drift.** "46% off + 4 free gifts" closes kept reappearing from old wiki formats. Daily-fiber CTA, always.
5. **"Pick one" hooks in ClickUp** (2026-06-19, SH-16405). In task bodies the 5 hooks are one-variation-each for the editor, not options.
6. **Stale canon claims.** "Allulose" (wrong, it's sucralose + erythritol), "29g Allstars," clean-label lines that were live in wiki/Amazon copy until the 2026-06-30 scrub. Verify claims against the gate, not against older drafts.
7. **Em dashes in ad copy** (flagged 2026-06-02). They read as AI-written. Periods or commas.
8. **Fenced code blocks** around creative output. They overflow the UI and break copy-paste.
9. **Over-flagging allowed terms.** Compliance-flagging "food noise," "pooping every day," or "prebiotic fiber" wastes a round trip; they're approved.
10. **Identical parallel briefs** (2026-05-28, SH-15968/69/70). N briefs on one angle must test N sub-angles.

## After approval — save into the canonical SHA Doc

Copy the canonical template doc and fill it in. **Template:** https://docs.google.com/document/d/1z0WoRm0xAWdTKGRpERR5pGEr9Nt6oF0eoL7FQeQiGfc/edit (personal Drive, propeidzas@gmail.com; work-account Drive MCP can't reach it — use `xattr -p com.google.drivefs.item-id <synced file>` on a local mirror for IDs).

**Title:** `SHA_2026_S<##>_<Angle>_<ScriptName>_<VideoStyle>` where `S<##>` is the **next** ISO week number (look it up, never current week), Angle like `9pm-cravings`, ScriptName a short handle, VideoStyle like `UGC-stitch-trojan` / `founder-confession` / `narrator-broll`.

**Block 1, metadata table (2 cols):** Preferred Casting / Notes for Videographers / Notes for Video Editors / Muse Video (URL) / Muse Hook (transcribed exact line) / Hooks (1-5). **Block 2, script body table (2 cols):** `Visual reference (optional) | New Script`, one row per beat (reading chunk + visual cue), not per-second timestamps.

**On approval:** 1) copy template → new doc named per convention, 2) fill metadata block, 3) fill script body table, 4) return the Doc URL. **Before approval:** never render the table in chat (markdown tables don't paste into Docs cleanly); print only hooks + prose script.

## Reference assets in the wiki

Under `Code Things/wiki/` (plus `systems/research/2026-04_creative-strategy-tactics/`): 7 script-format catalogs, 49-archetype hook catalog, 11-arc story-shape catalog, past-test performance data, live compliance guardrails. Load only when the brief calls for archetype/arc lookup. Where wiki guidance conflicts with this skill (CTAs, "food noise"/"pooping" allowance), **this skill wins**; update wiki pages as they surface.

## Output discipline checklist

Before printing, verify:

- ✅ Compliance gate passed: zero banned hits, allowed terms not self-flagged, MARS judgment calls made.
- ✅ 5 numbered hooks, blank line, prose script. No headers, labels, fences, timestamps, or production notes.
- ✅ Stats correct (26 / 70 / 3 / 3), "only" used where it lands, no stale claims.
- ✅ CTA is daily-fiber, not offer-led.
- ✅ Five hooks span distinct patterns.
- ✅ No em dashes anywhere in the copy.
- ✅ Internal critique checklist run in order, every kill-criterion resolved, critique not printed (unless asked).
- ✅ Post-script: ask follow-up questions to drive toward approval (which hook to lock, length, persona, brief ambiguities).

## Source memories

Consolidates: `feedback_shameless_brief_defaults` (trim defaults, shape), `feedback_shameless_cta_daily_fiber` (CTA), `script_defaults` (5 hooks → script, internal critique, Micro-Scripts lens), `feedback_creative_output_plaintext` (no fences), `feedback_no_em_dashes`, `feedback_ask_muse_before_brief` (intake), `feedback_sha_hooks_one_variation_each` (ClickUp framing), `feedback_parallel_brief_differentiation`, `shameless_brand_canon` (stats, offer ceiling, canon-beats-brief), `shameless_compliance_language` + KB `shameless-compliance-guardrails` (allowed/banned, 2026-06-30 corrections), `project_shameless_script_template` (SHA Doc), `project_steph_joplin_winner_pattern` (performance over heuristics).

When a memory and this skill conflict, the memory wins — it's the live source of truth.
