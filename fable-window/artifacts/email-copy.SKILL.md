---
name: email-copy
description: >
  Write DR email copy — broadcasts, sequence steps (welcome, post-purchase, abandoned-cart, win-back, lapsed-buyer), founder notes, sales and lifecycle emails — in the canonical hand-off shape: 5 numbered subject-line options, blank line, 1 preheader, blank line, prose body, blank line, single CTA. Plaintext, no fences, no labeled blocks. Senior-strategist critique runs INTERNALLY; only the corrected output ships. Brand canon (stats, allowed-language, CTA convention, voice) supplied per task. Fires on "write an email", "draft a broadcast", "welcome/abandoned-cart/win-back email", "founder email", "sales email for X", "subject lines for X", "email sequence for X". Does NOT fire for: ad/video scripts (use dr-script or shameless-script), landing/sales pages (use landing-page-copy), a standalone tagline or headline with no email attached (use micro-scripts).
---

# Email Copy

DR email writing for any brand. Same plaintext-first, hand-off-shape discipline as `dr-script`, adapted for the email format. Brand canon supplied per task.

## When to invoke

Any marketing email request: broadcasts, sequence steps (welcome, post-purchase, win-back, abandoned-cart, lapsed-buyer), founder notes, sales emails, lifecycle emails, transactional-with-marketing-tail. For long-form content emails (newsletters with multiple sections), apply the same shape per section.

For Shameless-specific email copy, layer Shameless brand canon (`shameless-script` skill rules: 26g/70/3/3 stats, daily-fiber CTA, allowed-language) on top of this skill.

## The deliverable shape (DEFAULT)

For first drafts, the entire deliverable is **four things in this exact order**:

1. **5 numbered subject-line options** — `1.` through `5.`, no header, no "(pick one)". Each subject line tests a distinct angle: stat shock, curiosity gap, personal/founder voice, urgency-with-substance, payoff-promise.
2. *(blank line)*
3. **1 preheader** — single line, ~50-90 chars, complementary to (not duplicative of) the chosen subject. Acts as the second hook.
4. *(blank line)*
5. **Prose body** — one continuous block, no labeled sections, no "Greeting:" / "Body:" / "Close:" headers. Sentence-cased flow as a real person would write. Short paragraphs (2-4 lines) with line breaks between for scannability.
6. *(blank line)*
7. **Single CTA** — one line, one ask, one link target. Spell out the link target in plain language (e.g. *Eat the whole bag → eatshameless.com*).

Plaintext. **No triple-backtick fences ever.** No section headers. No "P.S." unless the brief calls for it. No em dashes anywhere in the copy.

## Subject-line craft (the 5)

Subject lines are micro-scripts in a 30-50 char container. Apply the `micro-scripts` skill: prefer A/B equation, stark reminder, unique wordplay, or whole micro-story templates. At least one of these must be present in every subject line:

- A specific number (the stat does the heavy lifting)
- A pattern interrupt (curiosity gap, unfinished sentence, contrast)
- A demographic callout (the buyer feels addressed)
- A confession or admission (founder voice, broken-fourth-wall)
- A naked statement of payoff (no metaphor, just the result)

Avoid in subject lines:

- Spam triggers (excessive caps, multiple !!!, "FREE", "$$$", "act now")
- Vague curiosity ("you won't believe…", "this changed everything…")
- Corporate filler ("Quarterly update from <brand>", "We wanted to let you know…")
- Brand name + colon + content. Boring, signals broadcast, low open rates.

## Preheader craft (the second hook)

The preheader is the line that shows up next to the subject in the inbox preview. It's the second sentence of the email, not a recap. Use it to:

- Add the proof beat the subject teased (subject = curiosity, preheader = specific)
- Add a contrasting tone (subject = stat, preheader = personal)
- Land the payoff the subject implied (subject = problem, preheader = the relief)

Avoid: identical content to subject, marketing taglines, "Open to learn more", or "Hi {first_name}".

## Body craft

Body copy follows the script discipline: prose flow, single voice, beats not blocks. Specifics:

- **Open with a line that pays off the subject.** First sentence of the body matches what the subject promised. Anything else feels like bait-and-switch.
- **One idea per paragraph.** Two-to-four lines. Line breaks between. People scan email, they don't read it.
- **Specifics beat adjectives.** Numbers, names, dates, places. *"26 grams of fiber in a single bag"* beats *"a ton of fiber"*.
- **Proof in the body, not as a separate "testimonials" block.** Drop a quote inline, in voice, with a one-line context.
- **One emotional beat per email.** Don't try to make the reader feel three things; pick one.
- **Single CTA.** Multi-CTA emails dilute conversion. If the brand demands a secondary, make it a soft P.S. reference, not a competing button.

## CTA discipline

One ask. The body should earn it; the CTA should name it.

- ✅ *Make it your daily fiber → eatshameless.com*
- ✅ *Lock your discount before it expires Sunday → /upgrade*
- ❌ *Click here to learn more* (vague, weak verb, no payoff)
- ❌ *Shop now / Subscribe / Read the blog* (multi-CTA dilution)

If the user supplies a CTA convention, use it verbatim. Otherwise default to *"<verb> <object> → <link>"* in the same voice as the body.

## Brand canon — supplied per task

This skill is brand-agnostic. Expect the user (or brief) to supply:

