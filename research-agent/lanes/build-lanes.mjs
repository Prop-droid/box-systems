#!/usr/bin/env node
import { promises as fs } from 'fs'
import { readdirSync, readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { execFileSync } from 'child_process'
import { assembleLane, classifyLanes } from './score.mjs'
import { tagAds, proposeLanes } from './tag.mjs'

const DRY = process.argv.includes('--dry-run')
const KEY = process.env.GEMINI_API_KEY
const ATRIA_DIR = process.env.ATRIA_DIR
const CANON = process.env.LANES_CANON
const OUT = process.env.LANES_OUT
const BQ_TABLE = process.env.BQ_TABLE
const BRAND = (process.env.BRAND || 'SHA').replace(/'/g, '')
const SEED = new URL('./canon.seed.json', import.meta.url)

function newestAtria() {
  const f = readdirSync(ATRIA_DIR)
    .filter(n => /^atria-swipe-.*\.jsonl$/.test(n))
    .sort()
    .pop()
  if (!f) throw new Error('no atria file in ' + ATRIA_DIR)
  return join(ATRIA_DIR, f)
}

function parseAtria(file) {
  return readFileSync(file, 'utf-8')
    .split('\n')
    .filter(Boolean)
    .map(l => {
      try {
        const r = JSON.parse(l)
        return {
          id: String(r.id),
          brand: r.brand_name || '',
          title: r.title || '',
          body: r.body || '',
          angles: Array.isArray(r.angles) ? r.angles : [],
          variantCount: r.variant_count || 0,
          startDate: (r.start_date || '').slice(0, 10),
          endDate: (r.end_date || '').slice(0, 10),
          adLibraryUrl: r.ad_library_url || '',
        }
      } catch {
        return null
      }
    })
    .filter(Boolean)
}

async function loadCanon() {
  if (CANON && existsSync(CANON)) return JSON.parse(await fs.readFile(CANON, 'utf-8'))
  const seed = JSON.parse(readFileSync(SEED, 'utf-8'))
  if (CANON && !DRY) {
    await fs.mkdir(join(CANON, '..'), { recursive: true })
    await fs.writeFile(CANON, JSON.stringify(seed, null, 2))
  }
  return seed
}

function bqCoverage(canonLane) {
  if (!BQ_TABLE) return null
  const rx = canonLane.aliases.map(a => a.replace(/'/g, '')).join('|')
  if (!rx) return null
  const sql =
    `SELECT ROUND(SUM(spend),0) spend, ROUND(SAFE_DIVIDE(SUM(revenue)-SUM(cogs),SUM(spend)),2) cmRoas` +
    ` FROM \`${BQ_TABLE}\`` +
    ` WHERE brand='${BRAND}'` +
    ` AND dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)` +
    ` AND REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(ai_headline,''),' ',IFNULL(ai_first_sentence,''),' ',IFNULL(headline,''),' ',IFNULL(description,''),' ',IFNULL(adset_name,''))), r'(${rx.toLowerCase()})')`
  try {
    const out = execFileSync('bq', ['query', '--use_legacy_sql=false', '--format=json', sql], {
      encoding: 'utf-8',
    })
    const row = JSON.parse(out)[0] || {}
    return {
      spend: row.spend != null ? Number(row.spend) : null,
      cmRoas: row.cmRoas != null ? Number(row.cmRoas) : null,
    }
  } catch (e) {
    console.error('bq coverage failed for', canonLane.id, e.message)
    return null
  }
}

function demandFor(canonLane, themes) {
  const hits = themes.filter(t =>
    canonLane.aliases.some(a => t.toLowerCase().includes(a.toLowerCase())),
  ).length
  return { commentThemes: hits, trendMentions: 0 }
}

function loadThemes() {
  const dir = process.env.COMMENTS_DIGEST_DIR
  if (!dir || !existsSync(dir)) return []
  try {
    const f = readdirSync(dir)
      .filter(n => n.endsWith('.md'))
      .sort()
      .pop()
    if (!f) return []
    return readFileSync(join(dir, f), 'utf-8')
      .split('\n')
      .filter(l => /^[-*]\s/.test(l))
      .map(l => l.replace(/^[-*]\s/, ''))
  } catch {
    return []
  }
}

async function loadPrior() {
  if (!OUT) return {}
  try {
    const files = readdirSync(OUT)
      .filter(n => /^\d{4}-\d{2}-\d{2}\.json$/.test(n))
      .sort()
    const target = files[files.length - 8] || files[0] // ~7 days back
    if (!target) return {}
    const prev = JSON.parse(readFileSync(join(OUT, target), 'utf-8'))
    return Object.fromEntries((prev.lanes || []).map(l => [l.id, l]))
  } catch {
    return {}
  }
}

async function main() {
  if (!KEY) throw new Error('GEMINI_API_KEY not set (source ~/.hermes/.env)')
  if (!ATRIA_DIR) throw new Error('ATRIA_DIR not set')

  const ads = parseAtria(newestAtria())
  const cutoff = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10)
  const recent = ads.filter(a => a.startDate && a.startDate >= cutoff)

  const canon = await loadCanon()
  const adLaneRaw = await tagAds(recent, canon, KEY)

  const themes = loadThemes()
  const prior = await loadPrior()

  const byLane = {}
  for (const a of recent) {
    const id = adLaneRaw[a.id]
    if (id && id !== 'unmatched') {
      ;(byLane[id] ??= []).push(a)
    }
  }

  let lanes = canon.map(c =>
    assembleLane(c, byLane[c.id] || [], bqCoverage(c), demandFor(c, themes), prior[c.id] || null),
  )
  // Final classification is RELATIVE across our covered lanes (see classifyLanes).
  lanes = classifyLanes(lanes)

  const unmatched = recent.filter(a => adLaneRaw[a.id] === 'unmatched')
  const proposed = await proposeLanes(unmatched, KEY)

  const adLane = Object.fromEntries(
    Object.entries(adLaneRaw).filter(([, v]) => v !== 'unmatched'),
  )

  const result = { generatedAt: new Date().toISOString(), lanes, proposed, adLane }

  if (DRY) {
    console.log(JSON.stringify(result, null, 2))
    return
  }

  await fs.mkdir(OUT, { recursive: true })
  const date = new Date().toISOString().slice(0, 10)
  await fs.writeFile(join(OUT, 'latest.json'), JSON.stringify(result, null, 2))
  await fs.writeFile(join(OUT, `${date}.json`), JSON.stringify(result, null, 2))
  console.log(
    `lanes: ${lanes.length} scored, ${proposed.length} proposed, ${Object.keys(adLane).length} ads tagged`,
  )
}

main().catch(e => {
  console.error(e)
  process.exit(1)
})
