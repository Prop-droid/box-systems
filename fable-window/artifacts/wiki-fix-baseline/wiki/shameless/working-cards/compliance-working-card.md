# Compliance — Working Card

**Summary**: Day-to-day compliance filter for Shameless Snacks static ads, scripts, hooks, and comment replies. Decision tree, grouped hard stops, monitor tier with fiber-grounding rule, ⚠ tagging format, and the script-level drift question.

**Sources**: compliance_guide.md, shameless-static-copywriter/knowledge/compliance.md

**Last updated**: 2026-04-23

---

> **Relationship to [[compliance-guardrails]]:** [[compliance-guardrails]] is the canonical policy source of truth. This page is the generation-ready working card (tagging format, decision tree, line-level filters) imported from the static-copywriter pack. Use it for production tagging mechanics, but when the two diverge on policy, defer to [[compliance-guardrails]]. The 927-line `raw/brand-context/compliance_guide.md` remains the authoritative edge-case source.

## How to use

Every line of ad copy — hook, headline, body, CTA, comment reply — has to clear this page before it ships. There are two tiers:

- **Hard stops** — phrases, terms, and claims that are auto-tagged and never rescued. Flag and rewrite. No softening, no "if we just tweak it," no exceptions.
- **Monitor tier** — language that is permitted only when the body grounds the claim in the fiber mechanism (26g of fiber → fullness → fewer cravings → natural outcome). Monitor-tier language without a fiber anchor is treated the same as a hard stop.

Workflow for every draft or review:

1. Scan the line for any hard stop. If present, tag and rewrite.
2. Scan for monitor-tier language. If present, verify the surrounding body includes the fiber mechanism. If the grounding is missing, tag and either add the grounding or cut the claim.
3. Run the script-level filter (bottom of this page) on the piece as a whole.
4. If all three pass, the copy is approved.

When in doubt, rewrite. Hard stops never get benefit of the doubt.

## Tagging format

```
Format: ⚠ "<phrase>" — <stop reason>
Compliant:  ✓ clean
Violating:  ⚠ "melts fat" — physiological/clinical weight claim (hard stop)
```

Keep violating lines in the ranked list with the tag — do not silently drop them. The tag is the feedback loop for the strategist.

Worked example — raw draft:

> "Our candy won't spike blood sugar and melts fat while you sleep — the Ozempic alternative you've been waiting for."

Tagged output:

> "Our candy ⚠ \"won't spike blood sugar\" — diabetic safety claim (hard stop) and ⚠ \"melts fat\" — physiological/clinical weight claim (hard stop) while you sleep — the ⚠ \"Ozempic\" — drug name (hard stop) alternative you've been waiting for."

## Hard stops (auto-tag, never rescue)

### GLP-1 and weight-loss drug names

All treated as comparison/alternative claims the moment they appear in copy:

- Ozempic
- Wegovy
- Zepbound
- Mounjaro
- semaglutide
- tirzepatide
- GLP-1 (when named as a comparison, alternative, or clinical context — see monitor tier for the one narrow exception)

### Disease / medical outcome verbs

Applied to any condition or symptom:

- cure / cures / cured
- treat / treats / treated
- fix / fixes / fixed
- heal / heals / healed
- reverse / reversed
- prevent / prevents / prevented
- eliminate / eliminated

### Diabetic safety and blood sugar claims

- "safe for diabetics"
- "diabetic-friendly" / "diabetic safe"
- "regulates blood sugar"
- "won't spike blood sugar" / "no sugar spike" / "no blood sugar spike"
- "manages blood sugar" / "controls blood sugar"
- "insulin-friendly" / any insulin claim
- "A1C" claims

### Cardiovascular / cholesterol claims

- "lowers cholesterol"
- "heart health benefits" (as a product claim)
- "cardiovascular" benefit claims
- "beneficial for cholesterol health"

### Weight / body physiological claims

- "melts fat" / "melt fat"
- "burns fat" / "burn fat"
- "cures obesity"
- "BMI" threshold claims
- "calorie deficit" paired with medical/clinical framing

### Detox and shape-based language

- "detox"
- "cleanse"
- "skinny" (as a product promise, audience descriptor, or outcome)

### Disease / immunity / microbiome outcomes

- "boosts immunity"
- "cures leaky gut" / any leaky-gut claim
- "treats IBS" / any IBS treatment claim
- "cures constipation" / "fixes constipation"
- "stops bloating"

### Body-shaming language

- Any ridicule of body size, shape, or eating habits
- "pinch an inch" style imagery language
- Negative body-image framing in copy (self-directed or about others)

### Before/after and body-transformation framing

- "before and after" applied to bodies
- "body transformation"
- "Day 1 / Day 30" over bodies
- Scale / tape-measure / calorie-counter references in body copy

### Factually false ingredient claims

Product contains sucralose — the following are hard stops:

- "no artificial sweeteners"
- "all natural sweeteners"
- "only natural ingredients"

### Defamatory competitor claims

- Any negative naming of a competitor brand (e.g., "better than SmartSweets," "SmartSweets is junk")

### Metabolic state claims beyond keto-friendly as a factual descriptor

- "helps you stay in ketosis"
- "won't kick you out of ketosis"

### Overconsumption-in-response-to-harm language

- Any instruction to "keep eating them" in response to a reported digestive issue

