import test from 'node:test'
import assert from 'node:assert/strict'
import { validationScore, classify, momentum, medianRunDays, assembleLane } from './score.mjs'

test('validationScore strong needs >=3 advertisers AND >=15 variants', () => {
  assert.equal(validationScore({ advertisers: 3, variants: 15 }), 'strong')
  assert.equal(validationScore({ advertisers: 5, variants: 14 }), 'weak')
  assert.equal(validationScore({ advertisers: 2, variants: 99 }), 'weak')
})

test('momentum ±15% thresholds', () => {
  assert.equal(momentum(120, 100), 'up')
  assert.equal(momentum(80, 100), 'down')
  assert.equal(momentum(110, 100), 'flat')
  assert.equal(momentum(50, null), 'flat')
})

test('momentum exactly +15% is flat (strictly greater than threshold)', () => {
  assert.equal(momentum(115, 100), 'flat')
})

test('classify gap = strong validation + not covered', () => {
  const l = { competitorValidation: { score: 'strong' }, ourCoverage: { covered: false, cmRoas: null } }
  assert.equal(classify(l, 'flat'), 'gap')
})
test('classify proven-ours = strong + covered + cmRoas>=1.6', () => {
  const l = { competitorValidation: { score: 'strong' }, ourCoverage: { covered: true, cmRoas: 2.0 } }
  assert.equal(classify(l, 'flat'), 'proven-ours')
})
test('classify fading = covered but cmRoas<1.0 OR momentum down', () => {
  assert.equal(classify({ competitorValidation: { score: 'weak' }, ourCoverage: { covered: true, cmRoas: 0.8 } }, 'flat'), 'fading')
  assert.equal(classify({ competitorValidation: { score: 'strong' }, ourCoverage: { covered: false, cmRoas: null } }, 'down'), 'fading')
})
test('classify emerging = momentum up + weak validation', () => {
  assert.equal(classify({ competitorValidation: { score: 'weak' }, ourCoverage: { covered: false, cmRoas: null } }, 'up'), 'emerging')
})
test('medianRunDays', () => {
  const ad = (s, e) => ({ startDate: s, endDate: e })
  assert.equal(medianRunDays([ad('2026-06-01', '2026-06-11'), ad('2026-06-01', '2026-06-21')]), 15)
  assert.equal(medianRunDays([]), 0)
})

test('assembleLane produces the full Lane contract object', () => {
  // 3 advertisers reach the strong threshold (>=3 advertisers AND >=15 variants);
  // the 2-brand input the review draft used scores weak (advertisers < 3), so it
  // cannot be 'strong'/'gap' under the locked thresholds.
  const lane = assembleLane(
    { id: 'x', label: 'X', aliases: [], status: 'watching' },
    [{ brand: 'B', title: 'T', body: 'body', variantCount: 20, adLibraryUrl: 'u', startDate: '2026-06-01', endDate: '2026-06-20' },
     { brand: 'C', title: '', body: 'b2', variantCount: 10, adLibraryUrl: 'u2', startDate: '2026-06-01', endDate: '2026-06-15' },
     { brand: 'D', title: 'T3', body: 'b3', variantCount: 5, adLibraryUrl: 'u3', startDate: '2026-06-01', endDate: '2026-06-10' }],
    { spend: 0, cmRoas: null },
    { commentThemes: 2, trendMentions: 1 },
    null
  )
  assert.equal(lane.id, 'x')
  assert.equal(lane.competitorValidation.advertisers, 3)
  assert.equal(lane.competitorValidation.variants, 35)
  assert.equal(lane.competitorValidation.score, 'strong')
  assert.equal(lane.ourCoverage.covered, false)
  assert.equal(lane.classification, 'gap')
  assert.equal(lane.evidence.length, 3)
  assert.equal(lane.evidence[0].variants, 20)
  for (const key of ['id', 'label', 'status', 'classification', 'competitorValidation', 'ourCoverage', 'demand', 'momentum', 'evidence', 'suggestedBrief', 'updatedAt']) {
    assert.ok(key in lane, `missing contract key: ${key}`)
  }
})

test('assembleLane evidence mapping is null-safe when an ad lacks title and body', () => {
  const lane = assembleLane(
    { id: 'y', label: 'Y', aliases: [], status: 'watching' },
    [{ brand: 'B', variantCount: 4, adLibraryUrl: 'u', startDate: '2026-06-01', endDate: '2026-06-05' }],
    null,
    { commentThemes: 0, trendMentions: 0 },
    null
  )
  assert.equal(lane.evidence.length, 1)
  assert.equal(lane.evidence[0].title, '')
})
