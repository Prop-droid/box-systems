# Skill-description trims (staged, NOT applied)

Covers context-audit Opportunities 1, 2, 4 and the Section-4 routing fixes. These are the always-loaded skill-catalog `description:` frontmatter lines. RULES #2: never edit live skills; this file is a paste-ready map for Tomas review. To apply, replace only the `description:` value in each named `~/.claude/skills/<name>/SKILL.md` (body untouched). Char counts measured against the current live descriptions on 2026-07-04. No em/en dashes anywhere.

How to read each entry: `<skill>  (CURRENT chars -> NEW chars)` then the exact replacement text between the BEGIN/END markers.

---

## Opportunity 1 - the 8 mega descriptions (>700 chars)

### system-control  (959 -> NEW)
<<<BEGIN system-control
Drive a terminal, app, session, or background job once you are ON a machine. macOS via osascript/macos-mcp: open Terminal or iTerm windows and tabs, run commands, activate/quit apps, place windows, read/write clipboard, post notifications, hold awake with caffeinate. Linux box: tmux detached sessions (send-keys, capture-pane), systemd user units, and disconnect-surviving background jobs. Prefers macos-mcp Snapshot to element for GUI acts. Triggers: "open a new terminal", "run this in another window", "control my mac", "keep this running after I disconnect", "start a detached job on the box". For WHICH device or how to reach it (addresses, keys, ports), use fleet-control instead.
END system-control

### clickup-task-creator  (973 -> NEW)
<<<BEGIN clickup-task-creator
EXECUTION layer that creates or updates real ClickUp tasks/briefs on Tomas's Shameless Creative Strategist List (901110066469) via the ClickUp MCP: correct naming, the locked 3-block description, custom-field UUIDs and value formats, and task-type-aware assignee routing. Use whenever Tomas wants a brief to LAND in ClickUp: "create the task(s)", "push this brief to ClickUp", "brief this to [editor]", "make the image-test tasks", "spawn N tasks for [angle]", "create the WL deliverables", "set up the retro". Pairs with creative-brief-builder (which writes the CONTENT). NOT for analytics on existing tasks (use the winners archive) or writing copy/scripts (use shameless-script).
END clickup-task-creator

### shameless-script  (949 -> NEW)
<<<BEGIN shameless-script
Write Shameless Snacks scripts (ad, video, UGC, founder, narrator + B-roll, RD) in the canonical hand-off shape: 5 numbered hooks, blank line, one continuous prose script. Bakes in brand canon (26g fiber, 70 cal, 3g sugar, 3g net carbs), the allowed-language list (prebiotic fiber, food noise, pooping every day), the daily-fiber CTA, and trim defaults; runs the senior-strategist critique internally and ships only the corrected output; on approval saves to the SHA Google Doc template. Use for any Shameless script, ad, UGC, founder confession, narrator + B-roll, hook batch, adaptation, or revision. For non-Shameless brands use dr-script.
END shameless-script

### fleet-control  (841 -> NEW)
<<<BEGIN fleet-control
Operating manual for reaching and controlling Tomas's whole device fleet (MacBook, 24/7 agent box, Nobara PC, Pixel 7 Pro, Lenovo P11 Pro tablet, Steam Deck): hostnames, Tailscale IPs, SSH aliases/keys, adb paths, Fully REST creds, ntfy topics, tmux sessions, NoMachine, Syncthing, and load-bearing gotchas. Use whenever a task must SSH into, screenshot, drive, deploy to, or notify any machine/phone/tablet, when a device is "unreachable" and you need the right address, or when unsure how one box reaches another. For HOW to drive a terminal, app, or background job once you are on the machine, use system-control.
END fleet-control

### dr-script  (915 -> NEW)
<<<BEGIN dr-script
Write DR scripts (ad, video, UGC, founder confession, narrator + B-roll, RD) for ANY brand or client EXCEPT Shameless, in the canonical hand-off shape: 5 numbered hook options, blank line, one continuous prose script. Brand canon supplied per task. Runs the senior-strategist critique internally, ships only corrected output. Plaintext only: no fences, labeled beats, timestamps, or production notes. Use for "write a script/ad", "UGC for X", "founder confession for X", "give me 5 hooks", "adapt this competitor ad", "rewrite this hook". Shameless work uses shameless-script; emails use email-copy; landing/sales pages use landing-page-copy; a standalone tagline uses micro-scripts.
END dr-script

