# Search / retrieval APIs and MCP servers for the agent box (as of 2026-10-06)

Slice 2 of research-tools-2026-10. Every row has a source URL. Items I could not confirm from a primary source are marked UNVERIFIED. Vendor-authored benchmarks are marked VENDOR. Monthly cost math assumes 1 request = 1 search, basic depth, no full-content add-ons, 30-day month: 100/day = 3,000/mo, 300/day = 9,000/mo.

## 0. Headline findings

1. Firecrawl self-host /search is not "dead because SEARXNG_ENDPOINT is unset" in the sense of a missing feature. Code order (apps/api/src/search/v2/index.ts @ commit 4244638, 2026-10-02): fire-engine (cloud-only) -> SearXNG if SEARXNG_ENDPOINT set -> DuckDuckGo HTML scrape fallback -> `{}`. DDG fallback is blocked from the box IP (HTML contains `anomaly-modal`; I measured it), so it returns `{"success":true,"data":{}}` (the "empty = success" trap). Source: local checkout ~/firecrawl/apps/api/src/search/v2/index.ts, ddgsearch.ts; upstream https://github.com/firecrawl/firecrawl
2. Exact env vars (config.ts lines 357-359, docker-compose.yaml lines 55-57 already forward them): `SEARXNG_ENDPOINT`, `SEARXNG_ENGINES`, `SEARXNG_CATEGORIES`. Firecrawl appends `/search` itself and requests `format=json`, `pageno`, `language`, `engines`, `categories`; it ignores country, location, num and time filters (tbs) for SearXNG. Source: ~/firecrawl/apps/api/src/search/v2/searxng.ts
3. I ran a throwaway SearXNG container on the box (127.0.0.1:8899, removed afterwards; Firecrawl stack untouched) and measured it from the box's residential IP. Result: it works but is a one-or-two-engine service in practice (Google via the blackle CSE token, Yandex), the Google CSE engine tripped HTTP 429 after roughly 130-140 queries in about 25 minutes, and Yandex then carried 225 more queries at ~1 q/s with zero failures (250/250 non-empty, p50 0.42 s). Viable as a free fallback, not as the primary. Exact wiring steps are in B5b.
4. New 2026 entrant that changes the economics: TinyFish Search + Fetch, free (30 search req/min, 500/hr, no card), hosted MCP, independent AA Search Index score 71. https://www.tinyfish.ai/pricing , https://tinyfish.ai/blog/search-and-fetch-are-now-free-for-every-agent-everywhere
5. Independent leaderboard (Artificial Analysis Search Index, data Sep 28, 2026) puts Perplexity's official Search API first (80), above Brave LLM Context (75), Parallel Advanced (75), Exa Auto (74), You.com (74), Firecrawl (73). The official Perplexity Search API ($5/1k) is the right replacement for the cookie-hijack MCP. https://artificialanalysis.ai/agents/search-api
6. Google Custom Search JSON API is closed to new customers and ends 2027-01-01; Bing Search API retired 2025-08-11. Neither is an option. https://developers.google.com/custom-search/v1/overview , https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement

## A. Search / retrieval APIs

### A1. Pricing, free tier, MCP (all per 1,000 requests unless stated)

