# Ad Copy Patterns — Shameless Application

**Summary**: Shameless-specific Meta static ad copy library — five proven patterns with full body copy, three-field split routing, audience-to-format mapping, comment-reply library, compliance filter, and the canonical product-stat lock. Brand-neutral framework lives in [[ad-copy-patterns]].

**Sources**: static_ad_copy.md, meta_ad_copy.md.

**Last updated**: 2026-04-15

---

## Meta Three-Field Split — Shameless Pattern

| Field | Job | Shameless Pattern |
|---|---|---|
| Primary Text | Story, benefits, proof | Benefit stack with checkmarks OR urgency letter |
| Headline | Hook or offer | Customer quote, stat, or urgency statement |
| Description | Secondary reinforcement | Guarantee, shipping, or secondary benefit |

Headline stops the scroll. Primary text converts. Description closes.

## Five Proven Static Patterns

### Pattern 1 — Stat Lead + Benefit Stack (Cold Prospecting)

```
Headline: FINAL CLEARANCE SALE!
Primary:
Looking for a candy swap? Meet Shameless Snacks —
the gummies that taste just like candy but pack:
✅ 26g of gut-loving fiber per bag
✅ Only 3g sugar & 70 calories
✅ Keto-friendly, vegan & gluten-free
✅ No crash, no guilt — just sweet satisfaction
```

Leads with the #1 shock stat (26g fiber) before offer. Aligns with [[fiber-first-positioning]].

### Pattern 2 — Problem / Solution Lead (Prospecting)

```
Headline: Shameless Snacks: Now Available
Primary:
Looking for that perfect sweet snack to satisfy a fix
without all the sugar, net carbs or calories?
Well it's now available!
✅ Lip-smacking, natural fruity flavors!
✅ 3g sugar, 3g net carbs per bag
✅ 70 calories per bag
✅ Gluten Free / Keto-friendly + Vegan
```

### Pattern 3 — Social Proof Headline + Comparison Body (Retargeting)

```
Headline: "I ❤️ These Guilt-Free Gummies!!!!"
Primary:
One bag of Shameless Snacks has 3 grams of sugar,
3g net carbs, and only 70 calories… while still
tasting exactly like traditional candy.
✅ Fewer calories
✅ Lots more dietary fiber
✅ Vegan / Way less sugar
30-Day Satisfaction Guarantee
```

> Historical versions used "8g net carbs" — current spec is **3g**. Always use 3g.

### Pattern 4 — Urgency Letter (Promo Windows Only)

```
Headline: FINAL CLEARANCE SALE!
Primary:
Time's ticking…
Don't make a dumb decision you'll regret later.
This offer's almost gone - and once it's gone, it's gone.
Limited stock, limited time. Just a killer deal you'll wish you grabbed.
Up to 46% OFF + 4 FREE GIFTS
```

Scarcity requires a real deadline.

### Pattern 5 — Benefit Trio (Mobile-First Scroll)

```
Headline: [Offer CTA]
Primary:
Feeds cravings.
Fuels your gut.
Flips candy logic on its head.
UP TO 46% OFF + $2.69 PER BAG
```

Three-line rhythm as scroll-stopper.

## Ad Format Strategy ($5.2M Lifetime Spend)

| Format | Top 10 Share | Role |
|---|---|---|
| Video (UGC) | 6/10 | Dominates prospecting spend |
| Static (single image) | 4/10 | Dominates urgency / conversion spend |
| Carousel | 0/10 | Untested — see [[untested-opportunities]] |
| Collection | 0/10 | Not fit for purchase psychology |

### Single Image — The Workhorse
Use for urgency, retargeting warm audiences, comparison / social proof, fast iteration. Dominant buyer is 55+ women on Facebook mobile — retro aesthetic (yellow/red, block typography) differentiates from clean minimalist health-snack competitors.

