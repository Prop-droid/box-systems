# Tool videos — batch 2 walkthrough (2026-08-13)

Second pass over the saved-video "tool" bucket. What I think, mapped to your stack.

## Worth a look (new leverage)

- **CloakBrowser** — `CloakHQ/CloakBrowser` (★30k, MIT). Stealth Chromium, fingerprints patched at C++ source: scores 0.9 on reCAPTCHA v3 (human-level), passes 14/14 bot tests, auto-resolves Cloudflare Turnstile, beats FingerprintJS. Also `CloakHQ/CloakBrowser-Manager` (profile manager). **My take: the single most relevant find for you** — a stronger anti-bot layer than Camofox for the hardest scrape targets. Worth trialing against a site Camofox currently fails.
- **SkillOpt** — `microsoft/SkillOpt` (★16k). Text-space optimizer that trains reusable NL skills; a base model runs the task, an optimizer rewrites the instructions. **My take: directly on-theme with your self-improve loop / rule-gate** — this is the "skills improve themselves" idea done by Microsoft. Worth reading even if you don't adopt wholesale.
- **book-to-skill** — `virgiliojr94/book-to-skill` (★21k). Turn any technical book PDF into a Claude Code skill so the agent answers from the exact chapter (low hallucination). Complements the `watch` (video→skill) install.
- **Pinchtab** — `pinchtab/pinchtab` (★10k). Browser control for any agent over a plain HTTP API (curl works), single Go binary, no SDK lock-in. Also `BDuba/pinchtab-mcp-wrapper` (token-efficient MCP). Overlaps agent-browser; pick one.

## Marginal / overlaps what you have

- **PixelRAG** — visual document search ("screenshots beat text"): render pages to images, search by how they *look*. Apache-2.0. Core repo is comment-gated (search only surfaced LangChain wrappers). Overlaps gbrain + your vision reads; interesting for messy-layout scraping, not urgent.
- **Ponytail** — a "senior dev" code-review/architecture skill (claims 80-94% less code, 3-6x faster vs no-skill agent). Exact repo unresolved; appears bundled in Hermes skillpacks (e.g. `kimyoungwopo/frontend-token-trim-skillpack`). Overlaps your `premortem` + karpathy-guidelines. Skip unless you want the benchmark harness.
- **Ghost Downloader** (`XiaoYouChR/Ghost-Downloader-3`, ★8k) and the "downloader" reel (remy.engineering) which is just **yt-dlp** — you already run yt-dlp. Nothing new.
- **Leantime** — open-source project management (goals→tasks, Lean Canvas/SWOT). General PM tool, not agent-specific.

## Flagged — dual-use / not recommended

- **Decepticon** — "autonomous AI red team with full kill chain." Offensive-security automation. I did not scaffold or resolve an install; noting only that it exists. Not relevant to your creative/agent work.
- **Osiris** ("open-source Palantir") and **Mirofish** ("thousands of AI agents") — surveillance/swarm framing, unresolved repos, low relevance. Left alone.