### landing-page-copy  (887 -> NEW)
<<<BEGIN landing-page-copy
Write DR landing-page copy module by module (H1, subhead, value-prop, benefit bullets, proof modules, FAQ, primary/secondary CTA) in clean plaintext. Full-page default: 5 numbered H1 options + subhead + value-prop prose + bullets + proof block + FAQ + CTA; single-module requests get only that module. Brand canon supplied per task; senior-strategist critique applied silently on first drafts. Use for landing/sales page copy, ATF/hero section, PDP, advertorial, long-form sales letter, or "rewrite the LP for X". Ad/video scripts use dr-script or shameless-script; emails use email-copy; a standalone tagline uses micro-scripts.
END landing-page-copy

### gbrain-tag-audit  (791 -> NEW)
<<<BEGIN gbrain-tag-audit
Score and fix tag quality on brain/KB concept pages. Rates every tag pass/warning/fail on relevance, specificity, consistency, and redundancy, for one concept or a batch; also a cheap corpus-wide report mode (orphan tags, over/underused tags, entity-tag-without-mention conflicts). NEVER auto-rewrites tags; fixes only on explicit request, propose-then-confirm. Use for "audit the tags", "check tag quality", "clean up tags on X", "find bad tags", "orphan tags". For tag review use THIS, not concept-synthesis.
END gbrain-tag-audit

### email-copy  (864 -> NEW)
<<<BEGIN email-copy
Write DR email copy (broadcasts, sequence steps, welcome, post-purchase, abandoned-cart, win-back, lapsed-buyer, founder notes, sales/lifecycle) in the canonical hand-off shape: 5 numbered subject-line options, blank line, 1 preheader, blank line, prose body, blank line, single CTA. Plaintext, no fences. Brand canon supplied per task; senior-strategist critique applied silently on first drafts. Use for "write an email", "draft a broadcast", "welcome/abandoned-cart/win-back email", "founder email", "sales email for X", "subject lines for X", "email sequence for X". Ad/video scripts use dr-script or shameless-script; landing pages use landing-page-copy; a standalone tagline uses micro-scripts.
END email-copy

---

## Opportunity 2 - firecrawl cluster

### firecrawl (umbrella)  (699 -> NEW)
<<<BEGIN firecrawl
Firecrawl CLI umbrella for web work: search, scrape, crawl, map, download, and interactive/authenticated sessions. Prefer the specific sub-skill when the action is known (firecrawl-scrape, firecrawl-search, firecrawl-crawl, firecrawl-map, firecrawl-download, firecrawl-interact); use this only when the action is unclear or spans several. On the box, curl and scrapling come first per CLAUDE.md; reach for Firecrawl when those fail on JS-heavy or auth-gated pages.
END firecrawl

### Settings change (needs approval, NOT a description edit)
Disable the 4 `firecrawl-build-*` skills (firecrawl-build-onboarding, firecrawl-build-scrape, firecrawl-build-search, firecrawl-build-interact). They wire Firecrawl into PRODUCT CODE (env keys, SDK setup) which is app-development guidance irrelevant to this box's ops/creative role. Removing them drops ~1,170 chars (~290 tok) from the always-loaded catalog plus four false-positive trigger candidates. This is a skill-enablement/settings change, not a frontmatter edit, so it is staged here as a recommendation only.

---

## Opportunity 4 - 6 more long descriptions

### micro-scripts  (785 -> NEW)  [also resolves the collision with dr-script/shameless-script]
<<<BEGIN micro-scripts
Apply Bill Schley's Micro-Scripts framework to write short, repeatable, story-bite copy that rides word-of-mouth: taglines, headlines, mission statements, slogans, product names, elevator pitches, comment-pinned answers, "make this stickier/shorter/repeatable". Use this for the memorable-phrase layer, NOT full ad scripts or hook batches (those go to dr-script or shameless-script). Trigger: "write a tagline/headline", "name this product", "compress this", "make this repeatable".
END micro-scripts

### script-critique  (733 -> NEW)
<<<BEGIN script-critique
Senior creative-strategist critique of a DR ad/video/UGC/founder/narrator/email/LP script. Returns 5-7 prioritized one-line problems, each pinned to a named failure mode with a concrete fix, plus a trailing "don't touch" line. Assesses against the 8 standard lenses (hook, discovery/pivot, compliance, second surprise, permission close, voice authenticity, brand canon, saturated phrases). Use for "critique this", "strategist pass", "tear it apart", "what's wrong with this script". Also runs silently inside shameless-script and dr-script first drafts.
END script-critique

