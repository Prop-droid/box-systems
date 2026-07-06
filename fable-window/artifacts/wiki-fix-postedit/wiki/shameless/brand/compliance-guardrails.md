# Compliance Guardrails — Quick Reference

**Summary**: At-a-glance compliance reference for Shameless Snacks ad review, covering permitted and prohibited claims, weight-loss framing rules, and the fiber-mechanism routing policy.

**Sources**: compliance_guide.md, [systems/research/2026-04_creative-strategy-tactics/06-fiber-positioning-deep-dive.md](06-fiber-positioning-deep-dive.md), [systems/research/2026-04_creative-strategy-tactics/01-meta-dtc-creative.md](01-meta-dtc-creative.md)

**Last updated**: 2026-06-25

---

> **Authoritative source:** `raw/brand-context/compliance_guide.md` (workspace — 927 lines, full policy, substitution library, automation tiers, edge-case decisions).
> This wiki page is the **at-a-glance card for ad review**. For automation, edge cases, or ambiguity, defer to the workspace doc.

## Current Policy Version

**2026-06-25** — Meta 2026 enforcement sync. Meta now runs **MARS** (Multimodal Ad Review System: scans copy + image + video + audio + LP before first impression) and **retroactively re-audits already-approved ads** (material spike in health-ad rejections Q1 2026). "It got approved" no longer means safe. Three guardrail tightenings, detailed below: (1) personal-attributes — indirect "for people who…" framing is now flagged like direct "you" health-status claims; (2) before/after ban now extends to *implied* transformation (product beside a fit body, "journey" testimonials); (3) the structure-function disclaimer is now expected *in the ad copy itself* for supplement-classified creative, not just the LP. GLP-1 / compounded-weight-loss ads are under active state-AG pressure — treat all drug-adjacent language as high-scrutiny.

