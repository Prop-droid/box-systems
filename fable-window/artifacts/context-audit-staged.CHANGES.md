# Context-audit trims - staged replacements (Task 07 follow-through)

Source of recommendations: `artifacts/context-audit.md`. This staged the top-5 trim targets as paste-ready full replacement files. NOTHING APPLIED (RULES #2). Char->token = chars/4. All files verified free of em/en dashes (RULES #5). Measured against live surfaces 2026-07-04.

## Deliverables (all in artifacts/)

| # | Target | Replacement file | Saved |
|---|---|---|---|
| 1 | 8 mega skill descriptions | skill-descriptions.trimmed.md | ~735 tok (trims) |
| 2 | firecrawl cluster | skill-descriptions.trimmed.md (umbrella + build-* note) | ~60 tok (umbrella) + ~290 tok (build-* disable) |
| 3 | MEMORY.md hooks | MEMORY.md.trimmed | ~288 tok |
| 4 | 6 more long descriptions | skill-descriptions.trimmed.md | ~215 tok (trims) |
| 5 | CLAUDE.md | CLAUDE.md.box.trimmed | ~569 tok |

Rolled-up: ~875 tok from the 15 genuine skill-description trims, minus ~205 tok deliberately re-spent on 4 routing-accuracy expansions (net ~670 tok on descriptions), + ~290 tok if the 4 firecrawl-build-* skills are disabled, + ~288 tok MEMORY.md, + ~569 tok CLAUDE.md. Total realistically applicable at LOW-MED risk: ~1,550 tok, or ~1,820 tok including the firecrawl-build-* settings change.

## Target 5 - CLAUDE.md.box.trimmed (10,386 -> 8,108 chars, ~569 tok)
Refines the earlier `CLAUDE.md.replacement.md`. Same compressions (memory bullets merged, response-style 11->6, URL-handoff folded into the browser section, pain-area defaults collapsed to one line, critical-thinking tightened). Two corrections applied on top:
- **FIXED a fact drift.** The earlier draft silently changed the usage-reset time from `19:00 Europe/Vilnius` (live source) to `00:30`. Restored to **19:00** to match the live file. Flag this: if 00:30 is actually correct, that is a canon change to make deliberately in the live file, not to smuggle through a trim.
- **Removed all 16 em/en dashes** (RULES #5) by converting to hyphens; the earlier draft still had them.
Everything load-bearing preserved verbatim: box identity + systemctl-not-launchd, all paths (~/brain cwd-gating + brain/shameless/cs aliases, ~/systems canonical + Prop-droid/box-systems, retired ~/sha-systems/deploy.sh), service list (:3000 etc.), creds (BQ SA, ClickUp pk, gbrain pgurl), web chain order, Perplexity-parallel rule, three operating modes, Hermes-bounded rule, resume discipline, record-the-workflow rule, gbrain MCP + ~/.bun/bin, ~20k context threshold, confidence-check, fallback-chain, CLARIFICATION_REQUIRED block.

## Target 3 - MEMORY.md.trimmed (19,832 -> 18,681 chars, ~288 tok)
- **All 133 pointer lines kept, all 133 file links kept** (comm-verified: zero dropped links).
- Compressed only the hook text after the separator; separator switched from ` - ` (em dash) to ` - ` (hyphen) for RULES #5.
- **Deliberately did NOT hit the audit's mechanical <=40-char cap.** That cap would have dropped load-bearing tokens: list ID 901110066469, batch SH-16419-16430, LP slug trw-gifts-it2-vp, ntfy tomas-tab-958e4431, IPs 100.78.176.92 / 100.107.26.69 / 192.168.0.120, ports 3000/4030/4000/8092/8765/:99/:9377/5555, driver nvidia 580.142, embeddings @1536d, 1805 pages, keys id_ed25519_mac / github-personal / pixel-box, dates that ARE the point (self-disables 2026-07-17, git baseline 2026-06-09), and helper path ~/systems/lib/hermes_fallback.sh. Every one of these is preserved.
- **Honest gap vs the audit:** the audit projected ~1,000-1,200 tok for MEMORY.md. That figure is only reachable by truncating the IDs/ports/hostnames above, which are the actual routing keys. Fact-safe savings top out near ~290 tok. Recommend accepting the smaller number rather than the lossy one. If Tomas wants the bigger cut, the only safe lever is DELETING whole stale pointer lines (e.g. self-disabled crons past their date), not shortening the survivors, and that is a content decision for him.

## Target 1 - 8 mega descriptions (skill-descriptions.trimmed.md)
system-control, clickup-task-creator, shameless-script, fleet-control, dr-script, landing-page-copy, gbrain-tag-audit, email-copy. Current 6,979 -> new 4,749 chars (~735 tok saved on this group alone at the measured live counts). Dropped redundant trigger-phrase enumerations, kept every routing distinction, ID (901110066469), brand-canon number (26g/70/3g/3g), and cross-skill pointer. Also folded in the Section-4 collision fixes (system-control<->fleet-control, shameless-script<->dr-script boundaries, and dr-script/landing-page-copy/email-copy now each name the other copy skills to break the "ad copy" tie).

## Target 2 - firecrawl cluster
- **firecrawl umbrella** 699 -> 464 chars: now defers to the 6 specific sub-skills and states curl/scrapling come first on the box (kills the 7-way "scrape the web" tie).
- **firecrawl-build-* disable (needs approval, settings not frontmatter):** the 4 product-code-integration skills (onboarding/scrape/search/interact) are app-dev guidance irrelevant to this box; disabling removes ~1,170 chars (~290 tok) and 4 false-positive trigger candidates. Staged as a recommendation only.

## Target 4 - 6 more descriptions + routing fixes
micro-scripts, script-critique, interrogate, lt-marketplace-search, share-to-phone, firecrawl-interact trimmed (~215 tok). Plus Section-4 routing-accuracy fixes that intentionally ADD chars (net +205 tok) to make thin/colliding skills fire correctly: maintain (brain-maintenance boundary), claude-code (disambiguate the delegation quartet), claude-heavy-lifting (append one boundary line), creative-ideation (was 50 chars, too vague vs superpowers:brainstorming), humanizer (added triggers). These buy routing accuracy, not budget.

## Application note
To apply a skill trim: edit only the `description:` value in `~/.claude/skills/<name>/SKILL.md`, leave the body untouched (bodies are lazy-loaded, not part of the always-loaded catalog). MEMORY.md and CLAUDE.md are single-file swaps. None applied here.

## Open questions
1. **19:00 vs 00:30 reset** - confirm the real Vilnius reset time; the prior draft and this one disagree. Live CLAUDE.md says 19:00.
2. **firecrawl-build-* disable** - approve the settings change? ~290 tok + fewer mis-fires, ~zero downside on this box.
3. **MEMORY.md deeper cut** - accept ~290 tok fact-safe, or authorize deleting specific stale pointer lines (past-date self-disabled crons, resolved PARKED items) for a bigger reduction?
4. **~100+ skills figure** in CLAUDE.md - the live catalog resolves to ~84; state an exact number or leave the soft "~100+".