| Provider | Free tier | Price / 1k | Latency (source) | Own index? | Official MCP | Pricing source |
|---|---|---|---|---|---|---|
| TinyFish Search | Free, no card, 30 req/min, 500/hr, key required | $0 (Fetch also free: 150 URLs/min, 1,000/day) | p50 ~360-556 ms (VENDOR/bitdoze) | Live-web results via own Chromium fleet (index details not published) | Yes, hosted `https://agent.tinyfish.ai/mcp` | https://www.tinyfish.ai/pricing , https://tinyfish.ai/blog/search-and-fetch-are-now-free-for-every-agent-everywhere , https://www.bitdoze.com/tinyfish-ai-agents-web-search/ |
| Parallel Search API | $5 free credit/month (= up to 5,000 Turbo searches) + signup bonus up to $80 | Turbo $1, Fast $1, Basic $5, Advanced $5; extra results beyond 10 = $1/1k; Extract $1/1k | Turbo ~216-348 ms, Fast ~700-940 ms, Basic ~2.9 s, Pro ~13.6 s | Yes, own index | Yes, `https://search.parallel.ai/mcp` keyless (Fast mode, lower limits) or `/mcp-oauth`; tools web_search, web_fetch | https://parallel.ai/pricing , https://docs.parallel.ai/integrations/mcp/search-mcp , https://parallel.ai/articles/most-powerful-search-api-for-ai.md (free-credit detail) |
| Brave Search API | $5 credit/month (~1,000 searches); needs a card; credit tied to attribution per AlternativeTo (UNVERIFIED on Brave's own page) | Search $5 (50 qps); LLM Context $5 (same key); Answers/AI Grounding $4 + $5/M tokens (2 qps) | 430-670 ms | Yes, independent index | Yes, local `@brave/brave-search-mcp-server` (stdio default, optional http), needs BRAVE_API_KEY | https://brave.com/search/api/ , https://alternativeto.net/news/2026/2/brave-updates-its-search-api-with-a-new-llm-context-endpoint-for-ai-and-new-pricing , https://github.com/brave/brave-search-mcp-server |
| Exa | $10 credits at signup, resets to $10 on the 1st of each month (= 2,500 Instant searches) | Instant $4, Fast/Auto $7, Deep-lite/Deep $12, Deep-reasoning $15; >10 results +$1/1k; Contents $1/1k pages; Answer $5; Agent $0.012-$1/request | Instant ~178 ms (Exa test, Feb 2026), 361-398 ms (Parallel/Openbenchmarks), Fast ~652 ms | Yes, own neural index | Yes, hosted `https://mcp.exa.ai/mcp` keyless rate-limited; OAuth or x-api-key for limits; tools web_search_exa, web_fetch_exa (+advanced, agent_run) | https://exa.ai/pricing , https://exa.ai/docs/reference/exa-mcp , https://github.com/exa-labs/exa-mcp-server |
| Perplexity Search API (official) | None listed. Third-party says Pro subscribers get $5/month API credit (UNVERIFIED, https://pricepertoken.com/subscriptions/perplexity ) | Standard Search $5; Fast Search $1; rate limit 50 query-units/s all tiers | Not published on pricing page; AA time/task 27.5 s (agent task, not per call) | Yes (own index, ranked snippets) | Yes, hosted `https://api.perplexity.ai/mcp` with Bearer key, or local `npx @perplexity-ai/mcp-server`; tools perplexity_search, _ask, _research, _reason | https://docs.perplexity.ai/docs/getting-started/pricing , https://docs.perplexity.ai/docs/search/quickstart , https://docs.perplexity.ai/docs/admin/rate-limits-usage-tiers , https://github.com/perplexityai/modelcontextprotocol |
| Perplexity Sonar (answers) | none | Sonar: $1/M in+out tokens + request fee $5/$8/$12 (low/med/high ctx). Sonar Pro: $3 in / $15 out per M + $6/$10/$14. Sonar Reasoning Pro: $2 in / $8 out + $6/$10/$14. Deep Research: $2/$8 per M + $2/M citation + $3/M reasoning + $5/1k searches | Sonar ~11 s in AIMultiple test | Yes | same MCP as above | https://docs.perplexity.ai/docs/getting-started/pricing , https://aimultiple.com/agentic-search |
| Tavily | 1,000 credits/month, no card | PAYG $0.008/credit = $8/1k basic searches (advanced = 2 credits). Plans: $30 / 4,000 credits, $100 / 15,000, $220 / 38,000, $500 / 100,000. Extract 1 credit per 5 URLs | ~357 ms (Ultra Fast) to ~1 s (basic) | Mixed (aggregator + own) | Yes, hosted `https://mcp.tavily.com/mcp` (API key in URL/header or OAuth); local npx also | https://www.tavily.com/pricing , https://docs.tavily.com/documentation/api-credits , https://github.com/tavily-ai/tavily-mcp . Note: Nebius agreed to acquire Tavily Feb 2026; pricing unchanged (secondary: https://usagepricing.com/blueprint/activity/2026-02-10-tavily-nebius-acquisition ) |
| You.com Search API | $100 free credits, no card (secondary, https://about.you.com/resources/lower-search-api-cost ); keyless MCP free profile 100 queries/day | Web Search $5, Contents $1, Answer $5, Research $12-$1,200 by effort (secondary: https://costbench.com/software/ai-search-apis/you-com-api/ ) | not published | Yes | Yes, `https://api.you.com/mcp` (free profile at `?profile=free`, no key) | https://you.com/apis , https://about.you.com/resources/lower-search-api-cost |
| Linkup | 4,000 queries free (one-time) | Search $0.005-$0.006, Fetch $0.001-$0.006, Research $0.25-$2.50 per request | not published | Own + partner content | Yes, hosted `https://mcp.linkup.so/mcp` (Bearer or ?apiKey=), local stdio | https://www.linkup.so/pricing , https://github.com/LinkupPlatform/linkup-mcp-server |
| Octen (new) | $5 free balance at signup | Web Search $1 (shown as 80% off from $5, so likely promo), +$0.5/1k full-content results beyond 10 free per call; Extract $1; News $3; Business $5 | claims 79 ms (VENDOR) | Own real-time index | Yes (Skill, MCP, CLI; URL not verified) | https://octen.ai/pricing (scraped with local Firecrawl) |
| Valyu | $10 credits ($20 with work email) | Web $1.50, open DBs $0.50, finance $8, proprietary $30-50; plans $29-$449/mo | not published | Web + licensed datasets | Only a docs MCP verified (`https://docs.valyu.ai/mcp`); search MCP UNVERIFIED | https://docs.valyu.ai/pricing |
| Keenable (new) | Keyless MCP on shared public tier with an hourly cap (number not found); free key lifts cap | UNVERIFIED (pricing page would not render) | not published | own | Yes, `https://api.keenable.ai/mcp` | https://docs.keenable.ai/mcp-server.md |
| Serper.dev | 2,500 queries free, no card | Prepaid packs, $50/50k = $1/1k down to $0.30/1k; credits expire after 6 months (tiers from third-party; raw HTML of serper.dev shows $1.00/$0.75/$0.50/$0.30 price points) | "1-2 s" (VENDOR) | Live Google SERP (snippets only, no page content) | No official MCP found; community only | https://serper.dev , https://apiserpent.com/blog/serper-pricing-credits-explained (third-party, competitor) |
| SerpApi | 250 searches/month | Starter $25/1k, Developer $75/5k ($15/1k), Production $150/15k ($10/1k), Big Data $275/30k, Searcher $725/100k | ~1-2.4 s | Live SERP | Community only | https://serpapi.com/pricing |
| DataForSEO SERP | Free sandbox | Google organic: standard queue $0.6/1k (~5 min turnaround), high priority $1.2/1k (~1 min), Live $2/1k (~6 s); billed per 10-result SERP | Live ~6 s | Live SERP | Community only | https://dataforseo.com/pricing/google-serp/google-organic-serp-api |
| Firecrawl cloud search | 1,000 credits/month; /search 10 req/min on free | Search = 2 credits per 10 results; Hobby $16 / 5,000 credits, Standard $83 / 100k, Growth $333 / 500k; /search limits 100 / 500 / 5,000 rpm by plan | ~1.3 s (AIMultiple) | Cloud-only "fire-engine"/Alexandria index (not in self-host) | Yes, hosted `https://mcp.firecrawl.dev/v2/mcp` (keyless free tier: scrape, search, parse) or local `firecrawl-mcp` with FIRECRAWL_API_URL for self-host | https://www.firecrawl.dev/pricing , https://github.com/firecrawl/firecrawl-mcp-server |
| Jina (Reader / s.jina.ai / DeepSearch) | r.jina.ai: 20 RPM keyless, 500 RPM with free key; s.jina.ai: blocked keyless, 100 RPM with free key; 10M free tokens per new key | Token-based, $0.05/M tokens Standard, $0.045/M Premium (secondary); each search request costs >= 10,000 tokens, so floor ~ $0.5/1k, real cost higher because results include page content (my estimate) | not published | Reader + search wrapper | Yes, remote `https://mcp.jina.ai/v1` (Bearer optional; search tools require key). Elastic completed Jina acquisition 2025-10-09, APIs continue | https://jina.ai/reader/ , https://github.com/jina-ai/MCP , https://www.businesswire.com/news/home/20251009619654/en |
| Kagi Search API | Pay-per-use, prepaid credit, spend cap, open to all account holders, no invite | UNVERIFIED. Docs point to kagi.com/api/pricing (not fetched). Third-party tracker says $2.50/1k (Aug 2026) but earlier snapshot $15-25/1k | not published | Kagi index + partners | Yes, hosted `https://mcp.kagi.com/mcp` (Bearer key, no OAuth yet) | https://help.kagi.com/kagi/api/overview.html , https://github.com/kagisearch/kagimcp , https://costbench.com/software/ai-search-apis/kagi-search-api/ |
| Google Programmable Search / Custom Search JSON API | 100 queries/day (existing customers only) | $5/1k up to 10k/day | n/a | Google | n/a | Closed to new customers; existing customers must migrate by 2027-01-01. https://developers.google.com/custom-search/v1/overview |
| Bing Search API | n/a | Retired 2025-08-11. Replacement "Grounding with Bing Search" in Azure AI Agents (~$35/1k per secondary source, returns agent-consumed results, not raw SERP) | n/a | Bing | n/a | https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement , https://ppc.land/microsoft-ends-bing-search-apis-on-august-11-alternative-costs-40-483-more/ |
| Marginalia Search API | Free non-commercial key by email; shared key `public` often rate-limited | free | n/a | Small-web index, not general | Community MCP only | https://about.marginalia-search.com/article/api |
| Mwmbl API | Free, no key (`api.mwmbl.org`) | free | n/a | Community index, small | none | https://github.com/searxng/searxng (engine `mwmbl.py`); empirical test below |

### A2. Quality evidence

Independent:

| Evidence | What it shows | Source |
|---|---|---|
| Artificial Analysis Search Index, leaderboard data Sep 28, 2026 (methodology: three benchmarks, 1,700 tasks: DeepSearchQA 900 + BrowseComp-subset 200 + AA-Omniscience 600; fixed agent GPT-5.6 Luna, max_results=10, 25 runs per task) | Index scores: Perplexity Search (medium) 80, Perplexity (high) 79, Octen (highlights) 77, Parallel Advanced 75, Brave LLM Context 75, OpenAI Web Search (medium) 74, You.com (highlights) 74, Exa Auto 74, Parallel Basic 73, Firecrawl Search 73, TinyFish Search 71. Baseline without search: 33. Tavily and Keenable were tested in the Aug 18 run but are not in the public table I could read. "Search cost" columns there are per 1,000 benchmark TASKS (many searches each), not per 1k searches: Perplexity $62.30, Brave $61.96, Exa $65.57, Parallel Adv $47.93, Firecrawl $30.48, Octen $9.07, TinyFish $0. Time/task: Octen 15.9 s, You 19.5 s, Brave 22.7 s, Perplexity 27.5 s, Exa 31.8 s, Parallel Adv 41.4 s, TinyFish 58.2 s, Firecrawl 61.4 s. | https://artificialanalysis.ai/agents/search-api , https://artificialanalysis.ai/methodology/search-api , https://the-decoder.com/new-benchmark-ranks-search-apis-for-ai-agents-on-quality-cost-and-speed/ (Aug 18 run: Parallel Adv 75, Exa 74, Firecrawl 73), https://select.keenable.ai/r/best-search-interfaces-for-ai-agents-2026/MMBoAy2mLxybLFvQBvxuKA |
| AIMultiple agentic search benchmark (100 real AI/LLM queries, 6 categories, ~4,000 results, GPT-5.2 judge). Page header says Dec 2024-Jan 2025, which conflicts with a GPT-5.2 judge, so the date is UNVERIFIED | Agent Score: Brave 14.89, Firecrawl 14.58, Exa 14.39, Parallel Pro 14.21, Tavily 13.67, Parallel Base 13.50, Perplexity (11+ s latency, likely Sonar) 12.96, SerpAPI 12.28. Authors warn top cluster may be random variation. Latency: Brave 669 ms, Tavily 998 ms, Exa ~1.2 s, Firecrawl 1.3 s, SerpAPI 2.4 s. | https://aimultiple.com/agentic-search |
| Openbenchmarks fastest-search-API boards (Sep 2026), as cited by Parallel | Parallel Turbo 348 ms factual, Exa Instant ~398 ms, Brave 601-630 ms mean latency | https://openbenchmarks.com/web-search/fastest-search-api (cited in https://parallel.ai/articles/most-powerful-search-api-for-ai.md ; I did not open the board itself) |
| Ritza web API benchmark (848 real URLs), as summarized by Keenable | Tavily 82.1% coverage (winner) | https://select.keenable.ai/r/ai-web-search-api-benchmarks/OaFKKMHeqBfx3jQKy9nI-w (aggregator, not primary) |
| SearXNG empirical test from a single residential IP, Jul 22, 2026 (author sells a competing SERP API) | Of Google/DDG/Brave/Startpage only DDG worked; "DuckDuckGo proxy" | https://apiserpent.com/blog/searxng-self-hosted-serp-api-tested |

Vendor-authored (treat as marketing):

| Evidence | What it claims | Source |
|---|---|---|
| Parallel BrowseComp, 50-question sample, Sep 9, 2026 | Frontier tier: Parallel Adv 74%, Perplexity ~74%, Exa Auto 70%, Tavily 66%. Low-cost tier: Parallel Fast 44%, Exa 36%, Parallel Turbo 32%, Tavily 32%. Earlier July run (Brave 38.3%/430 ms, Exa Instant 33.7%, SerpAPI 23.3%, Tavily Ultra Fast 19.3%, Parallel Turbo 51%) uses different agents; numbers in two snippets disagreed so treat July figures as UNVERIFIED | https://parallel.ai/articles/most-powerful-search-api-for-ai.md |
| Exa evals | SimpleQA Exa 93 vs Parallel 92; WebWalker Exa 81 vs Parallel 54; FRAMES 69 vs 50; Exa Instant 178 ms (us-west-1, Feb 11, 2026) | https://exa.ai/docs/reference/evaluating-exa-search , https://exa.ai/versus/parallel |
| Tavily benchmark post (Apr 27, 2026) | Tavily leads SealQA hard 55.7% and SimpleQA 97.6% (per aggregator); post body not retrievable | https://www.tavily.com/blog/exa-vs-parallel-benchmarking-retrieval-apis-for-ai-agents-in-2026 (via https://www.plushcap.com/content/tavily/blog/tavily-exa-vs-parallel-benchmarking-retrieval-apis-for-ai-agents-in-2026 ) |
| Brave AI Grounding | SimpleQA F1 94.1% (SOTA claim, Brave). Brave's own 1,500-query answer test (Jun 2026, Claude Opus 4.5 + Sonnet 4.5 judges) ranks Ask Brave 1169, Grok 1157, Google AI Mode 1000, ChatGPT 880, Perplexity 695; competitor answers scraped via Bright Data | https://brave.com/blog/ai-grounding/ , https://ppc.land/braves-5-search-api-wins-ai-answer-test-as-perplexity-finishes-last/ |
| TinyFish benchmarks (Jul 2026) | SimpleQA end-to-end 86.8% (tied Parallel), Exa 83.6, Tavily 80.8, Firecrawl 80.0; p50 556 ms vs Exa 811 ms | https://www.tinyfish.ai/benchmarks |
| Firecrawl SimpleQA | 94.7% on 4,326 questions | via https://select.keenable.ai/r/ai-web-search-api-benchmarks/OaFKKMHeqBfx3jQKy9nI-w |

Takeaways: no universal winner; the independent tier 71-80 is tightly clustered (spread of 9 points between free TinyFish and top Perplexity). For price/quality the independent data supports Perplexity Search, Brave LLM Context, Parallel, Exa, TinyFish (free). Tavily is the weakest on vendor BrowseComp numbers and the most expensive per request among the mainstream options ($8/1k).

### A3. Monthly cost estimate (search calls only)

| Option | 100/day (3,000/mo) | 300/day (9,000/mo) | Notes |
|---|---|---|---|
| TinyFish Search | $0 | $0 | 500/hr cap = 12k/day max; free policy could change (no expiry stated) |
| Parallel Fast/Turbo ($1/1k, $5 monthly credit) | $0 | ~$4 | Free credit only covers $1/1k tiers; Basic/Advanced at $5/1k = $10 (3,000, after $5 credit) / $40 |
| Brave Search or LLM Context ($5/1k, $5 credit) | $10 | $40 | credit requires attribution per AlternativeTo |
| Perplexity Search API ($5/1k) | $15 | $45 | no free tier found |
| Perplexity Fast Search ($1/1k) | $3 | $9 | lower quality tier |
| Exa Instant ($4/1k, $10 monthly credit) | $2 | $26 | Fast/Auto $7/1k: $11 / $53; contents extra |
| Tavily PAYG ($8/1k, 1,000 free) | $16 | $64 | $30 plan = 4,000 credits only |
| You.com ($5/1k, $100 one-time credit) | $15 | $45 | one-time credit lasts ~6.7 / ~2.2 months |
| Linkup ($0.005) | $15 | $45 | 4,000 free queries one-time |
| Octen ($1/1k promo, $5 credit) | ~$0 | ~$4 | promo price likely temporary (list $5) |
| Serper ($1/1k) | ~$3 | ~$9 | snippets only; credits expire in 6 months |
| DataForSEO Live ($2/1k) / queue ($0.6/1k) | $6 / $1.8 | $18 / $5.4 | SERP only |
| SerpApi | $75 | $150 | |
| Firecrawl cloud (2 credits/search) | $83 (Standard) | $83 | 6,000 / 18,000 credits |
| Perplexity Sonar low-ctx (my est. ~1k in + 1k out tokens) | ~$21-30 | ~$63-90 | $5-8 request fee + $2 tokens per 1k |
| Perplexity Sonar Pro med-ctx (same est.) | ~$72-84 | ~$216-252 | $10 request fee + ~$18 tokens per 1k |
| Self-hosted SearXNG | $0 | $0 | ops + reliability cost, see B |

## B. Self-hosted search

### B1. Firecrawl wiring facts (verified in local source)

- Files: ~/firecrawl/apps/api/src/config.ts (lines 357-359), search/v2/index.ts, search/v2/searxng.ts, docker-compose.yaml (lines 55-57 already forward the three vars into the api container; compose already defines `extra_hosts: host.docker.internal:host-gateway` and network `backend`, project network name `firecrawl_backend`).
- Not documented in the public self-host docs (https://docs.firecrawl.dev/contributing/self-host has no SearXNG mention); the only authority is the code. Upstream repo active: pushed 2026-10-06, AGPL-3.0, https://github.com/firecrawl/firecrawl
- Request shape sent to SearXNG: GET `{SEARXNG_ENDPOINT}/search?q=..&language=en&engines={SEARXNG_ENGINES}&categories={SEARXNG_CATEGORIES}&pageno=N&format=json[&safesearch=2]`. Reads `results[].url/title/content`. 20 results per page; pages until `limit` satisfied. No time-range, no country, no per-call content.
- Local box state: docker.sock is root:docker 660, `/etc/group` lists tomas in docker, but the current shell process lacks the group (relogin needed). `sg docker -c '...'` works. Firecrawl stack is running (api, redis, rabbitmq, nuq-postgres, foundationdb, playwright-service).
- Verified on this box: connectivity from the `firecrawl-api-1` container to a SearXNG container attached to `firecrawl_backend` with exactly Firecrawl's param shape (including empty `engines=` and `categories=`): HTTP 200, JSON results. (Temporary attach, then detached.)
- Verified on this box: current `/v2/search` returns `{"success":true,"data":{},"creditsUsed":0}` and `/v1/search` returns `warning: No search results found` because the DDG fallback is blocked (anti-bot modal).

### B2. SearXNG Docker facts

- Image `docker.io/searxng/searxng:latest` (GHCR mirror `ghcr.io/searxng/searxng`); compose = core + valkey (limiter backend); config `/etc/searxng/settings.yml`, cache `/var/cache/searxng`. Source: https://docs.searxng.org/admin/installation-docker.html , https://raw.githubusercontent.com/searxng/searxng/master/container/docker-compose.yml
- JSON must be enabled: `search.formats: [html, json]`. Source: https://docs.searxng.org/admin/settings/settings_search.html
- Engine suspension defaults: CAPTCHA 86,400 s, access denied 86,400 s, HTTP 429 3,600 s, Cloudflare CAPTCHA 1,296,000 s, Google reCAPTCHA 604,800 s. Same page. So one burst benches an engine for an hour to a day.
- Repo: https://github.com/searxng/searxng (AGPL-3.0, 38k stars, pushed 2026-10-04).
- Limiter/valkey is only needed for public instances; for a private sidecar set `server.limiter: false` (what I used).

### B3. Reliability evidence

| Source | Finding |
|---|---|
| Docs defaults above | Engines suspend for hours to days on 429/CAPTCHA |
| https://apiserpent.com/blog/searxng-self-hosted-serp-api-tested (competitor, Jul 2026) | single residential IP: DDG OK, Google 0 results, Brave suspended, Startpage CAPTCHA |
| https://www.ssdnodes.com/learn/browser-search-skill-searxng-agents , https://you.com/resources/searxng-alternatives (competitor) | SearXNG "is not a stable programmatic search API for AI systems" (vendor-adjacent) |
| https://forum.cloudron.io/topic/9286/google-suspended-too-many-requests/ | users report Google engine suspended with too-many-requests |
| My own test below | Matches: Brave 429 immediately, DDG timeouts, Google blocked, Qwant CAPTCHA |

### B4. My empirical test (box residential IP, 2026-10-06 ~22:00-23:00 EEST, SearXNG latest, limiter off, default engines)

- Default engine set (enabled general): wikipedia, duckduckgo, google cse, brave (+ translation engines). `google cse` is a default engine that scrapes Google's CSE JSONP endpoint using a hard-coded third-party publisher token (`CX = "partner-pub-8993703457585266:4862972284"  # blackle.com`) in searx/engines/google_cse.py. It is a free-ride on someone else's Google CSE; it can disappear any time. Whether it survives Google's 2027-01-01 Custom Search shutdown is UNVERIFIED (the shutdown notice covers the JSON API and "search the entire web" PSEs, https://developers.google.com/custom-search/v1/overview ).
- Run 1, 40 distinct queries, 3 s apart: 40/40 returned 20 results, all from google cse; zero results from any other engine. Brave: "Suspended: too many requests" from the first query; DuckDuckGo: timeout on every query (the 3.0 s p50 latency is just the DDG timeout; with only google cse it answers in 0.2-0.8 s).
- Run 2, each engine forced individually (`engines=<name>`), 2 queries each: google "access denied"; qwant CAPTCHA; brave 429; duckduckgo timeout; searchmysite access denied; clean results from google cse (20/20), yandex (15/15), yep (20/20 in the first test, 0 later), bing (10 then 0), yahoo (0 then 7, parsing errors), mwmbl (2 and 47, low quality), arxiv/github/stackoverflow vertical engines. Startpage, mojeek, marginalia, stract, presearch, reddit showed 429/timeouts alongside default-set fallbacks (inconclusive).
- Quality of google cse results: relevant, current (snippets carry dates e.g. 2026-08-04); yandex returned relevant English results for a tech query.
- Run 3, load test: 250 random 2-4-word queries at ~1 q/s with `engines=google cse,yandex`. Google CSE returned "too many requests" and got suspended (3,600 s) by roughly the 130th-140th cumulative query of the session (about 20 minutes in); all subsequent queries were served by yandex alone. See section B5 for final numbers.
- Container-to-container check from `firecrawl-api-1`: OK (B1).

### B5. Final load-test numbers

250 random queries at ~1 q/s with `engines=google cse,yandex`: 250/250 returned results, 0 empty, p50 0.42 s, p90 0.54 s. The `google cse` engine was healthy for the first ~25 load-test queries, then returned 429 "too many requests" and was suspended by SearXNG for the rest of the run (222 suspended-skip events); Yandex alone served the remaining ~225 queries with no failures. Cumulative queries on the box IP before the Google trip: roughly 130-140 in about 25 minutes. Takeaway: Yandex was the most reliable engine from this IP; Google CSE is a burst-limited bonus.

The throwaway container (`searxng-test`) was removed afterwards and the Firecrawl stack was left untouched; only the cached image `searxng/searxng:latest` (264 MB) remains on the box. Scripts: /tmp/searxng-bench/*.py, logs bench.log/load.log.

### B5b. Exact wiring steps (not applied; box is unchanged)

1. Config dir: `mkdir -p ~/firecrawl/searxng && cd ~/firecrawl/searxng` then write `settings.yml`:
```
use_default_settings: true
server:
  secret_key: "<openssl rand -hex 32>"
  limiter: false
  image_proxy: false
search:
  formats:
    - html
    - json
outgoing:
  request_timeout: 5.0
engines:
  - name: duckduckgo
    disabled: true
  - name: brave
    disabled: true
  - name: yandex
    disabled: false
```
   then `chmod -R a+rX ~/firecrawl/searxng` (container runs as a non-root uid).
2. Add the sidecar to `~/firecrawl/docker-compose.override.yaml` (file already exists with restart policies; merge under `services:`):
```
  searxng:
    image: docker.io/searxng/searxng:latest
    restart: unless-stopped
    networks: [backend]
    volumes:
      - ./searxng:/etc/searxng
```
   No published port needed. Do not use a host-published 127.0.0.1 port plus `host.docker.internal`: host-gateway maps to the docker bridge IP, which cannot reach a service bound to loopback only.
3. `~/firecrawl/.env`: set
```
SEARXNG_ENDPOINT=http://searxng:8080
SEARXNG_ENGINES=google cse,yandex
SEARXNG_CATEGORIES=
```
   (docker-compose.yaml already forwards all three into the api container). Optionally also add `google cse` removal later if it gets blocked.
4. Apply: `sg docker -c 'cd ~/firecrawl && docker compose up -d searxng && docker compose up -d --force-recreate api'` (the shell lacks the docker group until re-login, hence `sg docker`).
5. Verify: `curl -s localhost:3002/v2/search -H 'Content-Type: application/json' -d '{"query":"firecrawl self host searxng","limit":5}'` must show `data.web` with 5 entries; also `sg docker -c 'docker logs firecrawl-api-1 --tail 50' | grep -i searxng` should show "Using searxng search". An empty `data: {}` with success:true = FAILURE (falls through to blocked DDG).
6. Optional MCP use of the same instance: `claude mcp add searxng -e SEARXNG_URL=http://127.0.0.1:8888 -- npx -y mcp-searxng` requires publishing `127.0.0.1:8888:8080` on the sidecar.

### B6. Other self-hosted indexes

| Option | Verdict | Source |
|---|---|---|
| YaCy | P2P crawler/index, 4k stars, active (pushed 2026-09-23); web-wide quality poor, useful for intranet/niche crawls; not a general web search backend | https://github.com/yacy/yacy_search_server , https://glukhov.org/post/2025/06/yacy-search-engine/ |
| Marginalia | Small-web/text-heavy index, free non-commercial API key by email, `public` key rate-limited; SearXNG has `marginalia` engine; good for blogs/forums, bad for commercial queries | https://about.marginalia-search.com/article/api |
| Mwmbl | Community non-profit index, keyless API, tiny coverage (my test: 2 and 47 results, noisy) | https://github.com/searxng/searxng engine mwmbl.py ; empirical |

### B7. Verdict: is SearXNG + Firecrawl a viable free search layer?

Conditionally yes as a free, zero-key fallback and to make the existing Firecrawl `/search` and `firecrawl-search` skill return something at all. No as the primary: from this one residential IP it degrades to one or two live engines (Google-CSE hack + Yandex), the Google CSE engine tripped 429 under ~1 q/s bursts, Brave/DDG/Qwant/Google are blocked, there is no recency/country filter through Firecrawl's wrapper, and the Google CSE engine depends on a third-party token. Rate-limit client side (<= 20 queries/min, <= ~100/hr), set `SEARXNG_ENGINES=google cse,yandex`, and treat empty results as a failure and fall through to TinyFish/Brave/Parallel. Residential/rotating proxy would raise reliability but costs money and defeats "free".

## C. MCP servers for research in Claude Code

| Server | Hosted remote vs local | Auth | Free path | Tools | Repo / stars / last push (GitHub API, 2026-10-06) |
|---|---|---|---|---|---|
| Exa MCP | Hosted `https://mcp.exa.ai/mcp` (streamable-http); also npm `exa-mcp-server`; Claude plugin `exa@claude-plugins-official` | none (rate-limited), OAuth (`?login`), or `x-api-key` / Bearer / `?exaApiKey=` | keyless free | web_search_exa, web_fetch_exa; opt-in web_search_advanced_exa, agent_run | exa-labs/exa-mcp-server, 5.1k stars, MIT, pushed 2026-10-06 |
| Tavily MCP | Hosted `https://mcp.tavily.com/mcp` (API key in URL/header or OAuth); local npx also | key or OAuth; keyless header `X-Tavily-Access-Mode: keyless` per Parallel's article (UNVERIFIED independently) | 1,000 credits/mo | search, extract, map, crawl | tavily-ai/tavily-mcp, 2.4k, MIT, 2026-10-05 |
| Brave MCP | Local (npx / docker), stdio default, optional local HTTP. No hosted | BRAVE_API_KEY | $5 credit/mo | brave_web_search, local, video, image, news, summarizer, place, llm_context | brave/brave-search-mcp-server, 1.5k, MIT, 2026-10-05 |
| Perplexity MCP (official) | Hosted `https://api.perplexity.ai/mcp` (Bearer key) or local `npx @perplexity-ai/mcp-server`; self-host HTTP mode available | PERPLEXITY_API_KEY | none | perplexity_search, perplexity_ask, perplexity_research, perplexity_reason | perplexityai/modelcontextprotocol, 2.6k, MIT, 2026-09-25 |
| Firecrawl MCP | Hosted `https://mcp.firecrawl.dev/v2/mcp` (keyless free tier for scrape/search/parse; OAuth `/v2/mcp-oauth`; `/v2/mcp-search` search-only); local npx with `FIRECRAWL_API_URL` for self-host | key / OAuth / keyless | keyless + 1,000 credits | 27 tools (scrape, search, crawl, map, interact, monitor...) | firecrawl/firecrawl-mcp-server, 7.6k, MIT, 2026-10-06 |
| Jina MCP | Hosted `https://mcp.jina.ai/v1` | Bearer optional; search_web/search_arxiv need key | free key = 10M tokens | read_url, search_web, search_arxiv, search_ssrn, search_images, embeddings/rerank | jina-ai/MCP, 873, Apache-2.0, 2026-09-18 |
| Parallel Search MCP | Hosted `https://search.parallel.ai/mcp` | none, or Bearer / OAuth (`/mcp-oauth`) | keyless (Fast mode, lower limits unpublished) | web_search, web_fetch; excerpts capped ~25k chars per call | docs https://docs.parallel.ai/integrations/mcp/search-mcp ; CLI repo parallel-web/parallel-web-tools (50 stars) |
| TinyFish MCP | Hosted `https://agent.tinyfish.ai/mcp`; CLI `tinyfish config-claude` | API key (free) or plugin OAuth | free Search+Fetch | tinyfish_search, tinyfish_fetch (+agent, browser metered) | https://docs.tinyfish.ai/mcp-integration/index.md ; https://github.com/tinyfish-io/tinyfish-cookbook |
| You.com MCP | Hosted `https://api.you.com/mcp` | none on `?profile=free` (100 queries/day) or API key | 100/day keyless | search (+contents, research, finance with key) | https://you.com/apis |
| Linkup MCP | Hosted `https://mcp.linkup.so/mcp`; local stdio | Bearer / ?apiKey= | 4,000 queries | search, fetch | LinkupPlatform/linkup-mcp-server, 29 stars, MIT |
| Kagi MCP | Hosted `https://mcp.kagi.com/mcp`; local uvx; self-host | Bearer API key (no OAuth) | none | kagi_search_fetch (FastGPT/summarizer tools removed for now) | kagisearch/kagimcp, 533, MIT, 2026-07-07 |
| Keenable MCP | Hosted `https://api.keenable.ai/mcp` | none (shared tier) or X-API-Key | keyless w/ hourly cap | search, fetch | https://docs.keenable.ai/mcp-server.md |
| mcp-searxng | Local (npx `mcp-searxng`, stdio or HTTP) with `SEARXNG_URL`; does not install SearXNG | none | free | searxng_web_search, url read | ihor-sokoliuk/mcp-searxng, 1.3k, MIT, 2026-10-06 |
| Fetch MCP (reference) | Local (`uvx mcp-server-fetch`), listed under active reference servers | none | free | fetch URL -> markdown | modelcontextprotocol/servers (src/fetch), 91k stars. Brave reference server is archived, replaced by the official one |
| Apify / scrapling / gbrain etc. | Already configured on this box (`~/.claude.json`: gbrain, android, apify, scrapling, mobile-mcp, brain, bigquery). android and mobile-mcp currently fail to connect | | | | local config |

Sources for the table: each repo README (raw.githubusercontent.com/<repo>/main/README.md) and metadata via api.github.com/repos/<repo>; hosted URLs as listed in the READMEs/docs: https://github.com/exa-labs/exa-mcp-server , https://github.com/tavily-ai/tavily-mcp , https://github.com/brave/brave-search-mcp-server , https://github.com/perplexityai/modelcontextprotocol , https://github.com/firecrawl/firecrawl-mcp-server , https://github.com/jina-ai/MCP , https://github.com/LinkupPlatform/linkup-mcp-server , https://github.com/kagisearch/kagimcp , https://github.com/ihor-sokoliuk/mcp-searxng , https://github.com/modelcontextprotocol/servers , https://parallel.ai/articles/best-free-web-search-mcp.md (keyless list, authored by Parallel).

Operational note for headless `claude -p` crons: hosted HTTP MCPs with a static header (`claude mcp add --transport http <name> <url> --header "Authorization: Bearer ..."`) need no browser, no cookie refresh and no Xvfb, which is the specific failure mode of the current Perplexity cookie MCP. OAuth-only flows (Exa `?login`, Tavily OAuth) are a poor fit for unattended boxes; prefer API-key headers.

## D. Recommendation (cheapest robust combo for 50-300 agent searches/day)

Layered, fail-down:

1. Default: TinyFish Search + Fetch via hosted MCP, free, $0. Independent AA score 71. Keep traffic under 30/min.
2. Quality / independent-index fallback: Brave Search API (LLM Context endpoint, same $5/1k key) or Parallel Fast ($5 monthly credit = 5,000 searches, then $1/1k). Brave: $10 (100/day) / $40 (300/day). Parallel: $0 / ~$4.
3. Perplexity-grade synthesis and top independent quality (AA 80): official Perplexity Search API ($5/1k) or Sonar for cited answers, replacing the cookie-hijack MCP. Use selectively (e.g. 20/day): ~$3/mo.
4. Local free fallback and Firecrawl `/search`: SearXNG sidecar (google cse + yandex only), $0, rate-limited.
5. Keep Claude's built-in WebSearch and the existing fetchers (Crawl4AI, scrapling, Camofox, Apify, local Firecrawl) for retrieval/extraction; the search APIs above only replace discovery.

Expected spend: ~$0 at 100/day (all on TinyFish plus Parallel credit), ~$0-10 at 300/day with Parallel Fast overflow; worst case if you pay for a single quality vendor with no free tiers: $15 / $45 (Perplexity or You.com), $10 / $40 (Brave).

## E. UNVERIFIED / gaps

- Brave's $5 credit attribution requirement (only AlternativeTo says it; Brave page did not mention it).
- Perplexity Pro $5/month API credit (third-party only).
- Kagi Search API price per 1k (docs defer to kagi.com/api/pricing; trackers conflict).
- Keenable pricing and hourly cap; Octen promo permanence; Valyu search MCP URL; Serper tier table from primary page (JS-rendered; consistent only via HTML price points and third parties).
- Perplexity Search API latency per call (not published on pages read).
- Whether Parallel's $5 free monthly credit applies beyond Turbo/Fast.
- AIMultiple benchmark date (page text conflicts with its GPT-5.2 judge).
- Tavily keyless header `X-Tavily-Access-Mode: keyless` (only from Parallel's article).
- Whether blackle's CSE token (used by SearXNG `google cse`) survives the 2027-01-01 Google shutdown.
- Index freshness: no vendor publishes a measured freshness number; Brave/Exa/Parallel/Octen claim real-time own indexes, SERP APIs (Serper, SerpApi, DataForSEO) are live Google and therefore freshest by construction.