**2026-06-09** — "food noise" confirmed permitted (mainstream lifestyle term, runs in shipped ads); keep it grounded in the fiber mechanism, not drug framing. **(2026-06-25 caveat: this is now the single highest-risk *approved* term — it's the signature vocabulary of the GLP-1 conversation Meta is policing. Keep it sparse, always fiber-routed, never near drug language.)**

**2026-06-30** — "appetite suppressant" / appetite-control positioning BANNED (reconfirmed 2026-07-02). Craving relief must stay first-person and situational ("the craving quiets down," "I stopped snacking at 9pm"), never appetite-suppression framing. This revokes the appetite-suppressant permission from the 2026-04-15 update below.

**2026-04-15** — policy expanded to permit weight-loss narrative, satiety, and craving-control language. Driven by top-ROAS winners (Genetics 1.31, Dad Bod 1.19). *(Appetite-suppressant permission from this update was revoked 2026-06-30.)*

> This policy is **not set in stone** — it evolves with shipped-ad practice and platform behavior. When a page conflicts with this one, this page wins; when shipped ads conflict with this page, flag it so the policy gets updated.

## At-a-Glance

### Now Permitted (was restricted)

- Weight-loss narrative framing (personal/testimonial)
- Craving control — "kills cravings," "curbs cravings," etc.
- Satiety claims — "keeps you full"
- Weight-management goal framing
- **"Food noise"** — permitted as lifestyle/on-screen copy (e.g. "food noise gone"); keep it routed through fiber, never drug-mechanism framing

All route through the fiber mechanism. See [[fiber-first-positioning]].

### Hard Stops (never use)

- Medical / disease claims (cures, treats, heals)
- **"Appetite suppressant" / "natural appetite suppressant" / any appetite-control positioning** (banned 2026-06-30). Craving relief stays first-person/situational ("the craving quiets down"), never appetite-suppression framing.
- **Drug names** — Ozempic, Wegovy, Zepbound, Mounjaro, semaglutide, tirzepatide
- **GLP-1 drug-equivalence claims** — "GLP-1 alternative," "natural Ozempic," "GLP-1 activation," "Ozempic-like effect," "replace your shot," "skip the injection." Sits in the FDA warning-letter zone (50+ letters in 2024–2025; 30 telehealth companies in March 2026).
- **"Melt fat" / "burn fat"**
- Diabetic safety claims ("safe for diabetics," "won't spike blood sugar")
- Cholesterol / cardiovascular claims
- Disease / immunity / microbiome outcomes ("cures IBS," "boosts immunity")
- Defamatory competitor claims
- Body-shaming language
- Body-transformation imagery, scales, tape measures, clinical props — **and (2026) *implied* transformation**: product shown beside a fit/healthy body, or a testimonial that narrates a "journey" while the speaker looks healthy. MARS classifies these the same as a literal before/after split, even with fully compliant copy.
- **Personal-attributes framing that implies we know the viewer's health status.** As of 2026 Meta flags indirect constructions ("for people managing X," "those dealing with Y," "if your digestion has slowed") at the same rate as direct "you" language, because targeting signal is factored in. Describe the *snack and the situation*, not the viewer's condition.
- **Front-of-pack fiber count that includes acacia gum / acacia fiber.** FDA's 2018 review did not accept acacia as countable dietary fiber on the Nutrition Facts panel. If the headline gram count includes acacia, the panel and the claim disagree — class-action plaintiff target. Verify against [[product-facts]] before stat-shock copy.

### Weight-Loss Framing — the Line

- Personal narrative: "I've been trying to lose weight" -- permitted
- Social proof: "Thousands are shedding pounds" -- permitted
- Clinical promise: "This product makes you lose weight" -- not permitted
- Outcome guarantee: "Guaranteed weight loss" -- not permitted

Mechanism must route through fiber: *fiber → fullness → fewer cravings → natural outcome.*

### GLP-1 — Permitted Framing (no drug name)

Ride the GLP-1 audience by naming the *symptom*, not the drug — **and (2026) by describing the snack/situation, not the viewer's body**. Prefer product-and-situation framing:

- "26g of fiber for the days nothing tastes good" (situation, not "for people whose appetite is gone")
- "A small bag that fills you up" / "fiber that keeps you full"
- "Supports your body's natural fullness signals"

⚠️ **2026 personal-attributes risk:** "For people whose digestion has slowed down," "for smaller-portion eaters," and similar "for people who…" constructions now trip Meta's personal-attributes classifier the same as direct "you" claims. They were permitted under earlier policy — reframe to the snack/situation. See the personal-attributes hard stop above.

See [[glp1-dosing-companion]] for peer-vocab examples (r/Mounjaro, r/Wegovy, r/Ozempic phrasing) — apply the 2026 reframing when lifting them.

### Claim-Language Map by Benefit

Compact decision support — clean wording on the left, flag risk on the right.

| Benefit | Clean wording | Flag risk wording |
|---------|---------------|-------------------|
| Regularity | "Supports digestive regularity," "helps you stay regular" | "Treats constipation," "relieves chronic constipation" |
| Satiety | "Helps you feel full longer," "keeps you satisfied" | "Suppresses appetite," "weight-loss aid," "burns fat" |
| Blood sugar | "Supports a healthy blood sugar response" (with disclaimer) | "Lowers blood sugar," "treats / prevents diabetes" |
| Weight | "Helps you stay full so you eat less," "supports a balanced lifestyle" | "Lose 10 lbs," "shrink your waist" |
| Bloating | "Gentle on digestion," "less bloat than other fibers" | "Cures bloating," "treats IBS bloat" |

### Account-Level Flag — Meta H&W Sensitivity Tier

Meta moved any advertiser using symptom language, before/after imagery, body-shaming hooks, or weight-loss optimization into the **Health & Wellness Sensitive Category** in January 2025. Sensitive-classified accounts **lose access to Purchase / Add-to-Cart events** and are forced upper-funnel (Landing Page Views, Engagement, Lead forms). Breaks ASC entirely.

- **Trigger is account-level, not ad-level.** A single non-compliant ad can flip the whole account into the tier.
- **Imagery alone is enough.** Even with compliant copy, before/after-coded visuals (split-screen, scale shots, tape measure, clinical props) trigger reclassification. The body-transformation imagery hard stop above is *load-bearing for the whole account*, not just the single ad.
- **If reclassified:** pause flagged creative, request review, assume 14–30 day cool-down before the tier resets.

See [[shameless-andromeda-meta-retrieval]] for why losing Purchase events kills retrieval-stage signal density.

### Defensive Disclaimer (Recommended)

Adding a §403(r)(6)-style structure-function disclaimer voluntarily on conventional-food creative — *"This statement has not been evaluated by the FDA. This product is not intended to diagnose, treat, cure, or prevent any disease."* — is cheap insurance with both Meta H&W reviewers and class-action plaintiffs. ColonBroom, Supergut, and BelliWelli use it on non-supplement SKUs for this reason. Recommended on any LP that uses blood-sugar, satiety, or fullness language.

**2026 update — disclaimer in-copy, not just LP.** Meta now expects this disclaimer *in the ad creative itself* for anything its classifier reads as supplement-adjacent. A fiber gummy is legally a *food*, but MARS can class gummies/fiber as supplement-coded. Decision: on any creative leaning on a health/benefit mechanism (satiety, fullness, blood-sugar, regularity), carry the disclaimer in-copy, not only on the LP. When in doubt, include it.

### Customer Testimonials You Shouldn't Amplify

FTC holds brands responsible for testimonials they like, pin, or enthusiastically reply to. Use canonical non-endorsement: *"So happy you're enjoying them! We always recommend checking with your healthcare provider for any specific health-related questions."*

Exception (new policy): weight-loss testimonials may be amplified, with "results not typical" disclosure if exceptional.

## When in Doubt

1. Check the workspace doc (`compliance_guide.md`) — it has the full substitution table, automation tiers, and GLP-1 decision tree.
2. If still unclear, escalate — don't publish.

## Related pages

- [[fiber-first-positioning]]
- [[brand-voice]]
- [[shameless-creative-strategy]]
- [[script-leaderboard]] (compliance translations for top scripts)
- [[objection-library]]
- [[glp1-dosing-companion]] (GLP-1 peer-vocab framings)
- [[shameless-andromeda-meta-retrieval]] (why H&W tier reclassification kills retrieval signal)
- [[product-facts]] (canonical fiber gram count for stat-shock verification)