## Monitor tier (allowed with fiber-grounded body)

Permitted only when the surrounding body anchors the claim in the fiber mechanism: **26g of fiber → fullness → fewer cravings → natural outcome**.

**Permitted phrases:**

- **"Natural appetite suppressant"** — must be paired with the fiber stat and the satiety mechanism in the same ad (e.g., "26g of fiber keeps you full — a natural appetite suppressant"). Never sits alone.
- **"Kills cravings" / "curbs cravings" / "cuts my sugar cravings" / "fights hunger"** — fiber-grounded. Body ties cravings reduction to fullness from fiber.
- **"Keeps you full" / "hunger disappears after a single bag" / "feel full after your whole bag"** — satiety claims rooted in the fiber stat.
- **"Weight loss" / "losing weight" / "shedding pounds" / "watching my weight"** — permitted as audience framing and personal narrative, never as outcome promise from the product. Weight loss is the audience's goal, not a product guarantee.
- **"Weight management journey" / "supports my health goals" / "fits my goals"** — goal framing, never clinical.
- **"Finally seeing results" / "jeans fit better"** — sensory personal outcome only, never paired with body-transformation imagery, scales, or tape measures.
- **"Only 70 calories" + first-person outcome narrative** — stat plus personal story is fine; stat plus clinical promise is not.
- **GLP-1 personal story — only when the drug is NOT named.** A creator can share personal experience with medication as context ("I've been on medication for six months and my digestion stopped — I needed more fiber") without ever naming Ozempic, Wegovy, Zepbound, Mounjaro, semaglutide, tirzepatide, or GLP-1. The moment a drug is named, it becomes a hard stop.

**Fiber-grounding requirement:** If a monitor-tier phrase appears and the ad does not include the fiber mechanism somewhere in the body (the 26g stat, the satiety logic, or the "fiber → fullness → fewer cravings" chain), tag the line and either ground it or cut it.

## Decision tree (line-level)

Run every headline and every body line through these 4 steps in order. Stop at the first match. The outcome goes in the Compliance column of any ranking table — the line is NEVER dropped from the list.

1. **Hard-stop scan.** Does the line contain any phrase or term from Hard Stops above?
   - Yes → Compliance = `⚠ "<phrase>" — <stop reason>`. Keep the line in the list.
   - No → continue.
2. **Monitor-tier scan.** Does the line contain a monitor-tier phrase?
   - Yes (headline) → Compliance = `✓ clean` (headline gets latitude; the body will need fiber-grounding at full-copy expansion).
   - Yes (body) → verify the fiber mechanism appears in the same ad. If not, Compliance = `⚠ "<phrase>" — missing fiber grounding`.
   - No → continue.
3. **Borderline scan.** Any claim, phrase, or implication that sounds medical, outcome-promising, or body-transformation adjacent but isn't listed above?
   - Yes → Compliance = `⚠ "<phrase>" — needs review`.
   - No → continue.
4. **Default.** Compliance = `✓ clean`.

## Script-level filter (cumulative drift)

Line-level checks catch obvious violations. They miss the drift that happens across a whole ad — where every line is technically compliant but the cumulative impression is a medical, drug-replacement, or transformation promise.

Ask this one question about the piece as a whole:

> **After reading the whole ad, does a reasonable viewer walk away believing the product cures a condition, replaces a drug, or guarantees a body transformation?**

If the answer is yes — even when no single line triggered a hard stop — the piece fails.

Specifically, the script-level filter catches:

- Ads where every monitor-tier phrase is present but the fiber grounding is buried or missing.
- Ads where audience framing + satiety claims + "finally seeing results" together read as a weight-loss guarantee.
- Ads where a GLP-1 personal story is compliant at the line level but the overall framing implies the product is a drug replacement.
- Compliant copy paired with imagery cues (scales, tape measures, calorie apps, before/after bodies) that Meta's visual policy would still reject.

When the filter flags a piece, rewrite the framing or kill the concept. Monitor-tier language is a privilege, not a loophole.

## Imagery policy

Visual policy is stricter than copy policy. Hard stops on imagery:

- Scales, tape measures, calorie-tracking apps in frame
- Before / after body comparisons
- Clinical props (glucometers, CGM sensors, prescription bottles) as product-promise cues
- Injection pen imagery
- Any body-shaming visual

Creators can *reference* these in personal narrative ("since my doctor told me...") without showing them on camera.

## Weight-loss framing — the line

Canonical table lives in [[compliance-guardrails]]. In short: personal narrative and social proof are permitted; clinical promise and outcome guarantee are not. Mechanism always routes through fiber.

## Customer testimonials — amplification rule

FTC holds brands responsible for testimonials they like, pin, or enthusiastically reply to. Canonical non-endorsement reply:

> *"So happy you're enjoying them! We always recommend checking with your healthcare provider for any specific health-related questions."*

Exception (2026-04-15 policy): weight-loss testimonials may be amplified, with "results not typical" disclosure if the outcome is exceptional.

## Related pages

- [[compliance-guardrails]] — canonical compliance policy (source of truth)
- [[brand-fact-rules]] — per-bag stat rules + "no artificial sweeteners" reference
- [[sub-angles-working-card]] — fiber-grounded body snippets ready to paste
- [[dont-say-bank]] — off-voice phrases (not compliance, but stylistic)
- [[fiber-first-positioning]]