### Video (UGC) — The Prospecting Engine
Use for cold traffic, new audience segments (GLP-1, keto, diabetic), trust-building. 73.4% Facebook spend + 55+ female skew mean slower pacing and trust-building outperform fast-cut Gen Z content.

### Carousel — Untested Strategic Opportunity
Flavor variety showcase, before/after nutrition comparison, objection-per-card retargeting sequence. Worth testing — flavor variety angle is highly requested in comments.

## Audience-to-Format Mapping

| Audience | Format | Best Hook Type |
|---|---|---|
| Cold prospecting | UGC Video 45–90s + benefit-stack static | Disbelief stat, demographic, investment |
| Retargeting (warm) | Urgency static + short video 15–30s | Scarcity letter, social proof quote |
| Lookalikes | Same as cold | Proven hooks that converted cold |

## ICP-Specific Defaults

See [[icp-creative-matrix]] for the full ICP × hook/format/offer/LP lookup. All ICP leads route through [[fiber-first-positioning|fiber]] as the mechanism.

## Comment Reply Library

Built from 50,000+ real comments. Templates address highest-liked objections. Full text in `meta_ad_copy.md`.

| # | Trigger | Tone |
|---|---|---|
| 1 | Skeptic / "is this real?" | Warm, self-aware |
| 2 | "Safe for diabetics?" | Warm, stat-led, doctor consult |
| 3 | Flavor questions | Enthusiastic, community |
| 4 | Price objection | Empathetic, route to subscribe-and-save |
| 5 | Digestive side effects | Humor + fiber education |
| 6 | Complaint | Gracious, curious, not defensive |
| 7 | Enthusiastic positive | Match energy, community |

Compliance rules per template: [[compliance-guardrails]].

## DM Response Modes

- **Customer service mode** — complaints, orders, subscription issues. Lead with empathy. Escalate billing/subscription to human immediately.
- **Sales mode** — general inquiries, flavor questions, "where can I buy." Recommend variety pack. Mention subscribe-and-save.

Never shift to sales mode before the service issue is resolved.

## Compliance Filter — Script-Level, Not Phrase-Level

A provocative hook paired with a compliant body is compliant. Hooks get latitude; the body must deliver the fiber/audience/mechanism framing. See [[compliance-guardrails]] for full policy.

**Auto-reject (body cannot rescue):** cures/treats/fixes, regulates blood sugar, lowers cholesterol, melt/burn fat, detox/cleanse/skinny, body shaming, before/after transformation, "Ozempic alternative."

**Monitor tier (allowed with fiber-grounded body):** kills cravings, keeps you full, no sugar spike, weight loss / lose weight (as audience framing), GLP-1 (category term only — never a drug name, audience context, not alternative).

**Banned (moved out of monitor tier 2026-06-30):** "appetite suppressant" / "natural appetite suppressant" — appetite-control positioning is a hard stop. Craving relief stays first-person/situational.

## Product Stats — Exact Values

| Stat | Approved phrasing |
|---|---|
| Fiber | `26g of fiber` |
| Sugar | `3g sugar` |
| Net carbs | `3g net carbs` |
| Calories | `70 calories` on fruit/berry SKUs (prefer `Only 70 calories` where true); `70–90 calories` for multi-SKU/range claims — verify the label per SKU |
| Price (sub) | `$2.69 per bag` |
| Price (one-time) | `$3.50 per bag` |
| Offer | `Up to 46% off + 4 free gifts` (first subscription order only — offer is sub-gated) |

---

## Related pages

- [[ad-copy-patterns]] — brand-neutral framework (parent)
- [[hook-framework]]
- [[shameless-creative-strategy]]
- [[script-leaderboard]]
- [[fiber-first-positioning]]
- [[compliance-guardrails]]
- [[voice-of-customer]]
- [[pricing-and-offers]]
- [[product-facts]]
- [[icp-creative-matrix]]
- [[untested-opportunities]]
