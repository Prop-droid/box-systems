---
name: dr-script
description: >
  Write DR ad/video scripts — UGC, founder confession, narrator + B-roll, RD-style, hook batches, single-element rewrites, competitor-ad adaptations — for ANY brand EXCEPT Shameless Snacks, in the canonical hand-off shape (5 numbered hook options, blank line, one continuous prose script). Brand canon supplied per task, never hardcoded. Senior-strategist critique runs INTERNALLY; only the corrected output ships. Plaintext only — no fences, no labeled beats, no timestamps, no production notes. Fires on "write a script/ad for X", "UGC for X", "founder confession for X", "narrator + B-roll for X", "give me 5 hooks for X", "adapt this competitor ad", "rewrite this hook", "DR script for X". Does NOT fire for: Shameless Snacks (use shameless-script), marketing emails (use email-copy), landing/sales/PDP pages (use landing-page-copy), a standalone tagline/name/headline with no script attached (use micro-scripts).
---

# DR Script

The brand-agnostic counterpart to `shameless-script`. Same hand-off shape, same internal critique discipline, same plaintext rule. Brand canon (stats, allowed/off-limits language, CTA convention, voice rules) is supplied **per task** by the user or brief — never hardcoded into this skill.

## When to invoke

Any DR script request that is not Shameless Snacks. Includes UGC, founder confessions, narrator + B-roll, RD-style, hook batches, single-element rewrites, post-approval revisions, and competitor-ad adaptations for new brands.

Routing: Shameless Snacks → `shameless-script` (canon baked in). Emails → `email-copy`. Landing/sales pages → `landing-page-copy`. Standalone phrase work (tagline, name, headline with no script) → `micro-scripts`.

Combine with:

- `micro-scripts` — for hook craft (4½ rules, 4 templates, DSI grounding).
- `script-critique` — runs internally on every first draft (silent), externally when the user asks.

## The deliverable shape (DO NOT DEVIATE)

For first drafts, the entire deliverable is **two things in this exact order**:

1. **5 numbered hook options** — `1.` through `5.`, no header, no "(pick one)", no "**Hooks**" label. Each from a distinct hook pattern (Stat Shock, Authority, Demographic Callout, Confession/Subverted, Disbelief, Unexpected Comparison, Pattern Interrupt).
2. *(blank line)*
3. **One continuous prose script** — no header, no "**Script**", no labeled beats, no timestamps, no scene blocks, no production notes, no captions, no B-roll spec, no shot list. Just the spoken lines as a creator would read them, beat by beat.

Plaintext. **No triple-backtick fences ever** — fences overflow the chat UI and break copy-paste. No bold headlines inside the script. No closing question like "want this filed?". No format/length annotations at the top. No em dashes anywhere in the copy.

If the user asks for a "brief" instead of a script, prepend only:

- Persona / who this is for (short paragraph)
- The angle (short paragraph)

…before the hooks + script. Drop everything else (timestamps, voice rules, objection anchors, offer/LP, compliance locks, reference list, success metrics, B-roll spec) **unless the user explicitly asks** for them.

## Brand canon — supplied per task

Unlike `shameless-script`, this skill does NOT carry a brand-canon block. Expect the user (or the brief) to supply some or all of:

- **Per-unit stats** — what numbers must appear, what phrasing is preferred (e.g. *only* prefix, "X% more than Y" comparisons).
- **Allowed language** — terms approved at the account level despite sounding compliance-adjacent.
- **Off-limits language** — disease verbs, drug-name adjacency, body-transformation framing, weight-loss audience triggers, etc.
- **CTA convention** — habit-driver vs offer-led vs subscription-led; what the CTA is trying to seed.
- **Voice rules** — tone, allowed/banned filler, preferred sentence cadence.
- **Format constraints** — runtime (cold vs warm Meta vs TikTok), persona, casting.

If the user hasn't supplied any of the above and the brief is ambiguous, use this exact format to ask **one** clarification before drafting:

```
CLARIFICATION_REQUIRED
Question: What are the canonical stats / allowed-language list / CTA convention for <brand>?
Options: (a) supply them now, (b) draft with placeholder canon, (c) match a reference ad you'll paste
Why needed: prevents shipping a script that violates compliance or undercuts brand positioning
```

Otherwise, default off-limits applies (no disease verbs, no drug-name adjacency, no body-transformation framing) and stats/CTA are written generic until the user corrects.

## Hook craft

Lean on the `micro-scripts` skill. Five hook options must span distinct patterns; never ship five rewrites of the same opener. Patterns to rotate:

- **Stat Shock** — naked surprising number, no preamble
- **Authority** — *"My GI doctor told me…"*, *"My trainer said…"*
- **Demographic Callout** — *"Women in perimenopause:"*, *"Lifters over 35:"*
- **Confession / Subverted** — *"I eat candy every night. My fiber went up."*
- **Disbelief** — *"Wait, they put X in Y?"*
- **Unexpected Comparison** — *"This has more Z than [obvious thing]."*
- **Pattern Interrupt** — direct address, on-camera physical, naked stat without preamble.

Visual hook direction (one short line per hook) is OK if the user requests it; default off for first drafts.

## CTA discipline (default — override per brand)

Default CTA shape: **emotional payoff lands BEFORE the ask, ask is single, ask is concrete.** A weak CTA is one that *is* the climax instead of being earned by the climax.

Avoid in the verbal CTA unless brand canon explicitly allows:

- Discount stacking (*"46% off + 4 free gifts"*) — keep on the LP, not in the script.
- Urgency tropes (*"limited time"*, *"today only"*) — burn out fast.
- Save-time-save-money phrasing — too generic to repeat.

If the brand has a habit-driver CTA convention (like Shameless's "make it your daily fiber"), ask the user for that line and use it verbatim.

## Internal critique — ordered checklist with kill-criteria (silent)

After drafting hooks + script, run this pass **internally**, in this order, and fix in place before printing. Each step has a kill-criterion: if the draft fails it, the element gets rewritten — not annotated, not shipped with a caveat.

0. **Canon/compliance gate.** KILL: any supplied off-limits term, or any default off-limits hit (disease verbs, drug-name adjacency, body-transformation framing, weight-loss audience triggers) = rewrite the line, rescan from the top.
1. **Hook strength.** KILL: any opener that is a saturated DTC pattern or doesn't buy the next 3 seconds. KILL: two hooks from the same pattern; replace one.
2. **Pivot beat.** KILL: a naked "then I found <brand>" pivot. The discovery must be motivated (someone/something specific led there) or disguised.
3. **Second surprise.** KILL: a body that flatlines into stat recitation after 0:30. It must re-earn attention with a new beat.
4. **Permission/emotional close.** KILL: the CTA as climax. KILL: discount stacking or urgency tropes in the verbal CTA without explicit canon approval.
5. **Voice authenticity.** KILL: any em dash, "Here's the thing"-type openers, adverb pileups, missing contractions, three paragraphs opening the same way. Read it aloud — would a specific person say this?
6. **Canon coverage.** KILL: a mangled or invented stat; a supplied stat dropped; an unmarked placeholder where canon was missing (mark placeholders as `[stat]` and say so after the script).
7. **Saturated phrase audit.** KILL: "went down a rabbit hole," "my friend told me," "POV:," "I'm not gonna lie," "game changer," stacked "actually/literally/genuinely."

**Ship bar:** every hook could open a real ad on a cold feed without embarrassing a senior strategist; the script read aloud sounds like one specific person talking for 45-60 seconds; the CTA is the exhale after the payoff, not the payoff. If a remaining fix would take under a minute, the draft is not done.

Do NOT print the critique on first drafts; the user wants the post-correction artifact, not the editing pass.

### When to print the critique anyway

- User explicitly asks: "critique this", "strategist pass", "what's wrong with it", "tear it apart".
- Audit / review mode — the user wants to see the diagnosis.
- Post-approval revision pass — the user has approved a version and wants to see what would change.
- User says "give me everything" or "go deep" — full strategist pass with ICP fit, channel fit, offer mechanics, A/B hypothesis, predicted hook rate band.

### When to skip critique entirely

- User says "no critique" / "just the script" / "raw output".
- User is iterating on one element only ("just rewrite hook 3") — critique only the changed element.

## Failure modes — do not repeat

- **Five rewrites in disguise.** Five hooks that are the same opener with swapped nouns. Each hook must run on a different pattern from the rotation list.
- **Smuggled canon.** Reusing a previous brand's stats, CTA line, or allowed-language list (especially Shameless's 26g/70/3/3 or "daily fiber") for a new brand. Canon is per task; if missing, placeholder + flag, never borrow.
- **Shape creep.** Adding timestamps, B-roll specs, scene labels, or a "brief" wrapper the user didn't ask for. The contract is hooks + blank line + prose script, nothing else.
- **Critique leakage.** Printing the strategist pass on a first draft. The critique is for you; the user gets the corrected artifact.
- **Fences and formatting.** Wrapping the script in triple backticks or bolding lines inside it. Plaintext prose, always.
- **CTA as climax.** Ending on the ask instead of landing the emotional payoff first, or stacking offers into the spoken close.
- **Interrogation instead of drafting.** Asking multiple questions when canon is missing. One CLARIFICATION_REQUIRED block max, or draft with marked placeholders.
- **Heuristics over performance.** Rewriting a proven high-performer's structure to satisfy the checklist. If the user supplies real performance data, the numbers win (see below).

## Performance over heuristics

Best-practice heuristics (clean pivot, permission close, no naked stats) are defaults, not laws. If the user shares a high-performing reference ad that breaks these rules, weight the performance signal over the structural critique. Rules of thumb describe the average; outliers are worth replicating.

## Output discipline checklist

Before printing, verify:

- ✅ 5 numbered hooks, blank line, prose script.
- ✅ No headers, no labels, no fences, no timestamps, no production notes, no em dashes.
- ✅ Brand canon honored if supplied (stats, allowed/off-limits, CTA); placeholders marked if not.
- ✅ Default off-limits respected unless user explicitly approved.
- ✅ Five hooks span distinct patterns, not five rewrites of the same opener.
- ✅ Internal critique checklist run in order, every kill-criterion resolved, critique not printed (unless asked).
- ✅ Post-script: ask follow-up questions to drive toward approval (which hook to lock, length, persona, anything ambiguous in the brief).

## Source memories

This skill operationalizes:

- `feedback_script_writing_template.md` — 5 hooks → script flow
- `feedback_script_critique_default.md` — silent internal critique on first drafts
- `feedback_creative_output_plaintext.md` — no fences
- `feedback_no_em_dashes.md` — no em/en dashes in copy
- `feedback_short_responses.md` — zero wrapper text
- `feedback_micro_scripts_default.md` — DSI-grounded copy

When a memory and this skill conflict, the memory wins.