### interrogate  (695 -> NEW)
<<<BEGIN interrogate
Relentlessly interview Tomas about a plan until shared understanding is reached, walking every branch of the design tree in dependency order, but answering from internal knowledge (Code Things wiki, memory/KB, GBrain, performance data) instead of asking whatever it can already answer. Use when Tomas shares a plan/brief/strategy/campaign and wants it pressure-tested: "interview me about this", "interrogate this plan", "poke holes in this", "let's align", or when executing would mean guessing on 3+ material decisions. For generating NEW ideas use creative-ideation.
END interrogate

### lt-marketplace-search  (653 -> NEW)
<<<BEGIN lt-marketplace-search
Search Lithuanian second-hand marketplaces (Vinted.lt public catalog API + skelbiu.lt) to find, price-check, or monitor any used product, with the proven multi-brand + multi-language query recipe and the known traps baked in (accessory/insole listings, mITX-case traps, PLN-converted prices, which site is stronger per category). Use for "find/price-check X used", "vinted", "skelbiu", "what's it going for locally", "cheap X in Lithuania".
END lt-marketplace-search

### share-to-phone  (622 -> NEW)
<<<BEGIN share-to-phone
Serve any local file (HTML gallery, report, image set, video, PDF) as a tappable URL on Tomas's phone/tablet over Tailscale/LAN, with port hygiene and cleanup tracking; also pushes plain notifications to the tablet via ntfy. Use when Tomas is on mobile and needs to SEE or OPEN a local artifact: "send me a link", "I need this on my phone", "make this tappable", "open this on mobile". The Claude app sends files as attachments, not clickable links, so a served URL is the only good path for anything interactive/HTML.
END share-to-phone

### firecrawl-interact  (734 -> NEW)
<<<BEGIN firecrawl-interact
Control a live browser session on a scraped page: click, fill forms, paginate, handle infinite scroll, log in, and navigate multi-step flows, or retry when a plain scrape failed behind JavaScript. Also does authenticated scraping via profiles. Use for "interact/click/fill the form/log in/sign in/submit", "next page", "infinite scroll", "scrape failed". On the box, Camofox is the stealth-session alternative per CLAUDE.md.
END firecrawl-interact

---

## Section 4 - routing-accuracy fixes (little token change, fix mis-firing)

### maintain  (203 -> NEW)  [add brain-maintenance boundary]
<<<BEGIN maintain
Brain health checks: back-link enforcement, citation audit, filing validation, stale-info and orphan-page detection, benchmarks. Use for "check brain health", "run maintenance", "audit quality". For tag quality use gbrain-tag-audit; for citation formatting use citation-fixer; for merging concept stubs use concept-synthesis.
END maintain

### claude-code  (53 -> NEW)  [disambiguate the delegation quartet]
<<<BEGIN claude-code
Delegate a concrete CODING task (feature, bugfix, PR) to a fresh Claude Code CLI run from within another agent. Use when the current session is Hermes or a subagent and needs real code written/committed elsewhere. For routing heavy analysis/research to Claude Max use claude-heavy-lifting; for Hermes-to-Claude task handoff mechanics use delegate-to-claude.
END claude-code

### claude-heavy-lifting  (keep current text, APPEND one boundary line)
<<<BEGIN claude-heavy-lifting-append
Pick this over claude-code when the work is analysis/research/reasoning rather than shipping code, and over delegate-to-claude when the goal is minimizing ChatGPT/Codex usage.
END claude-heavy-lifting-append

### creative-ideation  (50 -> NEW)  [too vague to fire; collides with brainstorming]
<<<BEGIN creative-ideation
Generate NEW project or product ideas using structured creative constraints (SCAMPER-style forcing, random-input, constraint-flipping). Use for "give me ideas for X", "brainstorm new projects", "what could I build with Y". For pressure-testing an EXISTING plan use interrogate; for feature brainstorming inside a build use superpowers:brainstorming.
END creative-ideation

### humanizer  (50 -> NEW)  [functional but triggerless]
<<<BEGIN humanizer
Humanize text: strip AI-isms and add real voice. Use for "humanize this", "make this sound less like AI", "add my voice", "de-slop this draft".
END humanizer

### delegate-to-claude / minion-orchestrator  (no text change)
Leave both as-is, but confirm each names the other delegation skills once so the router can separate the quartet. If a future edit touches them, add a single cross-ref line naming claude-code + claude-heavy-lifting.
