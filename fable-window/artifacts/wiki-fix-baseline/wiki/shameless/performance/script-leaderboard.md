# Script Leaderboard

**Summary**: Ranked leaderboard of 14 top-spend Shameless Snacks scripts with ROAS, spend, and format data, plus structural patterns, compliance translations, and flavor descriptors.

**Sources**: proven_scripts.md

**Last updated**: 2026-06-02 (added ROAS-Truth refresh from BigQuery, last 60d Meta paid). Prior: 2026-05-06 Motion Creative Benchmarks 2026.

---

14 top-spend scripts with ROAS, spend, and format data — plus the structural patterns, hook shortlist, and compliance translations. Source: `raw/templates/proven_scripts.md`.

This is a **reference library of what has worked so far** — not a required formula. Use for pattern extraction, hook borrowing, component reuse. See [[shameless-creative-strategy]] for the broader strategic frame and [[fiber-first-positioning]] for the updated primary angle direction.

## Leaderboard

| # | Script | ROAS | Spend | Format |
|---|---|---|---|---|
| 1 | Genetics | 1.31 | $116k | Scripted VSL |
| 2 | Dad Bod | 1.19 | $38k | Scripted VSL |
| 3 | 5 Reasons (Candy Carnival) | 0.90 | $6k | Product launch |
| 4 | Advertorial — Let Er Rip v1 | 0.89 | $42k | Long-form narrative |
| 5 | QVC | 0.88 | $69k | Live shopping excerpt |
| 6 | Travel Snack (UGC) | 0.85 | $46k | UGC conversational |
| 7 | Gummies Lover | 0.83 | $7k | UGC product review |
| 8 | Product Components | 0.81 | $4k | UGC product review |
| 9 | Fat Dad Bod | 0.80 | $9k | Scripted VSL (hook swap of #2) |
| 10 | Save Money | 0.77 | $3k | Voiceover product intro |
| 11 | Snack Smart (UGC) | 0.76 | $107k | UGC product intro |
| 12 | Advertorial — Let Er Rip v2 | 0.73 | $17k | Long-form narrative |
| 13 | 22 Teaspoons of Sugar | 0.71 | $10k | Founder-led brand story |
| 14 | Sweet Tooth Lovers | 0.65 | $5k | Scripted VSL |

## ROAS-Truth refresh: 2026-06-02 (BigQuery, last 60d Meta paid)

Ground-truth from `ejam-dwh.production.creative_dashboard` (brand=SHA, last 60 days, spend floors to cut small-sample noise). This is the dollar reality behind the leaderboard above. Use it to weight which patterns to borrow.

**By angle (portfolio level, spend ≥ $2k):**

| Angle (AI-tagged) | Spend | ROAS |
|---|---|---|
| Direct Offer | $57k | 1.04 |
| Scarcity & Urgency | $118k | 1.01 |
| Unique Selling Proposition | $71k | 1.00 |
| Simple Product | $181k | 0.85 |
| Problem-Solution | $121k | 0.62 |
| Curiosity-Driven Hook | $35k | 0.50 |
| Customer Testimonial | $16k | 0.52 |
| Comparison | $10k | 0.52 |

**Read:** offer-led, urgency-led, and USP creative are the only angles clearing ~1.0 ROAS at scale. Problem-led, curiosity-led, testimonial, and comparison are all losing money (0.50 to 0.62) despite heavy spend. Static images hold most of the top-ROAS slots.

**Top individual performers (spend ≥ $1.5k):** SH-2815 (Scarcity, 1.35 at $14.5k), SH-13396 (1.29 at $14.5k, video), SH-13673 (Scarcity, 1.08 at $20k), SH-11295 (USP, 1.08 at $57k), SH-3028 (Direct Offer, 1.13 at $13k).

> Caveat: "angle" here is BigQuery's generic DR-angle classifier, a different axis from the Shameless hook patterns in [[top-performer-patterns-observed]]. Read it as a spend-weighted profitability signal, not a hook taxonomy.

## Hook Shortlist

Script-level hooks with ROAS live in [[hook-framework#script-level-hook-winners|hook-framework]] — canonical inventory.

## Winning Structure — Constant Across Top Scripts

```
1. Personal / emotional / stat HOOK
2. Problem or tension expansion
3. Product reveal (often in-narrative, not as announcement)
4. Stat delivery (70 cal / 3g sugar / 3g net carbs / 26g fiber)
5. Mechanism or differentiator (fiber, dietary compatibility)
6. Social proof (reviews, friend recommendation, Amazon rank)
7. CTA (URL + tap/click)
```

Missing 3, 4, or 7 correlates with lower ROAS in this set.

## Format Observations

- **Scripted VSLs** dominate top spend (Genetics, Dad Bod, Advertorials)
- **UGC short-form** dominates retargeting efficiency at scale (Snack Smart at $107k spend, 0.76 ROAS)
- **Dialogue UGC** (Travel Snack) strong for prospecting — 0.85 ROAS at $46k
- **Long-form advertorials** have highest compliance risk — nearly every one contains hard-stop phrases
- **Brand-story** (22 Teaspoons, 0.71) is the cleanest compliance-wise, lowest ceiling

## 2026 Industry Baseline — DTC Food/Beverage

**Source:** MHI Growth Engine internal data across DTC food & beverage campaigns, 2025-2026 (as published in `Best DTC Ad Examples for Food and Beverage Brands`, scraped 2026-05-05). Use these as outside benchmarks for evaluating Shameless format-level performance, not as targets per se.

| Format | Hook rate | CTR | CPA vs baseline |
|---|---|---|---|
| **Problem agitation hook** | **64%** | 1.6% | **−20%** |
| **Founder/user testimonial** (direct-to-camera) | **62%** | **1.7%** | **−22%** |
| Before/after demonstration | 58% | 1.5% | −18% |
| Social proof lead | 52% | 1.4% | −12% |
| Ingredient/process education | 48% | 1.3% | −8% |
| Polished brand production | 44% | 1.1% | baseline |

**What this confirms (industry-wide):**

- Problem agitation and founder testimonial are the two highest-performing cold-acquisition formats for DTC food in 2026.
- Polished production *underperforms* iPhone-shot UGC by 18-22% on CPA. This holds across categories.
- Social proof leads work for retargeting but are mediocre for cold prospecting.
- Ingredient education has the lowest hook rate but the longest video tolerance — best on YouTube and Meta Feed, weak on Reels.

**Format duration sweet spots:**

- Founder testimonial: 15-30s
- Before/after: 20-35s (compliance-restricted for Shameless — see [[compliance-guardrails]])
- Problem agitation: 25-40s
- Ingredient education: 30-60s (Meta Feed / YouTube only)

**Reading this against the Shameless leaderboard above:**

- Genetics (1.31 ROAS, scripted VSL) sits at the long end of the founder testimonial duration range
- Travel Snack (UGC, 0.85) and Snack Smart (UGC, 0.76) are problem-agitation-adjacent but underperform Genetics — the founder voice is doing more lifting than UGC voice in the Shameless data set
- The leaderboard's two highest performers (Genetics, Dad Bod) are both founder/personal-stakes formats, consistent with the 2026 industry pattern that founder testimonial > polished brand
- 22 Teaspoons (founder-led brand story, 0.71) underperforms Genetics — the *brand-story* framing is weaker than the *personal-stakes* framing inside founder format

**Operational rule of thumb (industry consensus):** maintain **3-5 active formats simultaneously** rather than scaling a single winner until it fatigues. **5-8 new variants per month** minimum for active DTC brands. See [[shameless-creative-testing-framework]] for the Shameless application.

### Motion Creative Benchmarks 2026 — testing volume, hit rate, portfolio breakdown

**Source:** Motion's analysis of $1.29B in Meta spend across 578,750 creatives and 6,015 advertisers (Sep 2025 – Jan 2026, BFCM-inclusive). Full ingest at [[shameless-motion-creative-benchmarks-2026]].

**Definitions Motion uses (worth standardizing on internally):**
- **Winner** = spend ≥10× account median AND ≥$500
- **Mid-range** = ≥28 days with spend, not a winner
- **Loser** = turned off before 28 days

**Testing volume + hit rate by spend tier (CH-003):**

| Spend tier | Avg creatives/week | Avg hit rate |
|---|---|---|
| Micro (<$10K) | 2.8 | 4.0% |
| Small ($10K–$50K) | 4.1 | 6.4% |
| Medium ($50K–$200K) | 6.6 | 8.1% |
| Large ($200K–$1M) | 11.2 | 8.6% |
| Enterprise ($1M+) | 18.8 | 8.8% |

**Top 25% gap (CH-008) — the structural insight:**

| Tier | All vol/wk | **Top 25% vol/wk** | All winners/mo | **Top 25% winners/mo** |
|---|---|---|---|---|
| Medium ($50-200K) | 6.6 | **15.9** | 0.7 | **2.0** |
| Large ($200K-1M) | 11.2 | **31.1** | 1.7 | **5.9** |
| Enterprise ($1M+) | 18.8 | **54.6** | 3.9 | **10.4** |

Top-quartile accounts ship 2-3× the volume of tier-average and produce 2-3× the winners/month. **Implication for Shameless** (Medium-to-Large spend tier): top-25% positioning requires **15-30 new creatives/week**, not the 5-8 per month industry minimum.

**Portfolio breakdown — % of creatives (CH-005):** ~50-53% losers, ~38-46% mid-range, ~4-8% winners across tiers. Mid-range ads are not failed tests — they're portfolio ballast.

**Spend allocation (CH-006):** Winners absorb 23% of Micro spend → 64% of Enterprise spend. Mid-range carries proportionally more spend in smaller accounts (45.6% Micro → 22.4% Enterprise) because they have less capacity to ride pure winners.

**DTC food vertical (CH-007):** Health & Wellness Enterprise advertisers ship **46 creatives/week** (highest of any vertical, 2.4× cross-vertical Enterprise average). For Shameless's category, this is the cadence top-quartile competitors operate at.

**The hit rate gotcha:** Account A (50 launches, 5 winners, 10% hit rate) outperforms Account B (5 launches, 1 winner, 20% hit rate) by every meaningful measure. High hit rates can signal under-testing more than they signal strong judgment. Optimize for volume × hit rate, not hit rate alone.

**Top hooks confirmed in CH-011 (Motion's hook-and-headline leaderboard, hit rate band 6-11%):** Confession, Bold claim, Curiosity, FOMO, Urgency, Contrarian, Reverse psychology, Shocking statement. The Confession hook ranks top-tier on **both** hit rate and spend use ratio — directly supports the [[founder-script-framework]] confession-first thesis and the Giancarlo confession-first ad lane.



## Compliance Translation — Historical Winners → Updated Rules

Under the 2026-04-15 [[compliance-guardrails|compliance policy update]], much weight-loss language is now permitted. Remaining translations:

| Historical phrase | Status (2026-04-15) | Notes |
|---|---|---|
| "Lose weight" / "shedding pounds" / "watch my weight" | Permitted | Narrative context, not clinical promise |
| "Losing weight feels impossible" | Permitted | Problem statement |
| "Finally seeing results" / "jeans fitting better" | Permitted | Personal outcome framing |
| "Natural appetite suppressant" | Permitted | Must pair with fiber as mechanism |
| "Kills cravings" / "fights hunger" | Permitted | Craving-control, route through fiber |
| "Scale going up" | Copy OK, visuals still blocked | No scale imagery |
| Before/after transformation imagery | Still Meta-blocked | Visual policy unchanged |
| "Manage my blood sugar" (Gummies Lover) | Still hard stop | Diabetic safety claim |
| "Regulates blood sugar" / "lowers cholesterol" | Still hard stop | Drug/disease framing |
| "Helps with food noise" | Allowed (lifestyle term) | Keep grounded in fiber, not drug framing |
| "Ozempic alternative" / "better than Ozempic" | Still hard stop | Drug-replacement positioning |
| "Ozempic" / "GLP-1" as audience context | Monitor | Personal experience framing only, no drug name in brand voice |
| "3 to 8 grams of net carbs" (Snack Smart) | Factual error | Current spec is 3g — fix before reuse |

**Net effect:** Genetics and Dad Bod can now run largely intact under the updated policy — the fiber mechanism was already there; the framing is permitted. Only hard-stop phrase swaps needed.

## Flavor Descriptor Library (Reusable, Compliant)

From Candy Carnival script — safe copy elements for new flavor launches:

| Flavor | Descriptor |
|---|---|
| Sour Strawberry Splash | "Like biting into fresh summer berries" |
| Sour Mango Madness | "Tropical paradise in every bite" |
| Orange Blossom Bliss | "Sunshine sweet citrus perfection" |
| Sour Pineapple Punch | "Tangy tropical goodness" |
| So Cool Cola | "Your favorite soda, now in gummy form" |

## April 2026 Batch

Source: `raw/templates/scripts-april-2026-batch.md`. Rewritten from videographer/editor feedback — no em dashes, 6th–7th grade reading level, American English, shorter hooks, dead-weight lines cut, talent-rejectable lines removed. All scripts share canonical stats (26 g fiber, 3 g sugar, 70 cal, 9 flavors, 3,500+ 5★ reviews).

| Script | Persona / Angle | Lead ICP | Format | Notes |
|---|---|---|---|---|
| 1 — The Goodbye Letter | Anti-fiber-supplement breakup | Hannah, Maggie | UGC testimonial (female), raw edit, tossing old supplements on camera | Enemy-vocab hooks: *"I ghosted Metamucil,"* *"Dear fiber powder. It's not me. It's definitely you."* Directly executes G3 "Not Metamucil" angle. See [[creative-angles#Not Metamucil (direct comparison)]] |
| 2 — Late Night Cravings | Fiber-as-craving-control | Hannah, Linda | UGC female, raw edit | *"I stopped my late night cravings by eating candy during the day."* Executes the Craving-Control-via-Fiber (GLP-1 proxy) angle. See [[creative-angles#Craving Control via Fiber (GLP-1 proxy)]] |
| 3 — From Skeptic to Believer | Skeptic-convert + stat-shock | Hannah, Dave | Male VO, muse speed/tone | Hook: *"I ignored 3,500 five-star reviews for months."* Social-proof + skeptic pattern |
| 5 — Athletes Have in Common | Animal-athlete fiber comparison | Chris, Mike | UGC male, animal + athlete B-roll insets | Gorillas 40g, chimps 30–40g, Americans 10g. Novel comparison angle, not in prior leaderboard |
| 6 — Childhood Trauma | Anti-broccoli permission | Hannah, Sarah | Male, "horror story under a blanket" then color-flip to SS | Executes "your childhood vegetables in candy form" — novel story structure |
| 6B — Morning Routine | Morning poop / gut routine | Broad | Male VO, inside-the-bag shots | So Cool Cola spotlight + 32% subscribe-save CTA |
| 6C — Picky Friend | Taste-skeptic (friend-angle) | Hannah, Sarah | Female VO, colorful product shots | Orange Blossom Bliss / OMG Peach / Super Sour Blue Raspberry features |
| 7 — Sweet Morning Craving | Sweet-craving AM + fiber reassurance | Hannah | Female VO, website flavor shots | Sour Peach spotlight |
| 8 — Morning Fix | Constipation morning fix | Maggie, Dave | Female VO, simple shots | "20 minutes on the toilet" hook — same-category as Script 9. Subscribe pricing ($2.69) explicit |
| 9 — GLP-1 Constipation Fix | Direct GLP-1 segment (Maggie) | Maggie | Female VO, muse-style | *"I fixed my GLP-1 constipation with candy. Actual candy."* Explicit GLP-1 category term permitted. *"Like clockwork"* peer-vocab mirror. See [[glp1-dosing-companion]] for dosing-guidance context |

**Note**: Script 4 is not in the batch (numbering jumps from 3 to 5). Not a transcription error — confirmed from raw file.

**Compliance flags on this batch** (not a blocker; worth noting):

- Script 1 repeats *"93% of Americans don't get enough fiber"* — verify against canonical stat (most-cited figure is 90–95%; align across the batch).
- Script 1 claim *"26 grams of fiber... that's 93% of what you need in a day"* — do the math on daily-fiber RDA (25 g women / 38 g men) before locking. 26/28 ≈ 93% against a 28 g blended figure; safer to say "most of your daily fiber" per [[compliance-guardrails]].
- Script 9 uses "GLP-1" as a category term (permitted) and never names Ozempic/Wegovy/Mounjaro (correct). Sentence *"when you're only eating around 1,200 calories a day"* flirts with dietary-restriction claim — reviewable but likely OK as personal narrative per 2026-04-15 policy.
- None of the scripts use *"food noise"* (correct, hard-stop term).

### Borrowed DR Patterns to consider for next batch

Per [[creative-angles#Timeline-of-Effect (TUSHY DR Pattern)]] (source: competitor-research-v3-addendum-2026-04-24.md): TUSHY's clean 1–6 hrs / 12–48 hrs / 3–7 days / 2+ weeks timeline structure would slot into Script 8 (Morning Fix) or Script 9 (GLP-1) as a mid-script "here's what to expect" beat. Borrow structurally; keep "typical" / "may" hedging.

### Gemini Deep Reshoot methodology

Reference: the [[shameless-gemini-video-gem-transcribe-and-describe]] Gem transcribes + storyboards + maps to Shameless touchpoints. The action-backlog (shameless-action-backlog-2026-04-23.md) positions this as the reshoot methodology for iterating winning-but-tired scripts — transcribe the current winner via Gem, map the storyboard to the competitive-intelligence hook bank (this page + [[hook-framework#2026-04-24 Competitor-Sourced Hook Bank]]), then brief creators on hook-only swaps while keeping the body footage reusable. See [[shameless-gemini-video-gem-transcribe-and-describe]] and [[creative-intelligence-meta-ad-library]] for competitor-side reference patterns.

## Per-Script Index

Full scripts, structural takeaways, and per-script compliance flags live in the source file. This wiki page is the synthesis layer. For full text of any script, see `raw/templates/proven_scripts.md`.

## Related pages

- [[shameless-creative-strategy]]
- [[hook-framework]]
- [[ad-performance]]
- [[fiber-first-positioning]]
- [[compliance-guardrails]]
- [[shameless-video-structure]]
- [[shameless-ad-copy-patterns]]
- [[shameless-script-audit-checklist]]
- [[creative-angles]]
- [[glp1-dosing-companion]]
- [[creative-intelligence-meta-ad-library]]
- [[shameless-gemini-video-gem-transcribe-and-describe]]
