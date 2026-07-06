# Brand-Fact Rules — Generation Guardrails

**Summary**: The numeric and phrasing rules that govern every Shameless Snacks ad — calorie upper-bound, fiber exceptions, sweetener hard stops, approved stat phrasings, and the stat-drift flags currently sitting in wiki pages.

**Sources**: shameless-static-copywriter/knowledge/brand-facts.md, product-facts.md

**Last updated**: 2026-04-23

---

> **Relationship to [[product-facts]]:** That page is the canonical spec sheet (what the numbers are). This page is the rule layer (how those numbers are allowed to appear in copy) and the drift-catcher (where existing wiki pages still carry stale numbers).

## Per-bag canonical stats (repeat)

| Stat | Value | Rule |
|---|---|---|
| Fiber | **26g per bag** | Hero stat. ~90% of daily value. Consistent across every SKU including Allstars. |
| Sugar | **3g per bag** | Total sugar. Prefer "Only 3g of sugar" in voiced copy. Never round. |
| Net carbs | **3g per bag** | Keto-compatible. Never write older "8g net carbs." |
| Calories | **70 per bag** | Consistent across every SKU. Prefer "Only 70 calories" in voiced copy. |
| Serving size | **1 bag = 1 serving** | Permission frame: "the whole bag is the serving." |

## The "Only" rule (voice)

In voiced copy — headlines, hooks, primary text — prefer **"Only 3g of sugar"** over bare "3g sugar," and **"Only 70 calories"** over bare "70 calories." The "Only" prefix frames the number as surprisingly low and lands the disbelief harder. Not required in spec tables or tight lists where the "Only" would disrupt rhythm.

## Calorie rule

- **Every SKU is 70 calories per bag.** There is no range. The older "70–90 calories" framing was inaccurate and has been removed across the wikis and the copywriter pack.
- **Never use:** "under 100 calories," "90 calories or less," "70–90 calories." All deprecated.
- **Prefer in voiced copy:** "Only 70 calories per bag" or "Only 70 calories for the WHOLE bag."

## Fiber rule — 26g across every SKU

- **Every SKU is 26g fiber per bag**, including Allstars Sweet & Sour.
- The earlier "29g for some Allstars SKUs" framing was inaccurate and has been corrected. Do not use 29g anywhere.

## Sweetener hard stops (factually false claims)

Product contains **sucralose**. The following are hard stops — they're factually false and Meta-flaggable:

- ⚠ "no artificial sweeteners"
- ⚠ "all natural sweeteners"
- ⚠ "only natural ingredients"

Approved substitute: "No added refined sugar" — accurate and safe.

See [[compliance-working-card]] for the full hard-stops inventory.

## Approved ad phrasings

Pre-cleared against product facts and pricing guardrails. Drop into ads as-is:

- "26 grams of fiber per bag"
- "26g of gut-loving fiber per bag"
- "90% of your daily fiber in one bag"
- **"Only 3g of sugar"** *(preferred in voiced copy)*
- "3 grams of sugar"
- "3g sugar, 3g net carbs"
- "3g net carbs"
- **"Only 70 calories per bag"** *(preferred in voiced copy)*
- "70 calories per bag"
- "The whole bag is the serving"
- "Taste just like candy"
- "All the flavor, none of the guilt"
- "Eat like no one's watching"
- "Snack Shamelessly"
- "Keto-friendly, vegan, gluten-free"
- "Subscribe and save $1.30 per bag"
- "Just $2.69 per bag on subscribe & save"
- "Free shipping on all orders"
- "Up to 46% off your first order"
- "Up to 46% off + 4 free gifts (first order only)"

## Pricing rules

| Purchase type | Price per bag | Notes |
|---|---|---|
| Subscribe & Save | $2.69 per bag | ~33% off per bag vs. buy-once. Ships every 4 weeks. Flavor-picker model (customer selects flavors, not pre-built variety pack). Adjust, skip, or cancel anytime. |
| Buy Once | $3.50 per bag | Free shipping included on all orders. |

**First-order offer (exact phrasing):** "Up to 46% off + 4 free gifts (first order only)."

- The 46% figure blends the per-bag subscription discount with stated gift value. First order only.
- First-order gifts total $42.80 in stated value: ebook ($7.95), shipping ($4.95), bag clip ($9.95), candy jar ($19.95).
- Free shipping applies to all orders with no minimum.

## Stat-drift fixes — 2026-04-23

Several wiki and copywriter pages carried outdated numeric phrasings (70–90 calorie ranges, Allstars 29g fiber exception). All fixed in place:

- `wiki/shameless-snacks.md` and `shameless snacks wiki/shameless-snacks.md` — "70–90 cal" → "70 cal"; Allstars 29g exception removed
- `wiki/product-facts.md` and `shameless snacks wiki/product-facts.md` — Calories row corrected to 70
- `wiki/shameless-ad-copy-patterns.md` and `shameless snacks wiki/shameless-ad-copy-patterns.md` — Pattern 3 "90 calories or less" → "only 70 calories"; Calories row normalized
- `wiki/shameless-influencer-briefs.md` and `shameless snacks wiki/shameless-influencer-briefs.md` — Key Value Props corrected; "Only" prefix added to sugar stat
- `wiki/shameless-ad-creation-playbook.md`, `wiki/shameless-headline-craft.md` and copies — feature tables corrected to "Only 70 calories"
- `wiki/competitive-landscape.md` and copy — three head-to-head tables corrected
- `shameless-static-copywriter/knowledge/brand-facts.md` — intro paragraph, spec table, approved phrasings corrected
- `shameless-static-copywriter/knowledge/brand-voice.md` — stat-led lines updated with "Only" variants

Remaining non-numeric drift (flagged but not yet fixed — voice/pattern-labelling issues):

| Page | Issue | Suggested fix |
|---|---|---|
| `shameless-ad-copy-patterns.md` | Pattern 1 headline reads "FINAL CLEARANCE SALE!" but the pattern is labeled "Stat Lead + Benefit Stack" — copy-paste mislabelling | Change headline to a stat lead, e.g. "26g of fiber in a candy bag?!" |
| `shameless-ad-copy-patterns.md` | Pattern 1 benefit bullet "No crash, no guilt — just sweet satisfaction" | Replace with "Eat the whole bag. That's the serving." for voice alignment |
| `product-facts.md` | "no artificial sweeteners" flagged as compliance note, not hard stop | Elevate to hard stop — see [[compliance-working-card]] |

## Ingredient claims — safe list

- **Keto-compatible / keto-friendly** — 3g net carbs per bag. Use as factual descriptor only; never write "won't kick you out of ketosis" or "helps you stay in ketosis" (both hard stops).
- **Vegan / plant-based** — yes.
- **Gluten-free** — yes.
- **No added refined sugar** — accurate and safe.
- **Sweeteners used:** erythritol, isomalt, sucralose (internal reference; rarely named in ads).

No medical claims, no disease claims, no drug-name comparisons, no body-transformation language. For anything outcome-adjacent, see [[compliance-working-card]].

## Related pages

- [[product-facts]]
- [[pricing-and-offers]]
- [[compliance-working-card]]
- [[stat-led-lines]]
- [[sub-angles-working-card]]
