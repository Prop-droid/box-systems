export const VALIDATION_MIN_ADVERTISERS = 3
export const VALIDATION_MIN_VARIANTS = 15
export const COVERAGE_SPEND_FLOOR = 1000
export const BREAKEVEN_CMROAS = 1.6
export const MOMENTUM_PCT = 0.15

export function validationScore({ advertisers, variants }) {
  return advertisers >= VALIDATION_MIN_ADVERTISERS && variants >= VALIDATION_MIN_VARIANTS ? 'strong' : 'weak'
}

export function momentum(now, prior) {
  if (prior == null || prior === 0) return 'flat'
  const d = (now - prior) / prior
  if (d > MOMENTUM_PCT) return 'up'
  if (d < -MOMENTUM_PCT) return 'down'
  return 'flat'
}

export function classify(lane, mom) {
  const strong = lane.competitorValidation.score === 'strong'
  const { covered, cmRoas } = lane.ourCoverage
  if (covered && cmRoas != null && cmRoas < 1.0) return 'fading'
  if (mom === 'down' && !(covered && cmRoas != null && cmRoas >= BREAKEVEN_CMROAS)) return 'fading'
  if (strong && !covered) return 'gap'
  if (strong && covered && cmRoas != null && cmRoas >= BREAKEVEN_CMROAS) return 'proven-ours'
  if (mom === 'up' && !strong) return 'emerging'
  return 'watching'
}

export function medianRunDays(ads) {
  const days = ads
    .map(a => {
      const s = Date.parse(a.startDate), e = Date.parse(a.endDate)
      return Number.isFinite(s) && Number.isFinite(e) ? Math.round((e - s) / 86400000) : null
    })
    .filter(d => d != null && d >= 0)
    .sort((x, y) => x - y)
  if (!days.length) return 0
  const m = Math.floor(days.length / 2)
  return days.length % 2 ? days[m] : Math.round((days[m - 1] + days[m]) / 2)
}

// canonLane: { id, label, aliases, status }
// matchedAds: AtriaAd[] already filtered to this lane (last 30d)
// bq: { spend, cmRoas } | null   demand: { commentThemes, trendMentions }
// prior: previous snapshot Lane for this id | null
export function assembleLane(canonLane, matchedAds, bq, demand, prior) {
  const advertisers = new Set(matchedAds.map(a => a.brand).filter(Boolean)).size
  const variants = matchedAds.reduce((s, a) => s + (a.variantCount || 0), 0)
  const validation = { advertisers, variants, medianRunDays: medianRunDays(matchedAds), score: validationScore({ advertisers, variants }) }
  const covered = !!bq && bq.spend != null && bq.spend >= COVERAGE_SPEND_FLOOR
  const ourCoverage = { spend: bq?.spend ?? null, cmRoas: bq?.cmRoas ?? null, covered }
  const priorMetric = prior ? (prior.competitorValidation.advertisers + prior.competitorValidation.variants) : null
  const mom = momentum(advertisers + variants, priorMetric)
  const lane = { competitorValidation: validation, ourCoverage }
  const evidence = matchedAds
    .slice().sort((a, b) => (b.variantCount || 0) - (a.variantCount || 0)).slice(0, 5)
    .map(a => ({ brand: a.brand, title: a.title || (a.body || '').slice(0, 80), url: a.adLibraryUrl, variants: a.variantCount || 0 }))
  return {
    id: canonLane.id, label: canonLane.label, status: canonLane.status || 'watching',
    classification: classify(lane, mom),
    competitorValidation: validation, ourCoverage,
    demand: { commentThemes: demand.commentThemes || 0, trendMentions: demand.trendMentions || 0 },
    momentum: mom, evidence, suggestedBrief: null,
    updatedAt: new Date().toISOString().slice(0, 10),
  }
}
