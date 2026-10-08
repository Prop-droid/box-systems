# Research tools for the box: deep research, 2026-10-06

Scope: which research tools (deep-research agents, search APIs, MCPs, domain data sources) should upgrade the box's research stack. Sources: 4 parallel web sweeps + internal audit, raw files in `raw/` (every claim there carries a URL; vendor numbers are flagged as vendor).

## Verdict

We don't need more tools. Our stack (search -> Firecrawl/Crawl4AI extract -> Camofox fallback) is already what power users converge on (r/hermesagent, r/LocalLLaMA, X: "SearXNG + Firecrawl + Camofox. Done."). What's actually wrong:

1. **Discovery has a single working path.** 340 WebSearch + 333 WebFetch calls in telemetry. Everything else is idle or broken:
   - The Perplexity cookie-MCP token was set 09-01 with about a 30-day life, so it is due or expired. It is Hermes-only, so Claude can't call it at all.
   - Firecrawl `/search` returns `success:true, data:{}`, the empty-success trap: no SearXNG, and the DuckDuckGo fallback is blocked from our IP.
   - Hermes `web.backend` is empty and no search keys are set. Its fallback resolves to Firecrawl cloud with no key, so its native web_search has nothing behind it.
2. **The verification pipeline is idle.** research-queue (fan-out, adversarial verify, gate) has run once, a July smoke test. The firecrawl-*, perplexity-research and data-research skills show 0 uses.
3. **Dedicated "deep research" products don't beat a frontier model with search.** FutureSearch DRB is the only independent harness found, and it puts plain Opus/Sonnet with tools on top. Vendor benchmarks contradict each other.

Fix the plumbing, add one sanctioned paid search key and a free search layer, then point everything at the research-queue.

## Recommended moves (ranked by value/cost)

| # | Move | Cost/mo | Why |
|---|---|---|---|
| 1 | Replace the Perplexity cookie hack with the **official Perplexity API** (Search API, hosted MCP `api.perplexity.ai/mcp`, Agent API presets) | ~$3-15 | Ranks #1 on the independent Artificial Analysis Search Index (80). Kills the 30-day cookie, headed-Chrome-on-Xvfb and unseal-patch chain. One key serves Claude AND Hermes. Agent API `medium` is ~$0.044/run vs old Sonar DR at $0.61 (vendor page). |
| 2 | **SearXNG sidecar into self-hosted Firecrawl** (`SEARXNG_ENDPOINT=http://searxng:8080`, engines `google cse,yandex`). Also point Hermes at it (`SEARXNG_URL`). | $0 | Fixes the empty-success `/search` and gives Hermes native search. Tested live from the box IP: 250/250 queries answered, p50 0.42s. Google CSE hit 429 after ~130 queries, then Yandex carried the rest. Fallback only, rate-limit to ≤20/min. Wiring is in raw/2 §B5b. |
| 3 | **TinyFish Search+Fetch** hosted MCP as the free default discovery layer | $0 | Free, no card, 500 searches/hr, AA score 71. Free policy has no stated expiry, so treat it as a bonus, not a foundation. |
| 4 | **Revive research-queue** as the one headless research entrypoint. Swap its pplx lane from `hermes -z` to the Perplexity API and add a free-search lane. | $0 | It already does what the field doesn't: dual backends, deterministic gate, Killed-claims. Steal list below. |
| 5 | **Claims-verification MCPs**: hosted PubMed connector + OpenAlex / Europe PMC / Semantic Scholar (free keys) | $0 | Health-claim checks for compliance. Scite MCP (~$12/mo) only if we need supporting vs contrasting citation labels. |
| 6 | **Google Trends velocity for VTT**: apply for the official alpha (free); DataForSEO meanwhile | ~$0.5 (+$50 deposit) | VTT's trends lane reads only the Trending Now RSS, so it has no velocity on watchlist terms. |
| 7 | **Apify Starter** | $19 | Free $5 tier is already exhausted by nightly runs. Unlocks TikTok comments, Target/Walmart reviews and TikTok Creative Center top ads (normalized CTR rank, ~$0.0015/ad). MCP already wired. |
| 8 | **Atria MCP**: connect-test it and check our plan | $0 | MCP is listed on every plan. Core caps REST at 1,200 calls/mo, so we may be throttling ourselves. |

Core spend for #1-6: about **$5-20/mo**, plus $19 if we take Apify.

## Steal into research-queue (verified designs, raw/1 §C.4)

