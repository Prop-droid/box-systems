#!/usr/bin/env python3
"""Nightly Meta Ad Library rank capture (SCS Phase 2 / IRV).

Meta's per-brand Ad Library listing is sorted by total_impressions desc by
default — the DOM order of the top ~30 cards is the only public impressions
proxy for US-only ads (spec: creative-command-center
docs/superpowers/specs/2026-08-12-competitor-success-metric.md).

For each brand in monitor.conf, loads the impressions-sorted listing via
camoufox and appends {date, brand, page_id, rank, library_id, text_hash,
text_norm, total} JSONL to $ATRIA_DIR/rank/ad-rank-<date>.jsonl.
text_norm mirrors CCC lib/scs.ts normalizeCreative (the text-join key:
library IDs don't overlap between listing collation reps and Atria members).

Run: uv run --with camoufox python3 rank_scrape.py [--brands m123,m456] [--headful]
Exit 1 unless >= MIN_OK_BRANDS brands yielded >= MIN_CARDS cards
(empty result = FAILURE, never a silent no-op).
"""
import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import date
from pathlib import Path

ATRIA_DIR = Path("/home/tomas/brain/projects/2026-06/competitor-ads-scrape/atria")
MONITOR_CONF = Path("/home/tomas/systems/research-agent/monitor.conf")
MIN_CARDS = 5       # per-brand success threshold
MIN_OK_BRANDS = 5   # run-level success threshold

LISTING_URL = (
    "https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
    "&country=US&media_type=all&search_type=page&view_all_page_id={page_id}"
    "&sort_data[direction]=desc&sort_data[mode]=total_impressions"
)

# card-text lines that are Ad Library chrome, not creative copy
BOILERPLATE = re.compile(
    r"^(library id|started running|platforms?$|categories|active$|inactive$|sponsored$"
    r"|\d+ ads use this creative( and text)?$"
    r"|see ad details|see summary details|open drop-?down|this ad has multiple versions"
    r"|ad delivery|estimated audience|amount spent|impressions|learn more$|shop now$"
    r"|sign up$|order now$|get offer$|subscribe$|buy now$|download$)",
    re.IGNORECASE,
)

EXTRACT_JS = """
() => {
  const leaves = [...document.querySelectorAll('span,div')].filter(el =>
    el.childElementCount === 0 && /^Library ID:?\\s*\\d+/.test((el.textContent || '').trim()));
  const seen = new Set(); const out = [];
  for (const el of leaves) {
    const id = el.textContent.match(/(\\d+)/)[1];
    if (seen.has(id)) continue;
    seen.add(id);
    // card root = widest ancestor still containing exactly one "Library ID"
    let card = el;
    while (card.parentElement) {
      const n = (card.parentElement.innerText.match(/Library ID/g) || []).length;
      if (n > 1) break;
      card = card.parentElement;
    }
    out.push({ id, text: (card.innerText || '').slice(0, 3000) });
  }
  return out;
}
"""


def normalize_creative(text: str) -> str:
    """Mirror of CCC lib/scs.ts normalizeCreative (lowercase, non-alnum -> space, 200 chars)."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()[:200]


def creative_text(card_text: str) -> str:
    lines = [l.strip() for l in card_text.splitlines()]
    kept = [l for l in lines if l and not BOILERPLATE.match(l) and not l.startswith("http")]
    return " ".join(kept)


def brand_names() -> dict:
    """page_id -> brand_name from the newest curated Atria pull (guarantees the
    rank record's brand string equals the archive's, which the CCC join needs)."""
    daily = sorted(ATRIA_DIR.glob("atria-swipe-*-gr-ns-plus10.jsonl"))
    names = {}
    if daily:
        for line in daily[-1].read_text().splitlines():
            try:
                rec = json.loads(line)
                names[rec["brand_id"].lstrip("m")] = rec["brand_name"]
            except (json.JSONDecodeError, KeyError):
                continue
    return names


def monitor_page_ids() -> list:
    m = re.findall(r'^MONITOR_BRAND_IDS="([^"]+)"', MONITOR_CONF.read_text(), re.MULTILINE)
    if not m:
        sys.exit("monitor.conf: MONITOR_BRAND_IDS not found")
    return [b.lstrip("m") for b in m[-1].split()]


def scrape_brand(page, page_id: str) -> list:
    page.goto(LISTING_URL.format(page_id=page_id), wait_until="domcontentloaded", timeout=60000)
    # EU cookie wall (box is in Lithuania)
    for label in ("Decline optional cookies", "Allow all cookies"):
        try:
            page.get_by_role("button", name=label).first.click(timeout=4000)
            break
        except Exception:
            continue
    page.wait_for_function("() => document.body.innerText.includes('Library ID')", timeout=30000)
    for _ in range(3):  # load the full top-~30 set
        page.mouse.wheel(0, 2500)
        time.sleep(1.5)
    return page.evaluate(EXTRACT_JS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", help="comma-separated m-ids or page ids (default: monitor.conf)")
    ap.add_argument("--headful", action="store_true")
    args = ap.parse_args()

    page_ids = ([b.strip().lstrip("m") for b in args.brands.split(",")]
                if args.brands else monitor_page_ids())
    names = brand_names()
    today = date.today().isoformat()
    out_dir = ATRIA_DIR / "rank"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"ad-rank-{today}.jsonl"

    from camoufox.sync_api import Camoufox

    records, ok_brands = [], 0
    with Camoufox(headless=not args.headful) as browser:
        page = browser.new_page()
        for i, pid in enumerate(page_ids):
            brand = names.get(pid, pid)
            try:
                cards = scrape_brand(page, pid)
            except Exception as e:
                print(f"FAIL {brand} ({pid}): {e}", file=sys.stderr)
                cards = []
            bn = normalize_creative(brand)
            for rank, card in enumerate(cards, 1):
                norm = normalize_creative(creative_text(card["text"]))
                # drop the card's page-name header so text starts at the creative
                if bn and norm.startswith(bn + " "):
                    norm = norm[len(bn) + 1:]
                records.append({
                    "date": today, "brand": brand, "page_id": pid, "rank": rank,
                    "library_id": card["id"],
                    "text_hash": hashlib.sha1(norm.encode()).hexdigest()[:12],
                    "text_norm": norm, "total": len(cards),
                })
            print(f"{brand}: {len(cards)} cards", file=sys.stderr)
            if len(cards) >= MIN_CARDS:
                ok_brands += 1
            if i < len(page_ids) - 1:
                time.sleep(random.uniform(8, 15))

    # Merge by brand: a partial/manual run (subset of brands) must not wipe the
    # other brands' rows already written today. Keep existing rows for brands not
    # in this run, replace those that are.
    scraped_brands = {r["brand"] for r in records}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("brand") not in scraped_brands:
                records.append(r)
    records.sort(key=lambda r: (r["brand"], r["rank"]))
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in records))
    tmp.rename(out_path)
    print(f"{out_path}: {len(records)} records, {ok_brands}/{len(page_ids)} brands ok", file=sys.stderr)
    if ok_brands < min(MIN_OK_BRANDS, len(page_ids)):
        sys.exit(1)


if __name__ == "__main__":
    main()