- Stats / numbers that must appear or are off-limits
- Allowed language (terms approved at account level)
- Off-limits language (disease verbs, drug-name adjacency, body-transformation framing — these are default off-limits unless explicitly approved)
- CTA convention (habit-driver vs offer-led vs subscription-led)
- Voice rules (founder vs brand voice, allowed/banned filler)
- From-name and reply-to expectations (informs voice)

If the user hasn't supplied these and the brief is ambiguous, ask **one** clarifying question via the `CLARIFICATION_REQUIRED` format before drafting. Otherwise draft with marked placeholders and say so after the CTA.

## Internal critique — ordered checklist with kill-criteria (silent)

After drafting subject + preheader + body + CTA, run this pass **internally**, in this order, and fix in place before printing. Each step has a kill-criterion: fail it and the element gets rewritten — not annotated, not shipped with a caveat.

0. **Canon/compliance gate.** KILL: any supplied off-limits term or default off-limits hit (disease verbs, drug-name adjacency, body-transformation framing) = rewrite the line, rescan from the top.
1. **Subject-line strength.** KILL: any subject that wouldn't earn an open among 50 other emails in the preview pane. KILL: two subjects on the same angle; replace one. KILL: spam triggers, vague curiosity, brand-name-colon openers.
2. **Subject ↔ preheader fit.** KILL: a preheader that recaps the subject instead of complementing it. The second hook must add proof, contrast, or payoff.
3. **First-line payoff.** KILL: a body opener that doesn't cash the subject's check. If subject = stat-shock and first line = "Hi friend!", the contract is broken; rewrite the opener.
4. **Scannability.** KILL: any paragraph over 4 lines, or two consecutive paragraphs carrying the same idea. One idea per beat, line breaks between.
5. **Single-CTA discipline.** KILL: a second ask anywhere in the body (a competing link, a "also check out"). One ask, named with verb + object + link.
6. **Voice authenticity.** KILL: any em dash, template cadence, missing contractions, corporate filler. Read it aloud — does it sound like the from-name wrote it?
7. **Saturated phrase audit.** KILL: "I wanted to reach out", "hope this finds you well", "just checking in", "quick question", "don't miss out", "transform your <noun>", "unlock your <noun>".

**Ship bar:** the winning subject would get opened by a stranger scanning 50 emails; the body reads aloud as one person talking, pays off the subject in the first line, and earns exactly one ask. If a remaining fix would take under a minute, the draft is not done.

Do NOT print the critique on first drafts. When to print it: same exceptions as `dr-script` (user asks, audit mode, post-approval revision, "go deep"). When to skip entirely: "no critique" / "just the email" / single-element iteration (critique only the changed element).

## Sequence step considerations

If the email is part of a sequence (welcome flow, abandoned-cart, win-back), also consider:

- **Position in the sequence** — opens, mid, close. Each has a different job (opens prime, mid teach, close converts).
- **Spacing assumption** — what's the prior touch's ask, and what's the next touch's ask? This email should advance the relationship, not repeat the prior.
- **Cumulative voice** — sequences are conversations; tone should compound, not reset each step.

## Failure modes — do not repeat

- **Preheader recap.** Writing the preheader as a shorter subject line. It's the second hook; duplication wastes the inbox's second slot.
- **Bait-and-switch open.** A stat-shock subject followed by a warm-greeting body opener. The first body line must cash the subject's promise.
- **Multi-CTA dilution.** A "main" CTA plus a second link "just in case". One ask; a brand-mandated secondary goes in a soft P.S. only when the brief calls for it.
- **Labeled blocks.** Printing "Subject:", "Preheader:", "Body:" headers. The shape itself (numbered lines, blank lines, order) is the labeling.
- **Wall of text.** Long paragraphs that die in the inbox. 2-4 lines each, break between ideas.
- **Smuggled canon.** Reusing another brand's stats or CTA line (especially Shameless's) for a new brand. Canon is per task; placeholders marked, never borrowed.
- **Sequence amnesia.** Writing a mid-sequence step as a standalone broadcast, repeating the prior touch's ask instead of advancing it.
- **Critique leakage / fences / em dashes.** Same as `dr-script`: corrected artifact only, plaintext only, no em dashes in copy.

## Output discipline checklist

Before printing, verify:

- ✅ 5 numbered subject lines, blank line, 1 preheader, blank line, prose body, blank line, 1 CTA.
- ✅ No fences, no section headers, no "Subject:" / "Body:" labels, no em dashes.
- ✅ Subject lines span distinct angles, not five rewrites.
- ✅ Preheader complements subject, doesn't duplicate.
- ✅ First body line cashes the subject's promise.
- ✅ One idea per paragraph, line breaks between, scannable.
- ✅ Single CTA, named clearly, with verb + object + link.
- ✅ Brand canon honored if supplied; default off-limits respected; placeholders marked if canon missing.
- ✅ Internal critique checklist run in order, every kill-criterion resolved, critique not printed (unless asked).
- ✅ Post-email: ask follow-up to drive toward approval (which subject to lock, send-time, list segment).

## Source memories

Same as `dr-script`:

- `feedback_script_writing_template.md` — 5-options-first pattern, generalized
- `feedback_script_critique_default.md` — silent internal critique
- `feedback_creative_output_plaintext.md` — no fences
- `feedback_no_em_dashes.md` — no em/en dashes in copy
- `feedback_short_responses.md` — zero wrapper text
- `feedback_micro_scripts_default.md` — DSI-grounded copy
