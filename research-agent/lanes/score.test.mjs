import test from 'node:test'
import assert from 'node:assert/strict'
import { validationScore, classify, momentum, medianRunDays } from './score.mjs'

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
