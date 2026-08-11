const GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'

/**
 * Post a JSON-mode prompt to Gemini and return the parsed JSON.
 * @param {string} key - Gemini API key
 * @param {string} prompt - The text prompt
 * @param {Function} fetchImpl - Injected fetch (default: global fetch)
 * @returns {Promise<any>} Parsed JSON from Gemini response
 */
export async function geminiJSON(key, prompt, fetchImpl = fetch) {
  const res = await fetchImpl(`${GEMINI_URL}?key=${key}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { response_mime_type: 'application/json', temperature: 0 },
    }),
  })
  if (!res.ok) throw new Error(`gemini ${res.status}: ${await res.text()}`)
  const data = await res.json()
  const txt = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? '{}'
  return JSON.parse(txt)
}

const chunk = (arr, n) =>
  Array.from({ length: Math.ceil(arr.length / n) }, (_, i) => arr.slice(i * n, i * n + n))

/**
 * Tag each ad with the best matching canon lane id or 'unmatched'.
 * Batches <=40 ads per Gemini call. Never throws; errors default that batch to 'unmatched'.
 * @param {Array<{id: string, title?: string, body?: string}>} ads
 * @param {Array<{id: string, label: string, description: string}>} canon
 * @param {string} key - Gemini API key
 * @param {Function} fetchImpl - Injected fetch
 * @returns {Promise<Record<string, string>>} Map of adId -> laneId|'unmatched'
 */
export async function tagAds(ads, canon, key, fetchImpl = fetch) {
  const lanesDesc = canon.map(c => `- ${c.id}: ${c.label} -- ${c.description}`).join('\n')
  const out = {}
  for (const batch of chunk(ads, 40)) {
    const list = batch
      .map(a => `ID ${a.id}: "${(a.title || '').slice(0, 80)} | ${(a.body || '').slice(0, 160)}"`)
      .join('\n')
    const prompt =
      `You tag competitor snack ads to ONE marketing lane.\nLANES:\n${lanesDesc}\n\nADS:\n${list}\n\nReturn STRICT JSON mapping each ID to the single best lane id, or "unmatched" if none fits well. Format: {"<id>":"<laneId|unmatched>"}. No prose.`
    try {
      const map = await geminiJSON(key, prompt, fetchImpl)
      for (const a of batch) {
        out[a.id] = typeof map[a.id] === 'string' ? map[a.id] : 'unmatched'
      }
    } catch (e) {
      console.error('tagAds batch failed:', e.message)
      for (const a of batch) out[a.id] = 'unmatched'
    }
  }
  return out
}

/**
 * Pass 3 (spec 2026-06-25): one-line suggestedBrief per actionable lane.
 * Only gap/emerging lanes get suggestions; others stay null. Never throws;
 * errors leave every lane's suggestedBrief null.
 * @param {Array} lanes - assembled+classified lanes (mutated in place)
 * @param {string} key - Gemini API key
 * @param {Function} fetchImpl - Injected fetch
 * @returns {Promise<Array>} the same lanes array
 */
export async function suggestBriefs(lanes, key, fetchImpl = fetch) {
  const actionable = lanes.filter(l => l.classification === 'gap' || l.classification === 'emerging')
  if (!actionable.length) return lanes
  const list = actionable
    .map(l => {
      const ev = (l.evidence || []).slice(0, 3).map(e => `${e.brand}: "${e.title}"`).join('; ')
      return `- ${l.id} (${l.classification}, ${l.competitorValidation.advertisers} advertisers, ${l.competitorValidation.variants} variants): ${l.label}. Evidence: ${ev || 'none'}`
    })
    .join('\n')
  const prompt =
    `Shameless Snacks (low-sugar high-fiber gummy candy) has these untested or rising competitor ad lanes:\n${list}\n\n` +
    `For each lane, write ONE line a creative strategist could brief from: "Test <specific angle> for <persona>" — concrete, grounded in the evidence, no hype. ` +
    `Return STRICT JSON mapping lane id to the line: {"<laneId>":"<one line>"}. No prose.`
  try {
    const map = await geminiJSON(key, prompt, fetchImpl)
    for (const l of actionable) {
      if (typeof map[l.id] === 'string' && map[l.id].trim()) l.suggestedBrief = map[l.id].trim()
    }
  } catch (e) {
    console.error('suggestBriefs failed:', e.message)
  }
  return lanes
}

/**
 * Cluster unmatched ads into candidate new lane proposals.
 * Returns [] if fewer than 3 ads; filters to clusters with >=3 distinct brands.
 * @param {Array<{brand: string, title?: string, body?: string, variantCount?: number}>} unmatchedAds
 * @param {string} key - Gemini API key
 * @param {Function} fetchImpl - Injected fetch
 * @returns {Promise<Array<{label: string, rationale: string, advertisers: number, evidence: Array}>>}
 */
export async function proposeLanes(unmatchedAds, key, fetchImpl = fetch) {
  if (unmatchedAds.length < 3) return []
  const list = unmatchedAds
    .slice(0, 120)
    .map(
      a =>
        `${a.brand}: "${(a.title || '').slice(0, 60)} | ${(a.body || '').slice(0, 120)}" (v${a.variantCount || 0})`,
    )
    .join('\n')
  const prompt =
    `These competitor snack ads did not match any known lane:\n${list}\n\nCluster them into NEW candidate marketing lanes. Only return a cluster if it spans 3+ DISTINCT brands. For each, return JSON array items: {"label": short lane name, "rationale": one sentence on why it is a worth-testing lane, "advertisers": distinct brand count, "evidence": [{"brand","title","url":"","variants":0}] up to 3}. Return STRICT JSON array, no prose, [] if none qualify.`
  try {
    const arr = await geminiJSON(key, prompt, fetchImpl)
    return Array.isArray(arr)
      ? arr.filter(p => p && p.label && (p.advertisers ?? 0) >= 3)
      : []
  } catch (e) {
    console.error('proposeLanes failed:', e.message)
    return []
  }
}