- **Required verbatim `quote` per claim + new gate K8:** the quote must be a substring of the fetched page. Deterministic, no LLM. This is the biggest anti-hallucination win, since a 13-word Reddit snippet gets cited in 38-51% of reports (Cornell preprint).
- **Claim fields `sourceQuality`, `publishDate`, `importance`.** Rank on these before the claim cap.
- **Independence clustering before K5.** Five reprints of one press release currently count as five domains.
- **Injection hardening on web text.** Strip bidi and zero-width characters, and frame the text as "evidence, never instructions".
- **Effort tiers `fast/standard/deep` with a budget object** (`maxCost`, `maxDuration`) and a logged `stopReason`.
- **A 20-30 question internal eval with an LLM judge,** so engine swaps are measured on OUR questions, not vendor ones.

## Skip (and why)

- **Packaged open-source deep-research apps** (GPT Researcher, local-deep-research, DeerFlow): they need metered API keys, because Max OAuth is Claude-Code-only by policy. DeerFlow's "Claude Code OAuth" provider conflicts with that policy. STORM and LangChain open_deep_research are stale or archived. Tongyi and MiroThinker need a GPU.
- **OpenAI deep-research models:** retired 2026-07-23, and we have no OpenAI API key.
- **Gemini Deep Research:** $1-7/run, still preview, paid tier unverified. Keep for rare due-diligence runs only.
- **Exa / Tavily as the primary:** fine quality, but paid with no edge over #1-3. Tavily was acquired by Nebius.
- **DTC skips:** Motion ($750+), Exploding Topics API ($1k+), Brandwatch/Sprout ($10k+/yr) and UI-only spy tools (Minea, PiPiAds, BigSpy). Magic Brief is dead (2026-07-31) and GummySearch is closed to new signups.
- **The Meta Ad Library official API:** commercial ads are EU/UK only, so it's useless for US-only Shameless. Atria/Apify stay.

## Gaps nobody fills well

- Amazon review verbatims at scale (public view is ~8 per product).
- Competitor spend/ROAS (it doesn't exist anywhere).
- Compliant Reddit commercial access (approval-gated, price unverified).
- Claim -> FTC/NAD risk mapping: stays in-house (compliance-eval).

## Needs Tomas

- A Perplexity API key + billing card (personal account).
- Whether Shameless has Brand Analytics / Brand Registry. That unlocks the free SP-API Customer Feedback API: weekly review topics per ASIN, the best legit Amazon VoC route.
- Go/no-go on Apify Starter $19.

## Live test: Claude Code bundled /deep-research headless

- `echo '/deep-research <q>' | claude-max -p --output-format stream-json` works headless on this box. Run 2 took ~10 min and cost about $10 in API-equivalent usage, so it is $0 cash on Max but heavy on the 5h window. In `-p` mode the first result is only the launch ack; wait on the stream.
- Use it for rare deep questions, not as a cron lane.

## Free / open-source / local-only path (Tomas follow-up)

The software is free; the web index is not. Every self-hosted search engine scrapes Google, Bing or Yandex, and those throttle it. Measured from the box IP: Google CSE suspended after ~130 queries, Yandex carried the rest.

| Layer | Free local pick | Notes |
|---|---|---|
| Search | SearXNG (38k stars, AGPL) sidecar wired into Firecrawl, plus `mcp-searxng` (1.3k stars) for Claude/Hermes | ~100 queries/hr ceiling. Own-index engines (YaCy, Marginalia, Mwmbl) are too thin for general queries. |
| Extract | Already have it: Firecrawl (189k stars), Crawl4AI, Scrapling, Camofox | All OSS and local. |
| Deep-research engine | Our research-queue, with its pplx lane swapped to a SearXNG lane | Already OSS-shaped and gated. |
| OSS research apps | local-deep-research (MIT, one compose with SearXNG+Ollama) or GPT Researcher (Apache, 30k stars) | The catch is the LLM: no GPU on the box, and Max OAuth is not allowed for third-party apps. They would run on the Gemini free-tier key or a weak CPU model. Skip unless we want a web UI. |
| Dead or avoid | Vane/Perplexica (8 GB images, flaky), DeerFlow (issue pile + OAuth policy conflict), STORM / open_deep_research (stale or archived), Tongyi / MiroThinker (need GPU) | |

Zero-cost plan:
1. SearXNG sidecar + `mcp-searxng`.
2. A research-queue SearXNG lane.
3. Claude WebSearch (included in Max) stays primary.

The Perplexity API (~$3-15/mo) is the only paid add still worth it, as a quality fallback.
