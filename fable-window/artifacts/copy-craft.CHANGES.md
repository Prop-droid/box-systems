# copy-craft skill upgrades — CHANGES (2026-07-02)

Upgraded rewrites of 4 copy-craft skills, following the format conventions established by the shameless-script upgrade (ordered kill-criteria checklist, ship bar, failure-modes section). Output contracts unchanged in all four. All files ≤1.5x original length (actual: 1.19x–1.37x).

## Cross-cutting (all four)

- **Critique pass rebuilt** as an ordered checklist where every step carries an explicit KILL criterion (rewrite, not annotate) plus a concrete "Ship bar" paragraph ending in "if a remaining fix would take under a minute, the draft is not done."
- **Failure-modes section added** — recurring mistakes stated as mistake → correction bullets.
- **Trigger descriptions tightened** with explicit negative routing between the sibling skills (dr-script ↔ email-copy ↔ landing-page-copy ↔ micro-scripts ↔ shameless-script), so the right skill fires on "write an ad" vs "write an email" vs "LP copy" vs "tagline".
- **Em-dash ban made explicit** (per `feedback_no_em_dashes.md`): added to each deliverable-shape rule, each voice kill-criterion, each output checklist, and the source-memories list. Example copy lines inside the skills that themselves contained em dashes were rewritten (they were teaching the model to emit them).
- **Unmarked-placeholder rule**: when brand canon is missing and the user chose to proceed, placeholders must be marked (e.g. `[stat]`) and flagged after the copy — previously silent generic stats were allowed.

## dr-script

- Critique: 8 loose lenses → 8-step kill-criteria checklist (canon/compliance gate first, then hook, pivot, second surprise, close, voice, canon coverage, saturated phrases), mirroring shameless-script's structure.
- Failure modes added: five-rewrites-in-disguise hooks, smuggled canon (borrowing Shameless 26g/70/3/3 for other brands), shape creep (timestamps/B-roll), critique leakage, fences, CTA-as-climax, interrogation instead of drafting, heuristics-over-performance.
- Trigger: added explicit NOT-for list (Shameless, emails, LPs, standalone taglines).
- Removed the deprecated `/ultrareview` mention (now just "audit / review mode").
- Contract unchanged: 5 numbered hooks, blank line, one continuous prose script; brief-mode prepend rule intact.

## email-copy

- Critique: the 8 email lenses kept but converted to KILL form with a compliance gate promoted to step 0; ship bar = "opened by a stranger scanning 50 emails, one ask."
- Failure modes added: preheader recap, bait-and-switch open, multi-CTA dilution, labeled blocks ("Subject:"), wall of text, smuggled canon, sequence amnesia, critique leakage/fences/em dashes.
- CTA example "Eat the whole bag — eatshameless.com" fixed to arrow form (em dash was in example copy).
- Trigger: added NOT-for routing to dr-script / landing-page-copy / micro-scripts.
- Contract unchanged: 5 subjects, preheader, prose body, single CTA; sequence-step section intact.

## landing-page-copy

- Critique: 8 lenses → kill-criteria checklist with compliance gate at step 0 (including guarantee/cure/prevent without legal sign-off); ship bar = ATF answers what/who/why-now in 5 seconds on mobile.
- Failure modes added: full-page dump on a single-module ask, markdown creep, interchangeable H1s, page-goal blindness, FAQ filler, fake proof, body-change before/after, smuggled canon.
- Page goal named as the single highest-leverage clarifying question when ambiguous.
- Two benefit-bullet examples and one bullet in the deliverable shape rewritten to drop em dashes from example copy.
- Trigger: added NOT-for routing; added FAQ/module-level trigger phrases.
- Contract unchanged: 8 modules in order, module name on its own line, single-module mode intact.

## micro-scripts

- **Primary vs companion mode made explicit** — the biggest behavioral change. Old description triggered on nearly all short-form copy, colliding with the three deliverable-shape skills. Now: primary only when the deliverable IS the phrase (tagline, name, headline, mission, pitch, testimonial compression); companion (silent, host contract wins) inside dr-script/shameless-script/email-copy/landing-page-copy. Working Format explicitly gated to primary mode.
- "Output Discipline" → "Candidate gauntlet": same 7 tests reordered with DSI and repeat tests promoted to position 1-2 as HARD KILLS (old rule "fails 3+ → kill" let a DSI-less but pretty line ship); added test 8 (corporate-vocabulary + em-dash sweep); ship bar = both hard kills + 4 of 6, template and ingredient nameable, no padding the shortlist with dead candidates.
- Process section: added scale-to-the-ask rule (full pass for naming/positioning, compressed DSI-first pass for a quick tagline batch).
- Failure modes added: clever-first drafting, Working Format leakage in companion mode, process theater, padding the shortlist, scoring your own cleverness, essay defense, corporate/em-dash leak.
- Book content (4½ rules, templates, ingredients, naming, micro-pitch, mission, testimonials, hostile-defense) preserved intact; anti-patterns section kept.
- Contract unchanged: the 5-step Working Format is verbatim, now explicitly scoped to primary mode.

## Open questions

1. **Stale source-memory citations (verified).** Three slugs cited by the originals do NOT exist in `~/.claude/projects/-home-tomas/memory/`: `feedback_script_writing_template.md`, `feedback_script_critique_default.md`, `feedback_micro_scripts_default.md`. The live equivalent is `script_defaults.md`. Kept the original citations per surgical-change rule; swap them for `script_defaults.md` when installing.
2. **Broken reference path (verified).** `~/.claude/skills/micro-scripts/references/` does not exist; the SKILL.md (original and rewrite) points at `references/the-micro-script-rules-summary.md`. Either restore the summary file or drop the pointer when installing.
3. The three deliverable skills keep Shameless example copy (26g etc.) as illustrations while banning smuggled canon. Intentional (examples teach the shape), but if a stricter firewall is wanted, examples could be genericized.
