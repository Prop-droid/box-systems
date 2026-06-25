import test from 'node:test'
import assert from 'node:assert/strict'
import { tagAds, proposeLanes } from './tag.mjs'

// Stub fetch: returns a1 mapped, a2 explicitly unmatched; a3 is missing from response
const stubTagFetch = async () => ({
  ok: true,
  json: async () => ({
    candidates: [{ content: { parts: [{ text: '{"a1":"9pm-cravings","a2":"unmatched"}' }] } }],
  }),
})

test('tagAds maps ids and defaults missing to unmatched', async () => {
  const ads = [
    { id: 'a1', title: 't', body: 'b' },
    { id: 'a2', title: 't', body: 'b' },
    { id: 'a3', title: 't', body: 'b' },
  ]
  const canon = [{ id: '9pm-cravings', label: '9pm', description: 'd' }]
  const r = await tagAds(ads, canon, 'k', stubTagFetch)
  assert.equal(r.a1, '9pm-cravings')
  assert.equal(r.a2, 'unmatched')
  assert.equal(r.a3, 'unmatched')
})

test('proposeLanes returns [] for fewer than 3 ads (no fetch call)', async () => {
  let fetchCalled = false
  const noFetch = async () => { fetchCalled = true; return {} }
  const result = await proposeLanes([], 'k', noFetch)
  assert.deepEqual(result, [])
  assert.equal(fetchCalled, false, 'fetch should not be called for 0 ads')

  const result2 = await proposeLanes([{ brand: 'A', title: 't', body: 'b' }], 'k', noFetch)
  assert.deepEqual(result2, [])

  const result3 = await proposeLanes(
    [{ brand: 'A', title: 't', body: 'b' }, { brand: 'B', title: 't', body: 'b' }],
    'k',
    noFetch
  )
  assert.deepEqual(result3, [])
  assert.equal(fetchCalled, false, 'fetch should not be called for < 3 ads')
})

test('tagAds defaults all ads to unmatched on fetch error', async () => {
  const errorFetch = async () => { throw new Error('network failure') }
  const ads = [{ id: 'x1', title: 't', body: 'b' }, { id: 'x2', title: 't', body: 'b' }]
  const canon = [{ id: 'lane-a', label: 'A', description: 'd' }]
  const r = await tagAds(ads, canon, 'k', errorFetch)
  assert.equal(r.x1, 'unmatched')
  assert.equal(r.x2, 'unmatched')
})

test('tagAds defaults all ads to unmatched on non-ok HTTP response', async () => {
  const badFetch = async () => ({ ok: false, status: 429, text: async () => 'rate limited' })
  const ads = [{ id: 'y1', title: 't', body: 'b' }]
  const canon = [{ id: 'lane-a', label: 'A', description: 'd' }]
  const r = await tagAds(ads, canon, 'k', badFetch)
  assert.equal(r.y1, 'unmatched')
})

test('proposeLanes filters out clusters with fewer than 3 advertisers', async () => {
  const stubProposeFetch = async () => ({
    ok: true,
    json: async () => ({
      candidates: [{
        content: {
          parts: [{
            text: JSON.stringify([
              { label: 'lane-a', rationale: 'reason', advertisers: 3, evidence: [] },
              { label: 'lane-b', rationale: 'reason', advertisers: 2, evidence: [] },
              { label: 'lane-c', rationale: 'reason', advertisers: 5, evidence: [] },
            ]),
          }],
        },
      }],
    }),
  })
  const ads = [
    { brand: 'A', title: 't', body: 'b', variantCount: 1 },
    { brand: 'B', title: 't', body: 'b', variantCount: 2 },
    { brand: 'C', title: 't', body: 'b', variantCount: 3 },
  ]
  const result = await proposeLanes(ads, 'k', stubProposeFetch)
  assert.equal(result.length, 2)
  assert.ok(result.every(p => p.advertisers >= 3))
})
