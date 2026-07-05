# CLAUDE.md replacement — CHANGES

Source: `~/.claude/CLAUDE.md` (10,386 chars, ~2,600 tok)
Replacement: `CLAUDE.md.replacement.md` (8,129 chars, ~2,030 tok)
Saved: ~2,257 chars (~565 tok, ~22%). Not applied (RULES #2); paste-ready full file.

## What changed and why
- **Merged the two memory bullets** into three tighter lines. Kept the path, the userMemory auto-inject fact, the point-in-time-verify warning, and the gbrain pointer. Dropped the parenthetical history about the SessionStart hook once double-loading (operational trivia, not load-bearing).
- **Response style: 11 bullets to 6.** Same guidance, de-duplicated (several bullets restated "be short/lead with the answer"). Overlaps memory `feedback_short_responses`; kept the terminal-formatting and headless-run specifics.
- **Browser section: folded the bottom "Browser: URL-handoff pattern" block into the Browser automation section** as one bullet pointing to memory `feedback_browser_url_handoff`. Removed the duplicated multi-sentence restatement (the full pattern already lives in that memory file). Saved the largest single redundant block.
- **Autonomous section: compressed the pain-area defaults list** to a single line naming the routes, because the full list duplicates the memory index (which is always loaded right below). Kept the confidence-check, fallback-chain, and CLARIFICATION_REQUIRED protocol verbatim.
- **Critical-thinking section: tightened from two dense paragraphs to two shorter ones.** No rule removed; removed restated framing.

## Preserved verbatim (load-bearing, unchanged)
- Box identity, `systemctl --user` not launchd.
- All paths: `~/brain`, cwd-gating + `brain`/`shameless`/`cs` aliases, `~/systems/` canonical + `Prop-droid/box-systems` git, retired `~/sha-systems`/`deploy.sh`.
- Services list (creative-command-center :3000, hermes-gateway, agentic-bots, camofox, tablet-dash + android MCP).
- Creds: BQ SA, ClickUp `pk`, gbrain pgurl paths.
- Web chain order (curl -> scrapling -> Camofox -> Chromium), Perplexity-parallel rule, downloads path.
- Three operating modes, Hermes-bounded rule, **00:30 Europe/Vilnius reset** + resume discipline, record-the-workflow rule.
- gbrain MCP + `~/.bun/bin` CLI, context-budget ~20k threshold.

## Open questions
- The "~108 skills" figure in the original was softened to "~100+" (count fluctuates; the resolved catalog today is ~84). Confirm the number you want stated, or drop it.
- If you prefer zero behavioral drift, the safest subset to apply is just the URL-handoff fold + response-style dedup (~700 chars), leaving the autonomous/critical-thinking prose untouched.
