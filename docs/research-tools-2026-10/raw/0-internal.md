# Internal audit: what the box actually uses for research (2026-10-06)

Source: ~/systems/skill-telemetry/stats.json + report.md, systemctl --user timers, ~/.hermes/logs, curl probes.

## Real usage (telemetry, 1,963 transcripts)
- WebSearch 340 calls, WebFetch 333, scrapling stealthy_fetch 104 + bulk 32. This IS the research stack in practice.
- firecrawl-* skills (6), perplexity-research, data-research, academic-verify: 0 recorded skill invocations. use-perplexity-for-search: 3.
- research-queue (verified fan-out -> adversarial verify -> gate): ran ONCE (2026-07-12 smoke). No timer, no queue rows since.

## Health
- Self-hosted Firecrawl localhost:3002: UP (scrape 200). /search dead: SEARXNG_ENDPOINT unset.
- Perplexity cookie-MCP: token last set 2026-09-01 (~30d life) -> expired or about to; lives in Hermes only, so Claude sessions can't call it at all. Fragile chain: headed Chrome on Xvfb + cookie + unseal patch that npm update wipes.
- No paid search API keys on box (no Exa/Tavily/Brave/Parallel/Jina/Serper). Keys present: GEMINI_API_KEY / GOOGLE_API_KEY, Apify.
- Scheduled research that does run: research-deepdive (lanes, Gemini 2.5 Flash, daily 01:00), research-monitor (Atria diff, daily), atria-weekly, trend-gap (weekly), comments-digest (weekly, now Laya-gated).

## Implication
The bottleneck is not missing tools. Built pieces (Firecrawl, research-queue, Perplexity) sit idle or broken while everything routes through WebSearch/WebFetch. Any new tool must be wired into the default path (an MCP Claude sees + the research-queue sweep lanes) or it will join the unused pile.
