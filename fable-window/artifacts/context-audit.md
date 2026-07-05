# Context Audit: always-loaded surfaces

Scope: `~/.claude/CLAUDE.md`, `~/.claude/projects/-home-tomas/memory/MEMORY.md`, and the frontmatter `description:` of every resolved skill under `~/.claude/skills/`. Token estimates use chars/4. Audit run 2026-07-03. Nothing applied (RULES #2); all rewrites are paste-ready drafts + full replacement files in this folder.

## 1. Rough size per surface

| Surface | Chars | ~Tokens | Notes |
|---|---|---|---|
| CLAUDE.md | 10,386 | ~2,600 | always loaded, every session |
| MEMORY.md | 19,030 | ~4,760 | always loaded (userMemory index), ~150 pointer lines |
| Skill descriptions (84 skills) | 28,362 | ~7,090 | always loaded as the skill catalog |
| Skill names (84 x ~18) | ~1,512 | ~380 | part of catalog |
| **Always-loaded total (these 3)** | **~59,290** | **~14,820** | before any tool schemas / MCP / hooks |

Distribution of the 7,090-token skill-description budget:
- 8 skills over 700 chars each = 6,839 chars (~1,710 tok) = 24% of the catalog in 10% of the skills.
- firecrawl family (12 skills) = 5,120 chars (~1,280 tok) = 18% of the catalog, heavy internal overlap, and firecrawl is NOT in the box's preferred web chain (CLAUDE.md says curl to scrapling to camofox to chromium).
- The remaining ~62 skills average ~250 chars each.

Biggest single levers, in order: MEMORY.md hooks (4,760 tok, one file), the skill catalog (7,468 tok, spread), then CLAUDE.md (2,600 tok, one file).

## 2. Top 10 trim opportunities (ranked by tokens-saved x low-risk)

| # | Opportunity | Est. tokens saved | Risk | Type |
|---|---|---|---|---|
| 1 | Trim the 8 mega skill descriptions (>700 chars) to ~470 each, dropping redundant trigger-phrase enumerations, keeping routing distinctions | ~770 | LOW | description edits |
| 2 | firecrawl cluster: disable the 4 `firecrawl-build-*` (product-code integration skills, irrelevant to this box's ops role) + tighten the umbrella | ~290 now, up to ~800 if runtime sub-skills collapse behind umbrella | LOW (build-*), MED (collapse) | settings + description |
| 3 | MEMORY.md hook compression: shorten each pointer hook to ~40 chars, keep every line/link | ~1,000-1,200 | MED (hooks aid recall) | full-file replacement |
| 4 | Trim 6 more long descriptions (micro-scripts, script-critique, interrogate, lt-marketplace-search, share-to-phone, firecrawl-interact) to ~350 | ~450 | LOW | description edits |
| 5 | CLAUDE.md: collapse the bottom "Browser: URL-handoff" section to a 2-line pointer (full text lives in memory feedback_browser_url_handoff) + compress duplicated memory/skill-first prose | ~350 | LOW-MED | full-file replacement |
| 6 | CLAUDE.md: compress Response-style (11 bullets to 6) and Autonomous pain-area defaults (redundant with the memory index) | ~325 | MED | full-file replacement |
| 7 | Fix trigger-accuracy collisions among delegation skills (claude-code / claude-heavy-lifting / delegate-to-claude / minion-orchestrator) with disambiguating one-liners | ~0 tok, routing quality | LOW | description edits |
| 8 | Disambiguate micro-scripts vs dr-script/shameless-script (both fire on "ad copy", "write a hook") | small, routing quality | LOW | description edits |
| 9 | Sharpen the too-vague ones that won't fire (creative-ideation, humanizer) or collide (creative-ideation vs superpowers:brainstorming) | ~0 tok, recall quality | LOW | description edits |
| 10 | Brain-maintenance overlap (maintain / gbrain-tag-audit / citation-fixer / concept-synthesis / brain-ops) needs explicit boundaries in each description | small, routing quality | LOW | description edits |

Notes:
- #1, #2(build-*), #4, #5 together save ~1,860 tokens at LOW risk and are the recommended first pass.
- #3 (MEMORY.md) is the single largest number but is MED risk: the hook text is what a future session reads to decide which memory file to open, so over-trimming hurts recall. Delivered as a mechanical recipe + sample below, not a hasty 150-line rewrite.
- Items #7-#10 save little raw budget but materially improve routing accuracy (the second half of the task).

## 3. Top 5: drafted replacement text (paste-ready)

RULES #5: no em dashes anywhere below. Preserve all load-bearing routing facts (IDs, cross-links, brand canon numbers).

### Opportunity 1 - the 8 mega descriptions

**system-control** (959 -> ~560)
```
Drive a terminal, app, session, or background job once you are ON a machine. macOS via osascript/macos-mcp: open Terminal or iTerm windows and tabs, run commands, activate/quit apps, place windows, read/write clipboard, post notifications, hold awake with caffeinate. Linux box: tmux detached sessions (send-keys, capture-pane), systemd user units, and disconnect-surviving background jobs. Prefers macos-mcp Snapshot to element for GUI acts. Triggers: "open a new terminal", "run this in another window", "control my mac", "keep this running after I disconnect", "start a detached job on the box". For WHICH device or how to reach it (addresses, keys, ports), use fleet-control instead.
```

**clickup-task-creator** (926 -> ~560)
```
EXECUTION layer that creates or updates real ClickUp tasks/briefs on Tomas's Shameless Creative Strategist List (901110066469) via the ClickUp MCP: correct naming, the locked 3-block description, custom-field UUIDs and value formats, and task-type-aware assignee routing. Use whenever Tomas wants a brief to LAND in ClickUp: "create the task(s)", "push this brief to ClickUp", "brief this to [editor]", "make the image-test tasks", "spawn N tasks for [angle]", "create the WL deliverables", "set up the retro". Pairs with creative-brief-builder (which writes the CONTENT). NOT for analytics on existing tasks (use the winners archive) or writing copy/scripts (use shameless-script).
```

**shameless-script** (924 -> ~490)
```
Write Shameless Snacks scripts (ad, video, UGC, founder, narrator + B-roll, RD) in the canonical hand-off shape: 5 numbered hooks, blank line, one continuous prose script. Bakes in brand canon (26g fiber, 70 cal, 3g sugar, 3g net carbs), the allowed-language list (prebiotic fiber, food noise, pooping every day), the daily-fiber CTA, and trim defaults; runs the senior-strategist critique internally and ships only the corrected output; on approval saves to the SHA Google Doc template. Use for any Shameless script, ad, UGC, founder confession, narrator + B-roll, hook batch, adaptation, or revision. For non-Shameless brands use dr-script.
```

**fleet-control** (841 -> ~560)
```
Operating manual for reaching and controlling Tomas's whole device fleet (MacBook, 24/7 agent box, Nobara PC, Pixel 7 Pro, Lenovo P11 Pro tablet, Steam Deck): hostnames, Tailscale IPs, SSH aliases/keys, adb paths, Fully REST creds, ntfy topics, tmux sessions, NoMachine, Syncthing, and load-bearing gotchas. Use whenever a task must SSH into, screenshot, drive, deploy to, or notify any machine/phone/tablet, when a device is "unreachable" and you need the right address, or when unsure how one box reaches another. For HOW to drive a terminal, app, or background job once you are on the machine, use system-control.
```

**dr-script** (837 -> ~490)
```
Write DR scripts (ad, video, UGC, founder confession, narrator + B-roll, RD) for ANY brand or client EXCEPT Shameless, in the canonical hand-off shape: 5 numbered hook options, blank line, one continuous prose script. Brand canon supplied per task. Runs the senior-strategist critique internally, ships only corrected output. Plaintext only: no fences, labeled beats, timestamps, or production notes. Use for "write a script/ad", "UGC for X", "founder confession for X", "give me 5 hooks", "adapt this competitor ad", "rewrite this hook". Shameless work uses shameless-script.
```

**landing-page-copy** (826 -> ~400)
```
Write DR landing-page copy module by module (H1, subhead, value-prop, proof modules, FAQ, primary/secondary CTA) in clean plaintext. Default output: 5 numbered H1 options + subhead + value-prop prose + proof block + FAQ + CTA. Brand canon supplied per task; senior-strategist critique applied silently on first drafts. Use for landing/sales page copy, ATF/hero section, PDP, advertorial, long-form sales letter, or "rewrite the LP for X".
```

**gbrain-tag-audit** (791 -> ~470)
```
Score and fix tag quality on brain/KB concept pages. Rates every tag pass/warning/fail on relevance, specificity, consistency, and redundancy, for one concept or a batch; also a cheap corpus-wide report mode (orphan tags, over/underused tags, entity-tag-without-mention conflicts). NEVER auto-rewrites tags; fixes only on explicit request, propose-then-confirm. Use for "audit the tags", "check tag quality", "clean up tags on X", "find bad tags", "orphan tags". For tag review use THIS, not concept-synthesis.
```

**email-copy** (735 -> ~370)
```
Write DR email copy (subject line, preheader, body, single CTA) in a clean hand-off shape. Default output: 5 numbered subject-line options + preheader + prose body + CTA, plaintext, no fences. Brand canon supplied per task; senior-strategist critique applied silently on first drafts. Use for any marketing email: broadcast, sequence step, welcome flow, abandoned-cart, win-back, founder note, sales email, or "subject lines for X".
```

New total for the 8: ~3,900 chars vs 6,839. Saved ~2,940 chars (~735 tok).

### Opportunity 2 - firecrawl cluster

Fact: CLAUDE.md's web chain is curl -> scrapling -> Camofox -> headless Chromium. Firecrawl is not in it, yet 12 firecrawl skills consume ~1,280 tok of always-loaded catalog.

Low-risk now (description tightening of the umbrella, which currently overlaps all 6 runtime sub-skills):

**firecrawl** (699 -> ~300)
```
Firecrawl CLI umbrella for web work: search, scrape, crawl, map, download, and interactive/authenticated sessions. Prefer the specific sub-skill when the action is known (firecrawl-scrape, firecrawl-search, firecrawl-crawl, firecrawl-map, firecrawl-download, firecrawl-interact); use this only when the action is unclear or spans several. On the box, curl and scrapling come first per CLAUDE.md; reach for Firecrawl when those fail on JS-heavy or auth-gated pages.
```

Strategic (needs approval, settings change, not applied): the 4 `firecrawl-build-*` skills (onboarding, scrape, search, interact) are about wiring Firecrawl into PRODUCT CODE (env keys, SDK setup). That is app-development guidance irrelevant to this box's ops/creative role. Disabling those 4 removes ~1,170 chars (~290 tok) and four false-positive trigger candidates from the catalog with essentially zero downside here.

### Opportunity 3 - MEMORY.md hook compression (recipe + sample)

Do not delete lines or links (each points to a real memory file). Compress only the hook after the em-dash-equivalent separator to <=40 chars. Full replacement file should keep the exact `- [Title](file.md) - hook` shape and every link. Sample before/after:

Before:
```
- [SHA angle-canon + naming](feedback_sha_task_angle_canon_naming.md) - angle names are canon; name needs script-name token; OUTPUT = "10 videos"
- [Winner patterns 2026H1](feedback_winner_patterns_2026H1.md) - 14 canon shapes from 334 winners; retros 43%, statics = factory, offer-wrapper mandatory; check every brief against it
- [ClickUp REST API fallback](reference_clickup_rest_api_fallback.md) - MCP hides attachments; pk_ token on disk; attachments survive description edits (recoverable); capture `![]()` before overwriting
```
After:
```
- [SHA angle-canon + naming](feedback_sha_task_angle_canon_naming.md) - angle names canon; script-name token in name
- [Winner patterns 2026H1](feedback_winner_patterns_2026H1.md) - 14 canon shapes; check every brief
- [ClickUp REST API fallback](reference_clickup_rest_api_fallback.md) - MCP hides attachments; pk_ token on disk
```
Applied across the ~90 lines whose hook exceeds 40 chars, this saves ~1,000-1,200 tokens while the title + link (the actual routing key) stay intact. Recommend running this as its own dedicated pass with a diff review, since the hooks are recall-load-bearing. Not drafted as a full 150-line file here to avoid a rushed rewrite that drops a nuance.

### Opportunity 4 - 6 more long descriptions

**micro-scripts** (702 -> ~330) - also fixes the collision with dr-script/shameless-script:
```
Apply Bill Schley's Micro-Scripts framework to write short, repeatable, story-bite copy that rides word-of-mouth: taglines, headlines, mission statements, slogans, product names, elevator pitches, comment-pinned answers, "make this stickier/shorter/repeatable". Use this for the memorable-phrase layer, NOT full ad scripts or hook batches (those go to dr-script or shameless-script). Trigger: "write a tagline/headline", "name this product", "compress this", "make this repeatable".
```

**script-critique** (733 -> ~350)
```
Senior creative-strategist critique of a DR ad/video/UGC/founder/narrator/email/LP script. Returns 5-7 prioritized one-line problems, each pinned to a named failure mode with a concrete fix, plus a trailing "don't touch" line. Assesses against the 8 standard lenses (hook, discovery/pivot, compliance, second surprise, permission close, voice authenticity, brand canon, saturated phrases). Use for "critique this", "strategist pass", "tear it apart", "what's wrong with this script". Also runs silently inside shameless-script and dr-script first drafts.
```

**interrogate** (695 -> ~330)
```
Relentlessly interview Tomas about a plan until shared understanding is reached, walking every branch of the design tree in dependency order, but answering from internal knowledge (Code Things wiki, memory/KB, GBrain, performance data) instead of asking whatever it can already answer. Use when Tomas shares a plan/brief/strategy/campaign and wants it pressure-tested: "interview me about this", "interrogate this plan", "poke holes in this", "let's align", or when executing would mean guessing on 3+ material decisions.
```

**lt-marketplace-search** (653 -> ~340)
```
Search Lithuanian second-hand marketplaces (Vinted.lt public catalog API + skelbiu.lt) to find, price-check, or monitor any used product, with the proven multi-brand + multi-language query recipe and the known traps baked in (accessory/insole listings, mITX-case traps, PLN-converted prices, which site is stronger per category). Use for "find/price-check X used", "vinted", "skelbiu", "what's it going for locally", "cheap X in Lithuania".
```

**share-to-phone** (622 -> ~330)
```
Serve any local file (HTML gallery, report, image set, video, PDF) as a tappable URL on Tomas's phone/tablet over Tailscale/LAN, with port hygiene and cleanup tracking; also pushes plain notifications to the tablet via ntfy. Use when Tomas is on mobile and needs to SEE or OPEN a local artifact: "send me a link", "I need this on my phone", "make this tappable", "open this on mobile". The Claude app sends files as attachments, not clickable links, so a served URL is the only good path for anything interactive/HTML.
```

**firecrawl-interact** (734 -> ~350)
```
Control a live browser session on a scraped page: click, fill forms, paginate, handle infinite scroll, log in, and navigate multi-step flows, or retry when a plain scrape failed behind JavaScript. Also does authenticated scraping via profiles. Use for "interact/click/fill the form/log in/sign in/submit", "next page", "infinite scroll", "scrape failed". On the box, Camofox is the stealth-session alternative per CLAUDE.md.
```

### Opportunity 5 - CLAUDE.md

Full replacement delivered as `~/fable-window/artifacts/CLAUDE.md.replacement.md` with a CHANGES section. Net ~10,386 -> ~8,000 chars (~600 tok saved). Only genuinely redundant prose compressed; every path, cred, service name, ID, and the 00:30 reset fact preserved verbatim.

## 4. Descriptions that hurt trigger accuracy (with rewrites)

Two failure modes: (A) too long/overlapping = dilution and mis-routing; (B) too vague/short = won't fire when it should.

### A. Collisions (mis-routing)

1. **firecrawl umbrella vs its 6 runtime sub-skills vs WebFetch/scrapling** - a 7+ way tie on "scrape / search the web / crawl / fetch this page". The umbrella currently claims every phrase its children do. Fix: umbrella rewrite in Opportunity 2 (defer to the specific sub-skill; note curl/scrapling come first on the box).

2. **micro-scripts vs dr-script / shameless-script** - all three fire on "ad copy", "video script", "write a hook". micro-scripts should own only the short memorable-phrase layer. Fix: micro-scripts rewrite in Opportunity 4 (explicit "NOT full ad scripts or hook batches").

3. **Delegation quartet: claude-code / claude-heavy-lifting / delegate-to-claude / minion-orchestrator** - four skills about handing work to Claude Code/subagents, none stating when to pick which. Disambiguating rewrites:
   - **claude-code** (51 -> ~180)
   ```
   Delegate a concrete CODING task (feature, bugfix, PR) to a fresh Claude Code CLI run from within another agent. Use when the current session is Hermes or a subagent and needs real code written/committed elsewhere. For routing heavy analysis/research to Claude Max, use claude-heavy-lifting; for Hermes-to-Claude task handoff mechanics, use delegate-to-claude.
   ```
   - **claude-heavy-lifting** (413, keep but add boundary line): append "Pick this over claude-code when the work is analysis/research/reasoning rather than shipping code, and over delegate-to-claude when the goal is minimizing ChatGPT/Codex usage."
   - Leave delegate-to-claude and minion-orchestrator as-is but ensure each names the other two once (one-line cross-ref) so the router can separate them.

4. **Brain-maintenance overlap: maintain / gbrain-tag-audit / citation-fixer / concept-synthesis / brain-ops** - overlapping "audit/clean up the brain". gbrain-tag-audit already carves out "tags, not concept-synthesis" (good). Add a one-line boundary to **maintain**:
   ```
   Brain health checks: back-link enforcement, citation audit, filing validation, stale-info and orphan-page detection, benchmarks. Use for "check brain health / run maintenance / audit quality". For tag quality use gbrain-tag-audit; for citation formatting use citation-fixer; for merging concept stubs use concept-synthesis.
   ```

### B. Too vague / won't fire

5. **creative-ideation** (48) "Generate project ideas via creative constraints." - collides with superpowers:brainstorming and is too thin to fire reliably. Rewrite:
   ```
   Generate NEW project or product ideas using structured creative constraints (SCAMPER-style forcing, random-input, constraint-flipping). Use for "give me ideas for X", "brainstorm new projects", "what could I build with Y". For pressure-testing an EXISTING plan use interrogate; for feature brainstorming inside a build use superpowers:brainstorming.
   ```

6. **humanizer** (48) "Humanize text: strip AI-isms and add real voice." - functional but triggerless. Add: `Use for "humanize this", "make this sound less like AI", "add my voice", "de-slop this draft".`

Net: section 4 saves little raw budget but removes the main sources of wrong-skill firing and non-firing. Combine with the Opportunity 1/4 rewrites, which already resolve collisions 1 and 2.

## Summary of safe-to-apply-now vs needs-approval

- Apply now (LOW risk, description edits only): Opportunities 1, 4, and the umbrella/collision rewrites in section 4. ~1,200 tok + routing fixes.
- Apply now, file-level (LOW-MED): CLAUDE.md replacement (Opportunity 5, full file provided).
- Needs approval / own pass: MEMORY.md hook compression (Opportunity 3, MED risk, recipe provided) and disabling the 4 firecrawl-build-* skills (settings change).
